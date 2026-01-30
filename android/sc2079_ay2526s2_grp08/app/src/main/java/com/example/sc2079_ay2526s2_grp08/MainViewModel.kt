package com.example.sc2079_ay2526s2_grp08

import androidx.lifecycle.ViewModel
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.domain.*
import com.example.sc2079_ay2526s2_grp08.protocol.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

class MainViewModel(
    private val bt: BluetoothManager
) : ViewModel() {

    private val _state = MutableStateFlow(AppState())
    val state: StateFlow<AppState> = _state

    init {
        bt.onEvent = { ev ->
            when (ev) {
                is BluetoothManager.Event.StateChanged -> {
                    _state.update {
                        it.copy(
                            mode = ev.mode,
                            conn = ev.state,
                            statusText = ev.message ?: it.statusText
                        )
                    }
                }

                is BluetoothManager.Event.LineReceived -> {
                    handleIncomingLine(ev.line)
                }

                else -> {}
            }
        }
    }

    /* ------------------- Public API ------------------- */

    fun sendMoveForward() {
        applyLocalMove(forward = true)
        send(Outgoing.Move("MOVE,F"))
    }

    fun sendMoveBackward() {
        applyLocalMove(forward = false)
        send(Outgoing.Move("MOVE,B"))
    }

    fun sendTurnLeft() {
        applyLocalTurn(left = true)
        send(Outgoing.Move("MOVE,L"))
    }

    fun sendTurnRight() {
        applyLocalTurn(left = false)
        send(Outgoing.Move("MOVE,R"))
    }

    fun sendRaw(line: String) = send(Outgoing.Raw(line))

    /* ------------------- Core Logic ------------------- */

    private fun send(cmd: Outgoing) {
        bt.sendLine(ProtocolEncoder.encode(cmd))
    }

    private fun handleIncomingLine(line: String) {
        when (val msg = ProtocolParser.parse(line)) {

            is Incoming.RobotPosition -> {
                _state.update {
                    it.copy(robot = RobotState(msg.x, msg.y, msg.directionDeg))
                }
            }

            is Incoming.RobotPose -> {
                _state.update {
                    it.copy(robot = RobotState(msg.x, msg.y, dirToDeg(msg.dir)))
                }
            }

            is Incoming.Target -> {
                val face = msg.face?.let { Facing.fromCode(it) }
                _state.update { s ->
                    s.copy(
                        obstacleBlocks = upsertTarget(
                            s.obstacleBlocks,
                            msg.obstacleId,
                            msg.targetId,
                            face
                        )
                    )
                }
            }

            is Incoming.Face -> {
                _state.update { s ->
                    s.copy(
                        obstacleBlocks = upsertFace(
                            s.obstacleBlocks,
                            msg.obstacleId,
                            Facing.fromCode(msg.face)
                        )
                    )
                }
            }

            is Incoming.Msg -> {
                _state.update { it.copy(statusText = msg.text) }
            }

            else -> {}
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

    private fun applyLocalTurn(left: Boolean) {
        val r = ensureRobot()
        val nextDeg = if (left) (r.directionDeg + 270) % 360 else (r.directionDeg + 90) % 360
        _state.update { it.copy(robot = r.copy(directionDeg = nextDeg)) }
    }

    private fun applyLocalMove(forward: Boolean) {
        val r = ensureRobot()

        val step = if (forward) 1 else -1
        val dir = ((r.directionDeg % 360) + 360) % 360

        val (dx, dy) = when (dir) {
            0 -> 0 to step
            90 -> step to 0
            180 -> 0 to -step
            270 -> -step to 0
            else -> 0 to step
        }

        val grid = ArenaConfig.GRID_SIZE
        val nx = (r.x + dx).coerceIn(1, grid - 2)
        val ny = (r.y + dy).coerceIn(1, grid - 2)

        _state.update {
            it.copy(robot = r.copy(x = nx, y = ny))
        }
    }

    /* ------------------- Helpers ------------------- */

    private fun dirToDeg(dir: String): Int =
        when (dir.trim().uppercase()) {
            "N" -> 0
            "E" -> 90
            "S" -> 180
            "W" -> 270
            else -> 0
        }

    private fun upsertTarget(
        list: List<ObstacleState>,
        id: Int,
        targetId: Int,
        face: Facing?
    ): List<ObstacleState> {
        val i = list.indexOfFirst { it.id == id }
        return if (i >= 0) {
            list.toMutableList().apply {
                set(i, list[i].copy(targetId = targetId, facing = face ?: list[i].facing))
            }
        } else {
            list + ObstacleState(id, 0, 0, face, targetId)
        }
    }

    private fun upsertFace(
        list: List<ObstacleState>,
        id: Int,
        face: Facing?
    ): List<ObstacleState> {
        val i = list.indexOfFirst { it.id == id }
        return if (i >= 0) {
            list.toMutableList().apply {
                set(i, list[i].copy(facing = face))
            }
        } else {
            list + ObstacleState(id, 0, 0, face, null)
        }
    }

    fun placeOrMoveObstacle(id: Int, x: Int, y: Int) {
        _state.update { s ->
            val filtered = s.obstacleBlocks
                .filterNot { it.id == id }
                .filterNot { it.x == x && it.y == y } // prevent two obstacles in one cell

            s.copy(obstacleBlocks = filtered + ObstacleState(id = id, x = x, y = y, facing = null, targetId = null))
        }
    }

    fun removeObstacle(id: Int) {
        _state.update { s ->
            s.copy(obstacleBlocks = s.obstacleBlocks.filterNot { it.id == id })
        }
    }

    fun setObstacleFacing(id: Int, facing: Facing?) {
        _state.update { s ->
            val next = s.obstacleBlocks.map { ob ->
                if (ob.id == id) ob.copy(facing = facing) else ob
            }
            s.copy(obstacleBlocks = next)
        }
    }

}
