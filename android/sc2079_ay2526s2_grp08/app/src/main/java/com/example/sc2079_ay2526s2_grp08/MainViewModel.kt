package com.example.sc2079_ay2526s2_grp08

import androidx.lifecycle.ViewModel
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.protocol.*
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
    val state: StateFlow<AppState> = _state

    // Counter for generating obstacle IDs
    private var obstacleCounter = 0

    init {
        bt.onEvent = { ev -> handleBluetoothEvent(ev) }
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
    fun connectToDevice(device: android.bluetooth.BluetoothDevice) {
        bt.connect(device)
    }

    /** Get list of paired Bluetooth devices */
    fun getPairedDevices(): List<android.bluetooth.BluetoothDevice> {
        return bt.getPairedDevices()
    }

    /** Check if Bluetooth is supported on this device */
    fun isBluetoothSupported(): Boolean = bt.isSupported()

    /** Check if Bluetooth is enabled */
    fun isBluetoothEnabled(): Boolean = bt.isEnabled()

    fun sendMoveForward() = send(Outgoing.MoveForward)
    fun sendMoveBackward() = send(Outgoing.MoveBackward)
    fun sendTurnLeft() = send(Outgoing.TurnLeft)
    fun sendTurnRight() = send(Outgoing.TurnRight)

    fun sendMoveForward(steps: Int) = send(Outgoing.MoveForwardSteps(steps))
    fun sendMoveBackward(steps: Int) = send(Outgoing.MoveBackwardSteps(steps))
    fun sendTurnDegrees(degrees: Int) = send(Outgoing.TurnDegrees(degrees))

    /**
     * Add obstacle at position (x, y) with given ID.
     * Also updates local arena state.
     */
    fun sendAddObstacle(obstacleId: String, x: Int, y: Int) {
        send(Outgoing.AddObstacle(obstacleId, x, y))
        // Update local state
        updateLocalObstacle(obstacleId, x, y, add = true)
    }

    /**
     * Add obstacle at position with auto-generated ID (B1, B2, etc.)
     */
    fun sendAddObstacle(x: Int, y: Int): String {
        obstacleCounter++
        val obstacleId = "B$obstacleCounter"
        sendAddObstacle(obstacleId, x, y)
        return obstacleId
    }

    /**
     * Remove obstacle by ID.
     * Also updates local arena state.
     */
    fun sendRemoveObstacle(obstacleId: String) {
        send(Outgoing.RemoveObstacle(obstacleId))
        // Update local state - find and remove obstacle
        removeLocalObstacle(obstacleId)
    }

    /**
     * Set which face of an obstacle has the target image.
     */
    fun sendSetObstacleFace(obstacleId: String, face: RobotDirection) {
        send(Outgoing.SetObstacleFace(obstacleId, face))
        // Update local state
        updateLocalObstacleFace(obstacleId, face)
    }

    /**
     * Send robot position to remote device.
     */
    fun sendSetRobotPosition(x: Int, y: Int, direction: RobotDirection) {
        send(Outgoing.SetRobotPosition(x, y, direction))
    }

    fun sendRequestArenaInfo() = send(Outgoing.RequestArenaInfo)

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
        _state.update { s ->
            s.copy(robot = RobotState(
                x = x,
                y = y,
                directionDeg = directionToDegrees(direction),
                robotX = s.robot?.robotX ?: 3,
                robotY = s.robot?.robotY ?: 3
            ))
        }
    }

    /** Clear all detections */
    fun clearDetections() {
        _state.update { it.copy(detections = emptyList(), lastDetection = null) }
    }

    /** Clear path execution state */
    fun clearPath() {
        _state.update { it.copy(pathExecution = PathExecutionState()) }
    }

    /** Set path playback speed */
    fun setPathSpeed(speed: Float) {
        _state.update { s ->
            s.copy(pathExecution = s.pathExecution.copy(speed = speed.coerceIn(0.1f, 10f)))
        }
    }

    /** Toggle path playback */
    fun togglePathPlayback() {
        _state.update { s ->
            s.copy(pathExecution = s.pathExecution.copy(isPlaying = !s.pathExecution.isPlaying))
        }
    }

    /** Step to next pose in path */
    fun stepPathForward() {
        _state.update { s ->
            val path = s.pathExecution
            if (path.currentIndex < path.poses.lastIndex) {
                val nextIndex = path.currentIndex + 1
                val pose = path.poses[nextIndex]
                s.copy(
                    pathExecution = path.copy(currentIndex = nextIndex),
                    robot = RobotState(pose.x, pose.y, pose.directionDeg, s.robot?.robotX ?: 3, s.robot?.robotY ?: 3)
                )
            } else s
        }
    }

    /** Step to previous pose in path */
    fun stepPathBackward() {
        _state.update { s ->
            val path = s.pathExecution
            if (path.currentIndex > 0) {
                val prevIndex = path.currentIndex - 1
                val pose = path.poses[prevIndex]
                s.copy(
                    pathExecution = path.copy(currentIndex = prevIndex),
                    robot = RobotState(pose.x, pose.y, pose.directionDeg, s.robot?.robotX ?: 3, s.robot?.robotY ?: 3)
                )
            } else s
        }
    }

    /** Clear message log */
    fun clearLog() {
        _state.update { it.copy(log = emptyList()) }
    }

    private fun send(msg: Outgoing) {
        val line = ProtocolEncoder.encode(msg)
        bt.sendLine(line)
        appendLog(LogEntry.Kind.OUT, line)
    }

    private fun handleBluetoothEvent(ev: BluetoothManager.Event) {
        when (ev) {
            is BluetoothManager.Event.StateChanged -> {
                _state.update {
                    it.copy(
                        mode = ev.mode,
                        conn = ev.state,
                        statusText = ev.message ?: it.statusText
                    )
                }
                ev.message?.let { appendLog(LogEntry.Kind.INFO, "STATE: $it") }
            }

            is BluetoothManager.Event.Connected -> {
                appendLog(LogEntry.Kind.INFO, "CONNECTED: ${ev.label}")
            }

            is BluetoothManager.Event.Disconnected -> {
                appendLog(LogEntry.Kind.INFO, "DISCONNECTED: ${ev.reason} ${ev.message ?: ""}".trim())
            }

            is BluetoothManager.Event.LineReceived -> {
                appendLog(LogEntry.Kind.IN, ev.line)
                handleIncomingLine(ev.line)
            }

            is BluetoothManager.Event.EchoReceived -> {
                appendLog(LogEntry.Kind.INFO, "ECHO: ${ev.line}")
            }

            is BluetoothManager.Event.SendRejected -> {
                appendLog(
                    if (ev.reason == BluetoothManager.SendRejectReason.IO_ERROR) LogEntry.Kind.ERROR else LogEntry.Kind.INFO,
                    "SEND_REJECTED: ${ev.reason} ${ev.message ?: ""}".trim()
                )
            }

            is BluetoothManager.Event.Log -> appendLog(LogEntry.Kind.INFO, ev.message)
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
        _state.update { s ->
            s.copy(robot = RobotState(
                x = msg.x,
                y = msg.y,
                directionDeg = msg.directionDeg,
                robotX = s.robot?.robotX ?: 3,
                robotY = s.robot?.robotY ?: 3
            ))
        }
    }

    /**
     * C.9: Handle target detection.
     * Format: "TARGET,<obstacle>,<targetId>[,<face>]"
     * Updates the obstacle block to display the target ID.
     */
    private fun handleTargetDetected(msg: Incoming.TargetDetected) {
        _state.update { s ->
            // Find the obstacle in the arena and update its imageId
            val arena = s.arena ?: return@update s

            // Search for the obstacle by ID and update it
            val updatedCells = arena.cells.mapIndexed { idx, cell ->
                // Check if this cell has the matching obstacle ID
                // Note: obstacleId in Cell is Int?, but msg.obstacleId is String
                val cellObstacleId = cell.obstacleId?.toString() ?: ""
                if (cell.isObstacle && (cellObstacleId == msg.obstacleId || "B$cellObstacleId" == msg.obstacleId)) {
                    cell.copy(
                        imageId = msg.targetId,
                        targetDirection = msg.face ?: cell.targetDirection
                    )
                } else {
                    cell
                }
            }

            // Also add to detections list
            val detection = ImageDetection(
                imageId = msg.targetId,
                label = "Obstacle ${msg.obstacleId}"
            )
            val detections = (s.detections + detection).takeLast(100)

            s.copy(
                arena = arena.copy(cells = updatedCells),
                detections = detections,
                lastDetection = detection
            )
        }

        appendLog(LogEntry.Kind.INFO, "TARGET: ${msg.obstacleId} -> ${msg.targetId}" +
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
        val width = _state.value.arena?.width ?: ArenaState.DEFAULT_WIDTH
        val height = _state.value.arena?.height ?: ArenaState.DEFAULT_HEIGHT
        val obstacles = decodeHexGrid(msg.hex, width, height)
        if (obstacles != null) {
            _state.update { it.copy(arena = ArenaState.fromObstacleArray(width, height, obstacles)) }
        } else {
            appendLog(LogEntry.Kind.ERROR, "Failed to decode grid hex length=${msg.hex.length}")
        }
    }

    private fun handleGridBinary(msg: Incoming.GridBinary) {
        _state.update { it.copy(arena = ArenaState.fromObstacleArray(msg.width, msg.height, msg.cells)) }
    }

    private fun handleArenaResize(msg: Incoming.ArenaResize) {
        _state.update { s ->
            val oldArena = s.arena
            if (oldArena == null) {
                s.copy(arena = ArenaState.empty(msg.width, msg.height))
            } else {
                val newCells = MutableList(msg.width * msg.height) { Cell.EMPTY }
                for (y in 0 until minOf(oldArena.height, msg.height)) {
                    for (x in 0 until minOf(oldArena.width, msg.width)) {
                        newCells[y * msg.width + x] = oldArena.getCell(x, y)
                    }
                }
                s.copy(arena = ArenaState(msg.width, msg.height, newCells))
            }
        }
    }

    private fun handleObstacleUpdate(msg: Incoming.ObstacleUpdate) {
        updateLocalObstacle(msg.obstacleId, msg.x, msg.y, add = true, face = msg.targetFace)
    }

    private fun handleObstacleRemoved(msg: Incoming.ObstacleRemoved) {
        removeLocalObstacle(msg.obstacleId)
    }

    private fun handlePathSequence(msg: Incoming.PathSequence) {
        _state.update { s ->
            s.copy(pathExecution = PathExecutionState(
                poses = msg.poses,
                currentIndex = -1,
                isPlaying = false,
                speed = s.pathExecution.speed
            ))
        }
        appendLog(LogEntry.Kind.INFO, "PATH RECEIVED: ${msg.poses.size} poses")
    }

    private fun handlePathStep(msg: Incoming.PathStep) {
        _state.update { s ->
            s.copy(robot = RobotState(
                x = msg.pose.x,
                y = msg.pose.y,
                directionDeg = msg.pose.directionDeg,
                robotX = s.robot?.robotX ?: 3,
                robotY = s.robot?.robotY ?: 3
            ))
        }
    }

    private fun handlePathComplete() {
        _state.update { s ->
            s.copy(pathExecution = s.pathExecution.copy(
                isPlaying = false,
                currentIndex = s.pathExecution.poses.lastIndex
            ))
        }
        appendLog(LogEntry.Kind.INFO, "PATH COMPLETE")
    }

    private fun handlePathAbort() {
        _state.update { s ->
            s.copy(pathExecution = s.pathExecution.copy(isPlaying = false))
        }
        appendLog(LogEntry.Kind.INFO, "PATH ABORTED")
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

    private fun updateLocalObstacle(obstacleId: String, x: Int, y: Int, add: Boolean, face: RobotDirection? = null) {
        _state.update { s ->
            val arena = s.arena ?: ArenaState.empty()
            if (x !in 0 until arena.width || y !in 0 until arena.height) return@update s

            // Extract numeric ID from "B1", "B2", etc.
            val numericId = obstacleId.removePrefix("B").toIntOrNull()

            val cell = arena.getCell(x, y)
            s.copy(arena = arena.withCell(x, y, cell.copy(
                isObstacle = add,
                obstacleId = if (add) numericId else null,
                targetDirection = if (add) (face ?: cell.targetDirection) else null
            )))
        }
    }

    private fun removeLocalObstacle(obstacleId: String) {
        _state.update { s ->
            val arena = s.arena ?: return@update s

            // Find and remove obstacle by ID
            val numericId = obstacleId.removePrefix("B").toIntOrNull()
            val updatedCells = arena.cells.map { cell ->
                if (cell.obstacleId == numericId) {
                    cell.copy(isObstacle = false, obstacleId = null, imageId = null, targetDirection = null)
                } else {
                    cell
                }
            }

            s.copy(arena = arena.copy(cells = updatedCells))
        }
    }

    private fun updateLocalObstacleFace(obstacleId: String, face: RobotDirection) {
        _state.update { s ->
            val arena = s.arena ?: return@update s

            val numericId = obstacleId.removePrefix("B").toIntOrNull()
            val updatedCells = arena.cells.map { cell ->
                if (cell.obstacleId == numericId) {
                    cell.copy(targetDirection = face)
                } else {
                    cell
                }
            }

            s.copy(arena = arena.copy(cells = updatedCells))
        }
    }

    private fun directionToDegrees(dir: RobotDirection): Int = when (dir) {
        RobotDirection.NORTH -> 0
        RobotDirection.EAST -> 90
        RobotDirection.SOUTH -> 180
        RobotDirection.WEST -> 270
    }

    private fun appendLog(kind: LogEntry.Kind, text: String) {
        _state.update { s ->
            val next = (s.log + LogEntry(kind, text))
            val capped = if (next.size > 300) next.takeLast(300) else next
            s.copy(log = capped)
        }
    }

    private fun decodeHexGrid(hex: String, width: Int, height: Int): BooleanArray? {
        val clean = hex.trim().lowercase()
        if (clean.isEmpty()) return null

        val totalBits = width * height
        val out = BooleanArray(totalBits)

        var bitIndex = 0
        for (ch in clean) {
            val nibble = ch.digitToIntOrNull(16) ?: return null
            for (shift in 3 downTo 0) {
                if (bitIndex >= totalBits) return out
                val bit = (nibble shr shift) and 1
                out[bitIndex] = (bit == 1)
                bitIndex++
            }
        }
        return out
    }
}
