package com.example.sc2079_ay2526s2_grp08.viewmodel

import androidx.lifecycle.ViewModel
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.bluetooth.BtDeviceMapper
import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.domain.util.DirectionUtil
import com.example.sc2079_ay2526s2_grp08.protocol.*
import com.example.sc2079_ay2526s2_grp08.viewmodel.reducers.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

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

    private val _state = MutableStateFlow(AppState())
    private var autoListenOnDisconnect: Boolean = true
    val state: StateFlow<AppState> = _state

    // Counter for generating obstacle IDs
    private var obstacleCounter = 0

    init {
        bt.onEvent = { ev -> handleBluetoothEvent(ev) }
    }

    fun setAutoListenOnDisconnect(enabled: Boolean) {
        autoListenOnDisconnect = enabled
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
        val adapter = android.bluetooth.BluetoothAdapter.getDefaultAdapter()
        val remote = adapter?.getRemoteDevice(device.address)
        if (remote != null) bt.connect(remote)
        else log(LogEntry.Kind.ERROR, "No adapter / invalid address: ${device.address}")
    }

    fun refreshPairedDevices() {
        val paired = bt.getPairedDevices().map { BtDeviceMapper.toBtDevice(it, bonded = true) }
        _state.update { s -> DiscoveryReducer.setPairedDevices(s, paired) }
    }

    /** Get list of paired Bluetooth devices */
    fun getPairedDevices(): List<android.bluetooth.BluetoothDevice> {
        return bt.getPairedDevices()
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

    fun clearScanResults() {
        bt.clearDiscoveredDevices()
        _state.update { s -> DiscoveryReducer.clearScanResults(s) }
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

    fun sendMoveForward(steps: Int) {
        repeat(steps.coerceAtLeast(0)){
            _state.update { s -> RobotReducer.applyLocalMove(s, forward = true) }
        }
        send(Outgoing.MoveForwardSteps(steps))
    }

    fun sendMoveBackward(steps: Int) {
        repeat(steps.coerceAtLeast(0)){
            _state.update { s -> RobotReducer.applyLocalMove(s, forward = false) }
        }
        send(Outgoing.MoveBackwardSteps(steps))
    }

    fun sendTurnDegrees(degrees: Int) {
        _state.update { s -> RobotReducer.applyLocalTurnDegrees(s, degrees) }
        send(Outgoing.TurnDegrees(degrees))
    }


    // ═══════════════════════════════════════════════════════════════════════════
    // OBSTACLE MANAGEMENT (C.6) - With local state + Bluetooth send
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Place or move an obstacle to position (x, y).
     * Updates local state AND sends via Bluetooth.
     * Use this for touch-to-place or drag interactions.
     *
     * @param id Obstacle number (1-8)
     * @param x Grid x-coordinate
     * @param y Grid y-coordinate
     */
    fun placeOrMoveObstacle(id: Int, x: Int, y: Int) {
        val obstacleId = "B$id"
        _state.update { s -> ObstacleReducer.placeOrMoveObstacle(s, id, x, y) }
        send(Outgoing.AddObstacle(obstacleId, x, y))
    }

    /**
     * Add obstacle at position (x, y) with given string ID.
     * Also updates local state.
     */
    fun sendAddObstacle(obstacleId: String, x: Int, y: Int) {
        val id = obstacleId.removePrefix("B").toIntOrNull() ?: run {
            obstacleCounter++
            obstacleCounter
        }
        placeOrMoveObstacle(id, x, y)
    }

    /**
     * Add obstacle at position with auto-generated ID (B1, B2, etc.)
     * Returns the obstacle ID string.
     */
    fun sendAddObstacle(x: Int, y: Int): String {
        obstacleCounter++
        val id = obstacleCounter.coerceIn(1, ArenaConfig.MAX_OBSTACLES)
        placeOrMoveObstacle(id, x, y)
        return "B$id"
    }

    /**
     * Remove obstacle by numeric ID (1-8).
     * Updates local state AND sends via Bluetooth.
     */
    fun removeObstacle(id: Int) {
        _state.update { s -> ObstacleReducer.removeObstacle(s, id) }
        send(Outgoing.RemoveObstacle("B$id"))
    }

    /**
     * Remove obstacle by string ID (e.g., "B1").
     */
    fun sendRemoveObstacle(obstacleId: String) {
        val id = obstacleId.removePrefix("B").toIntOrNull() ?: return
        removeObstacle(id)
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // TARGET FACE ANNOTATION (C.7)
    // ═══════════════════════════════════════════════════════════════════════════

    /**
     * Set which face of an obstacle has the target image.
     * Updates local state AND sends via Bluetooth.
     *
     * @param id Obstacle number (1-8)
     * @param facing Direction the target face is pointing
     */
    fun setObstacleFacing(id: Int, facing: RobotDirection?) {
        _state.update { s -> ObstacleReducer.setObstacleFacing(s, id, facing) }
        if (facing != null) {
            send(Outgoing.SetObstacleFace("B$id", facing))
        }
    }

    /**
     * Set obstacle face by string ID.
     */
    fun sendSetObstacleFace(obstacleId: String, face: RobotDirection) {
        val id = obstacleId.removePrefix("B").toIntOrNull() ?: return
        setObstacleFacing(id, face)
    }

    /**
     * Send robot position to remote device.
     */
    fun sendSetRobotPosition(x: Int, y: Int, direction: RobotDirection) {
        send(Outgoing.SetRobotPosition(x, y, direction))
    }

    fun sendRequestSync() = send(Outgoing.RequestSync)

    fun sendStartExploration() = send(Outgoing.StartExploration)
    fun sendStartFastestPath() = send(Outgoing.StartFastestPath)
    fun sendStop() = send(Outgoing.StopRobot)

    /** Stored configurable button commands */
    private val configButtonCommands = mutableMapOf(
        1 to "F1_DEFAULT",
        2 to "F2_DEFAULT"
    )

    /** Configure a button command (persisted locally) */
    fun setConfigButtonCommand(buttonId: Int, command: String) {
        configButtonCommands[buttonId] = command
    }

    /** Get configured command for a button */
    fun getConfigButtonCommand(buttonId: Int): String {
        return configButtonCommands[buttonId] ?: ""
    }

    /** Send the configured command for a button */
    fun sendConfigButton(buttonId: Int) {
        val command = configButtonCommands[buttonId] ?: return
        send(Outgoing.ConfigButton(buttonId, command))
    }

    fun sendStatus(status: String) = send(Outgoing.SendStatus(status))

    /** Send a raw string (for debugging or unsupported commands) */
    fun sendRaw(line: String) = send(Outgoing.Raw(line))

    /** Initialize arena with default or custom dimensions */
    fun initializeArena(width: Int = ArenaState.DEFAULT_WIDTH, height: Int = ArenaState.DEFAULT_HEIGHT) {
        obstacleCounter = 0
        _state.update { it.copy(arena = ArenaState.empty(width, height)) }
    }

    /** Set robot position locally (without sending) */
    fun setLocalRobotPosition(x: Int, y: Int, direction: RobotDirection) {
        _state.update { s -> RobotReducer.setRobotPosition(s, x, y, DirectionUtil.toDegrees(direction)) }
    }

    /** Clear all detections */
    fun clearDetections() {
        _state.update { it.copy(detections = emptyList(), lastDetection = null) }
    }

    /** Clear path execution state */
    fun clearPath() {
        _state.update { s -> PathReducer.clearPath(s) }
    }
    
    /** Toggle path playback */
    fun togglePathPlayback() {
        _state.update { s -> PathReducer.togglePlayback(s) }
    }

    /** Step to next pose in path */
    fun stepPathForward() {
        _state.update { s -> PathReducer.stepForward(s) }
    }

    /** Step to previous pose in path */
    fun stepPathBackward() {
        _state.update { s -> PathReducer.stepBackward(s) }
    }

    /** Clear message log */
    fun clearLog() {
        _state.update { s -> LogReducer.clear(s) }
    }

    private fun send(msg: Outgoing) {
        val line = ProtocolEncoder.encode(msg)
        bt.sendLine(line)
        log(LogEntry.Kind.OUT, line)
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
                if (autoListenOnDisconnect) {
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

            // Obstacle updates (echoed from AMD Tool)
            is Incoming.ObstacleUpdate -> handleObstacleUpdate(msg)
            is Incoming.ObstacleRemoved -> handleObstacleRemoved(msg)

            // Path execution
            is Incoming.PathSequence -> handlePathSequence(msg)
            is Incoming.PathStep -> handlePathStep(msg)
            is Incoming.PathComplete -> handlePathComplete()
            is Incoming.PathAbort -> handlePathAbort()

            // Sync request
            is Incoming.RequestSync -> handleRequestSync()

            // Raw/unrecognized
            is Incoming.Raw -> { /* Already logged */ }
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
        _state.update { s -> ObstacleReducer.onTargetDetected(s, msg) }
        log(LogEntry.Kind.INFO, "TARGET: ${msg.obstacleId} -> ${msg.targetId}" +
                (msg.face?.let { " (face: $it)" } ?: ""))
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

    private fun handleObstacleUpdate(msg: Incoming.ObstacleUpdate) {
        _state.update { s -> ObstacleReducer.onIncomingObstacleUpdate(s, msg) }
    }

    private fun handleObstacleRemoved(msg: Incoming.ObstacleRemoved) {
        _state.update { s -> ObstacleReducer.onIncomingObstacleRemoved(s, msg) }
    }

    private fun handlePathSequence(msg: Incoming.PathSequence) {
        _state.update { s -> PathReducer.onPathSequence(s, msg) }
        log(LogEntry.Kind.INFO, "PATH RECEIVED: ${msg.poses.size} poses")
    }

    private fun handlePathStep(msg: Incoming.PathStep) {
        _state.update { s -> PathReducer.onPathStep(s, msg) }
    }

    private fun handlePathComplete() {
        _state.update { s -> PathReducer.onPathComplete(s) }
        log(LogEntry.Kind.INFO, "PATH COMPLETE")
    }

    private fun handlePathAbort() {
        _state.update { s -> PathReducer.onPathAbort(s) }
        log(LogEntry.Kind.INFO, "PATH ABORTED")
    }

    private fun handleRequestSync() {
        // Remote requested sync - send current state
        val s = _state.value
        s.robot?.let {
            send(Outgoing.SetRobotPosition(it.x, it.y, it.robotDirection))
        }
        // Send obstacles
        s.arena?.getObstacles()?.forEach { (x, y, id) ->
            val obstacleId = id?.let { "B$it" } ?: "B${x}_${y}"
            send(Outgoing.AddObstacle(obstacleId, x, y))
        }
    }


    private fun log(kind: LogEntry.Kind, text: String) {
        _state.update { s -> LogReducer.append(s, kind, text) }
    }

    fun assignGroupIdFromCell(cellX: Int, cellY: Int, groupId: Int) {
        var tagged = false
        _state.update { s ->
            val (next, ok) = TaggingReducer.assignGroupIdFromCell(s, cellX, cellY, groupId)
            tagged = ok
            next
        }
        if (!tagged) {
            log(LogEntry.Kind.INFO, "No obstacle at ($cellX,$cellY) to tag.")
        }
    }

    fun setGroupMeta(groupId: Int, imageId: String?, facing: RobotDirection?) {
        _state.update { s -> TaggingReducer.setGroupMeta(s, groupId, imageId, facing) }
    }

    fun sendTaggedObstaclesToAlgo() {
        val s = _state.value
        for (r in s.taggedObstacleRects) {
            val meta = s.obstacleGroupMeta[r.groupId]
            send(
                Outgoing.TaggedObstacleRect(
                    groupId = r.groupId,
                    bottomLeftX = r.bottomLeftX,
                    bottomLeftY = r.bottomLeftY,
                    width = r.width,
                    height = r.height,
                    imageId = meta?.imageId,
                    facing = meta?.facing
                )
            )
        }
    }
}
