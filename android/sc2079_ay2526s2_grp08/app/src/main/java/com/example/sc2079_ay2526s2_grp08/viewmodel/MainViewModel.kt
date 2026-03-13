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

/**
 * Main ViewModel - the single point of interaction between UI and backend.
 *
 * UI layer should call this; UI must NOT touch BluetoothManager directly.
 * All state is exposed via [state] StateFlow which UI observes.
 *
 * MDP ARCM Checklist mapping:
 * - C.1: Bluetooth transmit/receive (via send* methods and state.log)
 * - C.2: Device scanning/selection (via connectToDevice, getPairedDevices)
 * - C.3: Robot movement (via sendMoveForward, sendTurnLeft, etc.)
 * - C.4: Status display (via state.statusText)
 * - C.5: Arena display (via state.arena)
 * - C.6: Obstacle placement (via sendAddObstacle, sendRemoveObstacle)
 * - C.7: Target face annotation (via sendSetObstacleFace)
 * - C.8: Robust connectivity (handled by BluetoothManager)
 * - C.9: Target ID display (handled by handleTargetDetected)
 * - C.10: Robot position update (handled by handleRobotPosition)
 */
class MainViewModel(
    private val bt: BluetoothManager
) : ViewModel() {

    private var playbackJob: Job? = null
    private val _state = MutableStateFlow(AppState())
    private var autoListenOnDisconnect: Boolean = true
    private val playbackQueue = ArrayDeque<PlaybackCommand>()
    private var waitingForSnap = false
    private var currentSnapObstacleId: String? = null
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

    fun sendStartExploration() {
        val s = _state.value
        val arena = s.arena ?: return
        val robot = s.robot ?: return

        playbackJob?.cancel()
        playbackJob = null
        playbackQueue.clear()
        waitingForSnap = false
        currentSnapObstacleId = null

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
        startRunTimer()
        bt.sendLine("""{"cmd":"START_FAST"}""")
        log(LogEntry.Kind.OUT, """{"cmd":"START_FAST"}""")
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
            // FR / FL
            repeat(shortSteps) {
                _state.update { s ->
                    RobotReducer.applyLocalMove(s, forward = true)
                }
                delay(120)
            }

            repeat(longSteps) {
                _state.update { s ->
                    RobotReducer.applySideShift(s, left = left)
                }
                delay(120)
            }

        } else {
            // BR / BL
            repeat(longSteps) {
                _state.update { s ->
                    RobotReducer.applyLocalMove(s, forward = false)
                }
                delay(120)
            }

            repeat(shortSteps) {
                _state.update { s ->
                    RobotReducer.applySideShift(s, left = left)
                }
                delay(120)
            }
        }

        _state.update { s ->
            RobotReducer.applyLocalTurn(s, left = left)
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
                val protocolId = if (ev.obstacleId.startsWith("B")) ev.obstacleId else "B${ev.obstacleId}"

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
