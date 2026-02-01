package com.example.sc2079_ay2526s2_grp08

import android.content.Context
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

    private fun android.bluetooth.BluetoothDevice.toBtDevice(bonded: Boolean? = null): BtDevice {
        val safeName = try { name } catch (_: SecurityException) { null }
        val safeAddr = try { address } catch (_: SecurityException) { "unknown" }
        val isBonded = bonded ?: (bondState == android.bluetooth.BluetoothDevice.BOND_BONDED)
        return BtDevice(name = safeName, address = safeAddr, bonded = isBonded)
    }

    fun refreshPairedDevices() {
        val paired = bt.getPairedDevices().map { it.toBtDevice(bonded = true) }
        _state.update { it.copy(pairedDevices = paired) }
    }

    /** Get list of paired Bluetooth devices */
    fun getPairedDevices(): List<android.bluetooth.BluetoothDevice> {
        return bt.getPairedDevices()
    }

    fun startScan() {
        refreshPairedDevices()
        _state.update { it.copy(scannedDevices = emptyList(), isScanning = true) }
        bt.clearDiscoveredDevices()
        bt.startDiscovery()
    }

    fun stopScan() {
        bt.stopDiscovery()
        _state.update { it.copy(isScanning = false) }
    }

    fun clearScanResults() {
        bt.clearDiscoveredDevices()
        _state.update { it.copy(scannedDevices = emptyList()) }
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
        applyLocalMove(forward = true)
        send(Outgoing.MoveForward)
    }

    fun sendMoveBackward() {
        applyLocalMove(forward = false)
        send(Outgoing.MoveBackward)
    }

    fun sendTurnLeft() {
        applyLocalTurn(left = true)
        send(Outgoing.TurnLeft)
    }

    fun sendTurnRight() {
        applyLocalTurn(left = false)
        send(Outgoing.TurnRight)
    }

    fun sendMoveForward(steps: Int) {
        repeat(steps) { applyLocalMove(forward = true) }
        send(Outgoing.MoveForwardSteps(steps))
    }

    fun sendMoveBackward(steps: Int) {
        repeat(steps) { applyLocalMove(forward = false) }
        send(Outgoing.MoveBackwardSteps(steps))
    }

    fun sendTurnDegrees(degrees: Int) {
        // Apply local turn based on degrees
        val turns = (degrees / 90) % 4
        repeat(turns) { applyLocalTurn(left = degrees < 0) }
        send(Outgoing.TurnDegrees(degrees))
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Local Movement Preview (updates UI immediately before Bluetooth response)
    // ─────────────────────────────────────────────────────────────────────────

    private fun applyLocalMove(forward: Boolean) {
        val robot = ensureRobot()
        val step = if (forward) 1 else -1
        val dir = ((robot.directionDeg % 360) + 360) % 360

        val (dx, dy) = when (dir) {
            0 -> 0 to step      // North: y increases
            90 -> step to 0     // East: x increases
            180 -> 0 to -step   // South: y decreases
            270 -> -step to 0   // West: x decreases
            else -> 0 to step
        }

        val gridSize = _state.value.arena?.width ?: ArenaConfig.GRID_SIZE
        val nx = (robot.x + dx).coerceIn(1, gridSize - 2)
        val ny = (robot.y + dy).coerceIn(1, gridSize - 2)

        _state.update {
            it.copy(robot = robot.copy(x = nx, y = ny))
        }
    }

    private fun applyLocalTurn(left: Boolean) {
        val robot = ensureRobot()
        val nextDeg = if (left) {
            (robot.directionDeg + 270) % 360  // -90 degrees
        } else {
            (robot.directionDeg + 90) % 360   // +90 degrees
        }
        _state.update {
            it.copy(robot = robot.copy(directionDeg = nextDeg))
        }
    }

    private fun ensureRobot(): RobotState {
        return _state.value.robot ?: RobotState(
            x = 1,
            y = 1,
            directionDeg = 0
        ).also { r ->
            _state.update { it.copy(robot = r) }
        }
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

        // Update local state
        _state.update { s ->
            // Remove any existing obstacle at this position, and update/add this obstacle
            val filtered = s.obstacleBlocks
                .filterNot { it.id == id }  // Remove old position of this obstacle
                .filterNot { it.x == x && it.y == y }  // Remove any obstacle at target position

            val existingObs = s.obstacleBlocks.find { it.id == id }
            val newObs = ObstacleState(
                id = id,
                x = x,
                y = y,
                facing = existingObs?.facing,
                targetId = existingObs?.targetId
            )

            s.copy(obstacleBlocks = filtered + newObs)
        }

        // Send via Bluetooth
        send(Outgoing.AddObstacle(obstacleId, x, y))

        // Sync to arena cells
        syncObstaclesToArena()
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
        _state.update { s ->
            s.copy(obstacleBlocks = s.obstacleBlocks.filterNot { it.id == id })
        }
        send(Outgoing.RemoveObstacle("B$id"))
        syncObstaclesToArena()
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
        _state.update { s ->
            val updated = s.obstacleBlocks.map { obs ->
                if (obs.id == id) obs.copy(facing = facing) else obs
            }
            s.copy(obstacleBlocks = updated)
        }

        if (facing != null) {
            send(Outgoing.SetObstacleFace("B$id", facing))
        }
        syncObstaclesToArena()
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
            is BluetoothManager.Event.DiscoveryStarted -> {
                _state.update { it.copy(isScanning = true) }
                ev.message?.let { appendLog(LogEntry.Kind.INFO, it) }
            }
            is BluetoothManager.Event.DeviceFound -> {
                val d = ev.device.toBtDevice()
                _state.update { s ->
                    val next = (s.scannedDevices + d).distinctBy { it.address }
                    s.copy(scannedDevices = next)
                }
            }

            is BluetoothManager.Event.DiscoveryFinished -> {
                _state.update { it.copy(isScanning = false) }
                appendLog(LogEntry.Kind.INFO, "Scan finished. found=${ev.foundCount}")
            }
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
        val numericId = msg.obstacleId.removePrefix("B").toIntOrNull()

        _state.update { s ->
            // Update obstacleBlocks
            val updatedBlocks = s.obstacleBlocks.map { obs ->
                if (obs.id == numericId || obs.obstacleId == msg.obstacleId) {
                    obs.copy(
                        targetId = msg.targetId,
                        facing = msg.face ?: obs.facing
                    )
                } else {
                    obs
                }
            }

            // Add to detections list
            val detection = ImageDetection(
                imageId = msg.targetId,
                label = "Obstacle ${msg.obstacleId}"
            )
            val detections = (s.detections + detection).takeLast(100)

            s.copy(
                obstacleBlocks = updatedBlocks,
                detections = detections,
                lastDetection = detection
            )
        }

        // Sync to arena cells
        syncObstaclesToArena()

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
        val id = msg.obstacleId.removePrefix("B").toIntOrNull() ?: return

        _state.update { s ->
            val filtered = s.obstacleBlocks
                .filterNot { it.id == id }
                .filterNot { it.x == msg.x && it.y == msg.y }

            val existingObs = s.obstacleBlocks.find { it.id == id }
            val newObs = ObstacleState(
                id = id,
                x = msg.x,
                y = msg.y,
                facing = msg.targetFace ?: existingObs?.facing,
                targetId = existingObs?.targetId
            )

            s.copy(obstacleBlocks = filtered + newObs)
        }
        syncObstaclesToArena()
    }

    private fun handleObstacleRemoved(msg: Incoming.ObstacleRemoved) {
        val id = msg.obstacleId.removePrefix("B").toIntOrNull() ?: return

        _state.update { s ->
            s.copy(obstacleBlocks = s.obstacleBlocks.filterNot { it.id == id })
        }
        syncObstaclesToArena()
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

    private fun directionToDegrees(dir: RobotDirection): Int = when (dir) {
        RobotDirection.NORTH -> 0
        RobotDirection.EAST -> 90
        RobotDirection.SOUTH -> 180
        RobotDirection.WEST -> 270
    }

    /**
     * Sync obstacleBlocks list to arena cells.
     * Call this after modifying obstacleBlocks to keep arena in sync.
     */
    private fun syncObstaclesToArena() {
        _state.update { s ->
            val arena = s.arena ?: ArenaState.empty()

            // Clear all obstacles from arena first
            var updatedArena = ArenaState(
                arena.width,
                arena.height,
                arena.cells.map { it.copy(isObstacle = false, obstacleId = null, imageId = null, targetDirection = null) }
            )

            // Add obstacles from obstacleBlocks
            for (obs in s.obstacleBlocks) {
                if (obs.x in 0 until arena.width && obs.y in 0 until arena.height) {
                    val cell = updatedArena.getCell(obs.x, obs.y)
                    updatedArena = updatedArena.withCell(obs.x, obs.y, cell.copy(
                        isObstacle = true,
                        obstacleId = obs.id,
                        imageId = obs.targetId,
                        targetDirection = obs.facing
                    ))
                }
            }

            s.copy(arena = updatedArena)
        }
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
