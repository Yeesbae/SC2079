package com.example.sc2079_ay2526s2_grp08.viewmodel

import android.bluetooth.BluetoothAdapter
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.bluetooth.BtDeviceMapper
import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.domain.util.DirectionUtil
import com.example.sc2079_ay2526s2_grp08.protocol.*
import com.example.sc2079_ay2526s2_grp08.protocol.util.isMoveCommand
import com.example.sc2079_ay2526s2_grp08.viewmodel.reducers.*
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.collections.ArrayDeque

class MainViewModel(
    private val bt: BluetoothManager
) : ViewModel() {

    private val demoMode = false
    private var playbackJob: Job? = null
    private val _state = MutableStateFlow(AppState())
    private var autoListenOnDisconnect: Boolean = true
    private val playbackQueue = ArrayDeque<PlaybackCommand>()
    private var waitingForSnap = false
    private var currentSnapObstacleId: String? = null
    private var fallbackImageObstacleIndex = 1
    private var runTimerJob: Job? = null
    private var awaitingAck = false
    private val pendingMoves = ArrayDeque<Outgoing>()
    val state: StateFlow<AppState> = _state

    init {
        bt.onEvent = { ev -> handleBluetoothEvent(ev) }
        ensureInitialState()
    }

    private fun ensureInitialState() {
        _state.update { s ->
            var next = s
            if (next.arena == null) {
                next = next.copy(arena = ArenaState.empty(ArenaState.DEFAULT_WIDTH, ArenaState.DEFAULT_HEIGHT))
            }
            if (next.robot == null) {
                next = next.copy(robot = RobotState(x = 1, y = 1, directionDeg = 0))
            }
            next
        }
    }


    /** Start listening for incoming connections (server mode) */
    fun startDefaultListening() {
        bt.startServer()
    }

    /** Disconnect current session and return to listening mode */
    fun disconnectAndReturnToListening() {
        bt.stopServer()
        bt.disconnectClient()
        bt.startServer()
    }

    /** Connect to a specific Bluetooth device (client mode) */
    fun connectToDevice(device: BtDevice) {
        log(LogEntry.Kind.INFO, "connectToDevice() called")
        autoListenOnDisconnect = false
        bt.stopServer()
        bt.disconnectClient()

        val adapter = BluetoothAdapter.getDefaultAdapter()
        val remote = adapter?.getRemoteDevice(device.address)
        if (remote != null) bt.connect(remote)
        else log(LogEntry.Kind.ERROR, "No adapter / invalid address: ${device.address}")
    }

    fun refreshPairedDevices() {
        val paired = bt.getPairedDevices().map { BtDeviceMapper.toBtDevice(it, bonded = true) }
        _state.update { s -> DiscoveryReducer.setPairedDevices(s, paired) }
    }

    fun startScan() {
        refreshPairedDevices()
        _state.update { s -> DiscoveryReducer.startScan(s) }
        bt.clearDiscoveredDevices()
        bt.startDiscovery()
    }

    fun stopScan() {
        bt.stopDiscovery()
        _state.update { s -> DiscoveryReducer.stopScan(s) }
    }

    /** Return an Intent so UI can launch system dialog */
    fun getDiscoverableIntent(durationSec: Int = 300) =
        bt.buildRequestDiscoverableIntent(durationSec)

    /** Check if Bluetooth is supported on this device */
    fun isBluetoothSupported(): Boolean = bt.isSupported()

    /** Check if Bluetooth is enabled */
    fun isBluetoothEnabled(): Boolean = bt.isEnabled()

    // ═══════════════════════════════════════════════════════════════════════════
    // MOVEMENT COMMANDS (C.3) - With local preview
    // ═══════════════════════════════════════════════════════════════════════════

    fun sendMoveForward() {
        _state.update { s -> RobotReducer.applyLocalMove( s, forward = true ) }
        send(Outgoing.MoveForward)
    }

    fun sendMoveBackward() {
        _state.update { s -> RobotReducer.applyLocalMove( s, forward = false ) }
        send(Outgoing.MoveBackward)
    }

    fun sendTurnLeft() {
        _state.update { s -> RobotReducer.applyLocalTurn( s, left = true ) }
        send(Outgoing.TurnLeft)
    }

    fun sendTurnRight() {
        _state.update { s -> RobotReducer.applyLocalTurn( s, left = false ) }
        send(Outgoing.TurnRight)
    }

    fun placeObstacleDirect(obstacleId: Int, bottomLeftX: Int, bottomLeftY: Int, width: Int, height: Int, facing: RobotDirection) {
        val arena = _state.value.arena
        val maxW = arena?.width ?: ArenaConfig.GRID_SIZE
        val maxH = arena?.height ?: ArenaConfig.GRID_SIZE

        if (bottomLeftX < 0 || bottomLeftY < 0 ||
            bottomLeftX + width > maxW || bottomLeftY + height > maxH
        ) return

        val newObstacle = PlacedObstacle(protocolId = "B$obstacleId", obstacleId = obstacleId, bottomLeftX = bottomLeftX, bottomLeftY = bottomLeftY, width = width, height = height, facing = facing)
        _state.update { s ->
            val updated = s.placedObstacles.filterNot { it.obstacleId == obstacleId } + newObstacle
            s.copy(placedObstacles = updated, pendingObstacle = null, pendingPreview = null, dragPreview = null).withArenaDerivedFromPlacedObstacles()
        }
    }

    fun updatePlacedObstacleDirect(protocolId: String, bottomLeftX: Int, bottomLeftY: Int, facing: RobotDirection) {
        val arena = _state.value.arena
        val maxW = arena?.width ?: ArenaConfig.GRID_SIZE
        val maxH = arena?.height ?: ArenaConfig.GRID_SIZE

        val current = _state.value.placedObstacles.find { it.protocolId == protocolId } ?: return

        if (bottomLeftX < 0 || bottomLeftY < 0 ||
            bottomLeftX + current.width > maxW || bottomLeftY + current.height > maxH
        ) return

        val updatedObstacle = current.copy(
            bottomLeftX = bottomLeftX,
            bottomLeftY = bottomLeftY,
            facing = facing
        )

        _state.update { s ->
            val updated = s.placedObstacles.map {
                if (it.protocolId == protocolId) updatedObstacle else it
            }
            s.copy(placedObstacles = updated).withArenaDerivedFromPlacedObstacles()
        }
    }

    fun selectObstacle(protocolId: String){
        _state.update { s -> s.copy(selectedObstacleId = protocolId) }
    }

    fun pickObstacleToConfigure(obstacleId: Int) {
        // obstacleId 1..8
        _state.update { PlacementReducer.setPending(it, PendingObstacle(obstacleId = obstacleId)) }
    }

    fun updatePendingConfig(width: Int, height: Int, facing: RobotDirection?) {
        _state.update { s ->
            val p = s.pendingObstacle ?: return@update s
            val next = p.copy(width = width, height = height, facing = facing)
            PlacementReducer.setPending(s, next)
        }
    }

    fun cancelPending() {
        _state.update { PlacementReducer.setPending(it, null) }
    }

    fun previewPendingAt(bottomLeftX: Int, bottomLeftY: Int) {
        _state.update { s ->
            val p = s.pendingObstacle ?: return@update s
            val protocolId = buildProtocolIdForPending(s, p)
            val preview = PlacedObstacle(protocolId, p.obstacleId, bottomLeftX, bottomLeftY, p.width, p.height, p.facing)
            PlacementReducer.setPendingPreview(s, preview)
        }
    }

    fun commitPendingAt(bottomLeftX: Int, bottomLeftY: Int) {
        val s = _state.value
        val p = s.pendingObstacle ?: return

        val protocolId = buildProtocolIdForPending(s, p)
        val placed = PlacedObstacle(protocolId, p.obstacleId, bottomLeftX, bottomLeftY, p.width, p.height, p.facing)

        _state.update { s ->
            val next = PlacementReducer.commitPlaced(s, placed)
            next
        }
    }

    fun movePlaced(protocolId: String, bottomLeftX: Int, bottomLeftY: Int) {
        val s = _state.value
        val ob = s.placedObstacles.find { it.protocolId == protocolId } ?: return

        val moved = ob.copy(bottomLeftX = bottomLeftX, bottomLeftY = bottomLeftY)
        _state.update { st -> PlacementReducer.commitPlaced(st, moved) }
        _state.update { it.copy(dragPreview = null) }
    }

    fun previewMovePlaced(protocolId: String, bottomLeftX: Int, bottomLeftY: Int) {
        val s = _state.value
        val ob = s.placedObstacles.find { it.protocolId == protocolId } ?: return
        _state.update { it.copy(dragPreview = ob.copy(bottomLeftX = bottomLeftX, bottomLeftY = bottomLeftY)) }
    }

    fun removePlaced(protocolId: String) {
        _state.update { PlacementReducer.removePlaced(it, protocolId).copy(dragPreview = null) }
    }

    fun setPlacedFacing(protocolId: String, facing: RobotDirection) {
        _state.update { PlacementReducer.updateFacing(it, protocolId, facing) }
    }

    /**
     * Send robot position to remote device.
     */

    fun setRobotPose(blX: Int, blY: Int, w: Int, h: Int, facing: RobotDirection, alsoSend: Boolean = true) {
        _state.update { s ->
            val r0 = s.robot ?: RobotState(1, 1, 0)
            s.copy(
                robot = r0.copy(
                    x = blX,
                    y = blY,
                    directionDeg = DirectionUtil.toDegrees(facing),
                    robotX = w,
                    robotY = h
                )
            )
        }
    }

    private fun startRunTimer() {
        runTimerJob?.cancel()
        _state.update {
            it.copy(runSeconds = 0)
        }
        runTimerJob = viewModelScope.launch {
            while (isActive) {
                delay(1000)
                _state.update { state ->
                    state.copy(
                        runSeconds = state.runSeconds + 1
                    )
                }
            }
        }
    }

    private fun stopRunTimer(){
        runTimerJob?.cancel()
        runTimerJob = null
    }

    fun stopCurrentRun() {
        playbackJob?.cancel()
        playbackJob = null
        playbackQueue.clear()
        waitingForSnap = false
        currentSnapObstacleId = null
        stopRunTimer()
        _state.update { it.copy(executionMode = ExecutionMode.NONE) }
        log(LogEntry.Kind.INFO, "RUN STOPPED MANUALLY")
    }

    private fun startDemoExploration() {
        playbackJob?.cancel()
        playbackJob = null
        playbackQueue.clear()
        waitingForSnap = false
        currentSnapObstacleId = null

        resetObstacleImages()
        clearPlaybackPath()
        startRunTimer()
        _state.update { it.copy(executionMode = ExecutionMode.EXPLORATION) }

        _state.value.robot?.let { appendPathPoint(it.x, it.y) }

        log(LogEntry.Kind.OUT, """{"cmd":"START_EXPLORE", "demo":true}""")
        log(LogEntry.Kind.INFO, "STATE: Demo exploration started")

        playbackJob = viewModelScope.launch {
            // HX start: “communication bridge... synchronized in real time”
            delay(400)

            // Vithun: live path visualization
            moveForwardDemo(3)
            arcTurnDemo(left = false, front = true)
            moveForwardDemo(2)

            // Pause like SNAP / image detection moment
            waitingForSnap = true
            currentSnapObstacleId = "B1"
            log(LogEntry.Kind.INFO, "SNAP waiting: B1_R")
            delay(700)

            // Fake target detected + fake image received
            val fakeBytes = android.util.Base64.decode(
                "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",
                android.util.Base64.DEFAULT
            )

            _state.update { s ->
                val s2 = PlacementReducer.onTargetDetected(s, "B1", "39", RobotDirection.WEST)
                s2.copy(
                    obstacleImages = s2.obstacleImages + ("B1" to fakeBytes),
                    lastImageBytes = fakeBytes,
                    selectedObstacleId = "B1"
                )
            }
            log(LogEntry.Kind.INFO, "IMG: B1 -> 39 face=W bytes=${fakeBytes.size}")

            waitingForSnap = false
            currentSnapObstacleId = null

            // Continue path
            moveForwardDemo(2)
            arcTurnDemo(left = true, front = true)
            moveForwardDemo(2)

            // Second detection moment
            waitingForSnap = true
            currentSnapObstacleId = "B2"
            log(LogEntry.Kind.INFO, "SNAP waiting: B2_L")
            delay(900)

            // Fake second target detected + fake image received
            val fakeBytes2 = android.util.Base64.decode(
                "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",
                android.util.Base64.DEFAULT
            )

            _state.update { s ->
                val s2 = PlacementReducer.onTargetDetected(s, "B2", "38", RobotDirection.SOUTH)
                s2.copy(
                    obstacleImages = s2.obstacleImages + ("B2" to fakeBytes2),
                    lastImageBytes = fakeBytes2,
                    selectedObstacleId = "B2"
                )
            }
            log(LogEntry.Kind.INFO, "IMG: B2 -> 38 face=S bytes=${fakeBytes2.size}")

            waitingForSnap = false
            currentSnapObstacleId = null

            // Final movement
            moveForwardDemo(2)
            arcTurnDemo(left = false, front = true)
            moveForwardDemo(2)

            // HX ending: “smart car locator... navigates toward you autonomously”
            delay(500)
            handlePlaybackFinished()
        }
    }

    fun sendStartExploration() {
        if (demoMode) {
            startDemoExploration()
            return
        }

        val s = _state.value
        val arena = s.arena ?: return
        val robot = s.robot ?: return

        playbackJob?.cancel()
        playbackJob = null
        playbackQueue.clear()
        waitingForSnap = false
        currentSnapObstacleId = null
        fallbackImageObstacleIndex = 1

        // reset obstacle images / detected IDs
        resetObstacleImages()
        startRunTimer()

        val json = JsonProtocol.encodeStartExplore(
            arena = arena,
            robot = robot,
            obstacles = s.placedObstacles.sortedBy { it.obstacleId }
        )

        bt.sendLine(json)
        log(LogEntry.Kind.OUT, json)
        _state.update { it.copy(executionMode = ExecutionMode.EXPLORATION) }
    }

    fun sendStartFastestPath() {
        playbackJob?.cancel()
        playbackJob = null
        playbackQueue.clear()
        waitingForSnap = false
        currentSnapObstacleId = null
        fallbackImageObstacleIndex = 1

        startRunTimer()

        val json = JsonProtocol.encodeStartFastest()
        bt.sendLine(json)
        log(LogEntry.Kind.OUT, json)
        _state.update { it.copy(executionMode = ExecutionMode.FASTEST) }
    }

    /** Send a raw string (for debugging or unsupported commands) */
    fun sendRaw(line: String) = send(Outgoing.Raw(line))

    /** Initialize arena with default or custom dimensions */
    fun initializeArena(width: Int = ArenaState.DEFAULT_WIDTH, height: Int = ArenaState.DEFAULT_HEIGHT) {
        _state.update {
            it.copy(
                arena = ArenaState.empty(width, height),
                pendingObstacle = null,
                pendingPreview = null,
                placedObstacles = emptyList(),
                usedTargetObstacleIds = emptySet(),
            )
        }
    }

    private fun clearPlaybackPath() {
        _state.update { it.copy(playbackPath = emptyList()) }
    }

    private fun appendPathPoint(x: Int, y: Int) {
        _state.update { s ->
            val last = s.playbackPath.lastOrNull()
            if (last?.x == x && last.y == y) return@update s
            s.copy(playbackPath = s.playbackPath + GridPoint(x, y))
        }
    }

    private suspend fun moveForwardDemo(steps: Int, delayMs: Long = 180L) {
        repeat(steps) {
            _state.update { s -> RobotReducer.applyLocalMove(s, forward = true) }
            _state.value.robot?.let { appendPathPoint(it.x, it.y) }
            delay(delayMs)
        }
    }

    private suspend fun moveBackwardDemo(steps: Int, delayMs: Long = 180L) {
        repeat(steps) {
            _state.update { s -> RobotReducer.applyLocalMove(s, forward = false) }
            _state.value.robot?.let { appendPathPoint(it.x, it.y) }
            delay(delayMs)
        }
    }

    private suspend fun arcTurnDemo(left: Boolean, front: Boolean, delayMs: Long = 120L) {
        val shortSteps = 25 / 5
        val longSteps = 40 / 5

        if (front) {
            repeat(shortSteps) {
                _state.update { s -> RobotReducer.applyLocalMove(s, forward = true) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(delayMs)
            }
            repeat(longSteps) {
                _state.update { s -> RobotReducer.applySideShift(s, left = left) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(delayMs)
            }
        } else {
            repeat(longSteps) {
                _state.update { s -> RobotReducer.applyLocalMove(s, forward = false) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(delayMs)
            }
            repeat(shortSteps) {
                _state.update { s -> RobotReducer.applySideShift(s, left = left) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(delayMs)
            }
        }

        _state.update { s -> RobotReducer.applyLocalTurn(s, left = left) }
    }

    private fun resolveImageObstacleId(rawObstacleId: String?): String {
        val trimmed = rawObstacleId?.trim().orEmpty()

        if(trimmed.isNotEmpty()){
            return if (trimmed.startsWith("B")) trimmed else "B$trimmed"
        }

        val resolved = "B$fallbackImageObstacleIndex"
        fallbackImageObstacleIndex++
        return resolved
    }

    fun clearAllDetectedImages() {
        _state.update { state ->
            val updated = state.placedObstacles.map {
                it.copy(targetId = null)
            }

            state.copy(
                placedObstacles = updated,
                obstacleImages = emptyMap(),
                lastImageBytes = null,
                selectedObstacleId = null
            ).withArenaDerivedFromPlacedObstacles()
        }
    }

    fun resetObstacleImage(protocolId: String) {
        _state.update { s -> PlacementReducer.resetObstacleImage(s, protocolId) }
    }

    private fun resetObstacleImages() {
        _state.update { state ->
            val updated = state.placedObstacles.map {
                it.copy(targetId = null)
            }

            state.copy(
                placedObstacles = updated,
                obstacleImages = emptyMap(),
                lastImageBytes = null,
                selectedObstacleId = null
            ).withArenaDerivedFromPlacedObstacles()
        }
    }

    fun resetAll() {
        pendingMoves.clear()
        awaitingAck = false
        playbackJob?.cancel()
        playbackJob = null
        playbackQueue.clear()
        waitingForSnap = false
        currentSnapObstacleId = null
        fallbackImageObstacleIndex = 1
        stopRunTimer()

        _state.update {
            it.copy(
                robot = RobotState(x = 1, y = 1, directionDeg = 0),
                statusText = null,
                detections = emptyList(),
                lastDetection = null,
                placedObstacles = emptyList(),
                pendingObstacle = null,
                pendingPreview = null,
                dragPreview = null,
                usedTargetObstacleIds = emptySet(),
                playbackPath = emptyList(),
                obstacleImages = emptyMap(),
                selectedObstacleId = null,
                lastImageBytes = null
            ).withArenaDerivedFromPlacedObstacles()
        }
    }

    private fun parsePlaybackCommand(cmd: String): PlaybackCommand? {

        if (cmd.startsWith("SF")) {
            val cm = cmd.substring(2).toInt()
            return PlaybackCommand.MoveForward(cm / 5)
        }

        if (cmd.startsWith("SB")) {
            val cm = cmd.substring(2).toInt()
            return PlaybackCommand.MoveBackward(cm / 5)
        }

        if (cmd.matches(Regex("[LR][FB]\\d{3}"))) {

            val left = cmd[0] == 'L'
            val front = cmd[1] == 'F'

            return PlaybackCommand.ArcTurn(left, front)
        }

        if (cmd.startsWith("SNAP")) {

            val parts = cmd.split("_")
            val obstacle = parts[0].removePrefix("SNAP")
            val face = parts[1]

            return PlaybackCommand.Snap("B$obstacle", face)
        }

        return null
    }

    private fun runPlaybackQueueIfIdle() {
        if (waitingForSnap) return
        if (playbackJob?.isActive == true) return
        if (playbackQueue.isEmpty()) return

        val next = playbackQueue.removeFirst()
        playbackJob = viewModelScope.launch {
            executePlaybackCommand(next)
            playbackJob = null
            runPlaybackQueueIfIdle()
        }
    }

    private suspend fun executePlaybackCommand(cmd: PlaybackCommand) {
        when (cmd) {
            is PlaybackCommand.MoveForward -> {
                repeat(cmd.grids.coerceAtLeast(0)) {
                    _state.update { s -> RobotReducer.applyLocalMove(s, forward = true) }
                    delay(120)
                }
            }
            is PlaybackCommand.MoveBackward -> {
                repeat(cmd.grids.coerceAtLeast(0)) {
                    _state.update { s -> RobotReducer.applyLocalMove(s, forward = false) }
                    delay(120)
                }
            }

            is PlaybackCommand.ArcTurn -> {
                executeArcTurn(cmd.left, cmd.front)
            }

            is PlaybackCommand.Snap -> {
                waitingForSnap = true
                currentSnapObstacleId = cmd.obstacleId
                log(LogEntry.Kind.INFO, "SNAP waiting: ${cmd.obstacleId}_${cmd.face}")
            }

            PlaybackCommand.Finish -> {
                handlePlaybackFinished()
            }
        }
    }

    private suspend fun executeArcTurn(left: Boolean, front: Boolean) {
        val shortSteps = 25 / 5
        val longSteps = 40 / 5

        if (front) {
            repeat(shortSteps) {
                _state.update { s -> RobotReducer.applyLocalMove(s, forward = true) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(120)
            }

            // turn before the sideways movement
            _state.update { s -> RobotReducer.applyLocalTurn(s, left = left) }

            repeat(longSteps) {
                _state.update { s -> RobotReducer.applyLocalMove(s, forward = true) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(120)
            }
        } else {
            repeat(longSteps) {
                _state.update { s -> RobotReducer.applyLocalMove(s, forward = false) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(120)
            }

            _state.update { s -> RobotReducer.applyLocalTurn(s, left = left) }

            repeat(shortSteps) {
                _state.update { s -> RobotReducer.applyLocalMove(s, forward = false) }
                _state.value.robot?.let { appendPathPoint(it.x, it.y) }
                delay(120)
            }
        }
    }

    private fun send(msg: Outgoing) {
        if (msg.isMoveCommand()) {
            if (awaitingAck) {
                pendingMoves.add(msg)
                log(LogEntry.Kind.INFO, "QUEUED: ${ProtocolEncoder.encode(msg)}")
                return
            }
            awaitingAck = true
        }

        val line = ProtocolEncoder.encode(msg)
        bt.sendLine(line)
        log(LogEntry.Kind.OUT, line)
    }

    private fun handlePlaybackFinished() {
        playbackJob?.cancel()
        playbackJob = null
        playbackQueue.clear()
        waitingForSnap = false
        currentSnapObstacleId = null
        stopRunTimer()
        _state.update { it.copy(executionMode = ExecutionMode.NONE) }
        log(LogEntry.Kind.INFO, "PLAYBACK FINISHED")
    }

    private fun handleBluetoothEvent(ev: BluetoothManager.Event) {
        when (ev) {
            is BluetoothManager.Event.DiscoveryStarted -> {
                _state.update { s -> ConnectionReducer.onDiscoveryStarted(s) }
                ev.message?.let { log(LogEntry.Kind.INFO, it) }
            }

            is BluetoothManager.Event.DeviceFound -> {
                val d = BtDeviceMapper.toBtDevice(ev.device)
                _state.update { s -> DiscoveryReducer.onDeviceFound(s, d) }
            }

            is BluetoothManager.Event.ImageReceived -> {
                val protocolId = resolveImageObstacleId(ev.obstacleId)

                log(
                    LogEntry.Kind.INFO,
                    "IMG: $protocolId -> ${ev.targetId} face=${ev.face ?: "-"} bytes=${ev.bytes.size}"
                )

                _state.update { s ->
                    val faceDir = ev.face?.let { DirectionUtil.fromProtocolToken(it) }
                    val s2 = PlacementReducer.onTargetDetected(s, protocolId, ev.targetId, faceDir)
                    s2.copy(
                        obstacleImages = s2.obstacleImages + (ev.obstacleId to ev.bytes),
                        lastImageBytes = ev.bytes,
                        selectedObstacleId = ev.obstacleId
                    )
                }

                if (waitingForSnap) {
                    if (currentSnapObstacleId == null || protocolId == currentSnapObstacleId) {
                        waitingForSnap = false
                        currentSnapObstacleId = null
                        runPlaybackQueueIfIdle()
                    }
                }
            }


            is BluetoothManager.Event.DiscoveryFinished -> {
                _state.update { s -> ConnectionReducer.onDiscoveryFinished(s) }
                log(LogEntry.Kind.INFO, "Scan finished. found=${ev.foundCount}")
            }

            is BluetoothManager.Event.StateChanged -> {
                _state.update { s -> ConnectionReducer.onStateChanged(s, ev) }
                ev.message?.let { log(LogEntry.Kind.INFO, "STATE: $it") }
            }

            is BluetoothManager.Event.Connected -> {
                log(LogEntry.Kind.INFO, "CONNECTED: ${ev.label}")
            }

            is BluetoothManager.Event.Disconnected -> {
                log(LogEntry.Kind.INFO, "DISCONNECTED: ${ev.reason} ${ev.message ?: ""}".trim())
                val permissionDenied =
                    ev.message?.contains("BLUETOOTH_CONNECT", ignoreCase = true) == true ||
                            ev.message?.contains("permission", ignoreCase = true) == true

                val shouldAutoListen = autoListenOnDisconnect &&
                        !permissionDenied &&
                        bt.mode != BluetoothManager.Mode.CLIENT

                if (shouldAutoListen) {
                    bt.startServer()
                }
            }

            is BluetoothManager.Event.LineReceived -> {
                log(LogEntry.Kind.IN, ev.line)
                handleIncomingLine(ev.line)
            }

            is BluetoothManager.Event.EchoReceived -> {
                log(LogEntry.Kind.INFO, "ECHO: ${ev.line}")
            }

            is BluetoothManager.Event.SendRejected -> {
                val kind =
                    if (ev.reason == BluetoothManager.SendRejectReason.IO_ERROR) LogEntry.Kind.ERROR
                    else LogEntry.Kind.INFO

                log(kind, "SEND_REJECTED: ${ev.reason} ${ev.message ?: ""}".trim())
            }

            is BluetoothManager.Event.Log -> {
                log(LogEntry.Kind.INFO, ev.message)
            }
        }
    }


    private fun handleIncomingLine(line: String) {
        val raw = line.trim()
        if (raw == "A") {
            awaitingAck = false
            log(LogEntry.Kind.INFO, "ACK received")

            val next = if (pendingMoves.isNotEmpty()) pendingMoves.removeFirst() else null
            if (next != null) send(next)
            return
        }

        when (val msg = ProtocolParser.parse(line)) {
            // C.10: Robot position update
            is Incoming.RobotPosition -> handleRobotPosition(msg)

            // C.9: Target detection
            is Incoming.TargetDetected -> handleTargetDetected(msg)

            // C.4: Status message
            is Incoming.StatusUpdate -> handleStatusUpdate(msg)

            // Arena updates
            is Incoming.GridHex -> handleGridHex(msg)
            is Incoming.GridBinary -> handleGridBinary(msg)
            is Incoming.ArenaResize -> handleArenaResize(msg)

            is Incoming.CommandBatch -> {
                msg.commands
                    .mapNotNull { parsePlaybackCommand(it) }
                    .forEach { playbackQueue.add(it) }
                runPlaybackQueueIfIdle()
            }
            is Incoming.PlaybackFinished -> handlePlaybackFinished()

            // Raw/unrecognized
            is Incoming.Raw -> { /* Already logged */ }
            is Incoming.ObstacleRemoved -> Unit
            is Incoming.ObstacleUpdate -> Unit
        }
    }

    /**
     * C.10: Handle robot position update.
     * Format: "ROBOT,<x>,<y>,<direction>"
     */
    private fun handleRobotPosition(msg: Incoming.RobotPosition) {
        _state.update { s -> RobotReducer.onIncomingRobotPosition(s, msg.x, msg.y, DirectionUtil.toDegrees(msg.direction)) }
    }

    /**
     * C.9: Handle target detection.
     * Format: "TARGET,<obstacle>,<targetId>[,<face>]"
     * Updates the obstacle block to display the target ID.
     */
    private fun handleTargetDetected(msg: Incoming.TargetDetected) {
        val protocolId = if (msg.obstacleId.startsWith("B")) msg.obstacleId else "B${msg.obstacleId}"
        if (msg.targetId.equals("TIMEOUT", ignoreCase = true)) {
            log(LogEntry.Kind.INFO, "TARGET TIMEOUT: $protocolId")

            if (waitingForSnap && (currentSnapObstacleId == null || protocolId == currentSnapObstacleId)) {
                waitingForSnap = false
                currentSnapObstacleId = null
                runPlaybackQueueIfIdle()
            }
            return
        }
        _state.update { s -> PlacementReducer.onTargetDetected(s, protocolId, msg.targetId, msg.face) }
        log(LogEntry.Kind.INFO, "TARGET: ${msg.obstacleId} -> ${msg.targetId}")

        if (waitingForSnap && (currentSnapObstacleId == null || protocolId == currentSnapObstacleId)) {
            waitingForSnap = false
            currentSnapObstacleId = null
            runPlaybackQueueIfIdle()
        }
    }

    /**
     * C.4: Handle status update message.
     * Format: "MSG,[status text]"
     */
    private fun handleStatusUpdate(msg: Incoming.StatusUpdate) {
        _state.update { it.copy(statusText = msg.message) }
    }

    private fun handleGridHex(msg: Incoming.GridHex) {
        var decodeFailed = false
        _state.update { s ->
            val next = ArenaReducer.onGridHex(s, msg)
            if (next == s) decodeFailed = true
            next
        }
        if (decodeFailed) {
            log(LogEntry.Kind.ERROR, "Failed to decode grid hex length=${msg.hex.length}")
        }
    }

    private fun handleGridBinary(msg: Incoming.GridBinary) {
        _state.update { s -> ArenaReducer.onGridBinary(s, msg) }
    }

    private fun handleArenaResize(msg: Incoming.ArenaResize) {
        _state.update { s -> ArenaReducer.onArenaResize(s, msg) }
    }

    private fun buildProtocolIdForPending(state: AppState, pending: PendingObstacle): String {
        return "B${pending.obstacleId}"
    }

    private fun log(kind: LogEntry.Kind, text: String) {
        _state.update { s -> LogReducer.append(s, kind, text) }
    }
}
