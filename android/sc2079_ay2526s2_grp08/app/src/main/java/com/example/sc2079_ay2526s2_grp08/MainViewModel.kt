package com.example.sc2079_ay2526s2_grp08

import androidx.lifecycle.ViewModel
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.domain.AppState
import com.example.sc2079_ay2526s2_grp08.domain.ArenaState
import com.example.sc2079_ay2526s2_grp08.domain.LogEntry
import com.example.sc2079_ay2526s2_grp08.domain.RobotState
import com.example.sc2079_ay2526s2_grp08.protocol.Incoming
import com.example.sc2079_ay2526s2_grp08.protocol.Outgoing
import com.example.sc2079_ay2526s2_grp08.protocol.ProtocolEncoder
import com.example.sc2079_ay2526s2_grp08.protocol.ProtocolParser
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

/**
 * UI layer should call this; UI must NOT touch BluetoothManager directly.
 */
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
    }

    // Methods to call

    fun startDefaultListening() {
        bt.startServer()
    }

    fun disconnectAndReturnToListening() {
        bt.stopServer()
        bt.disconnectClient()
        bt.startServer()
    }

    fun connectToDevice(device: android.bluetooth.BluetoothDevice) {
        bt.connect(device)
    }

    fun sendMoveForward() = send(Outgoing.Move("MOVE,F"))
    fun sendMoveBackward() = send(Outgoing.Move("MOVE,B"))
    fun sendTurnLeft() = send(Outgoing.Move("MOVE,L"))
    fun sendTurnRight() = send(Outgoing.Move("MOVE,R"))

    fun sendRaw(line: String) = send(Outgoing.Raw(line))

    // -----------------------------------------------------

    private fun send(cmd: Outgoing) {
        val line = ProtocolEncoder.encode(cmd)
        bt.sendLine(line)
        appendLog(LogEntry.Kind.OUT, line)
    }

    private fun handleIncomingLine(line: String) {
        when (val msg = ProtocolParser.parse(line)) {

            is Incoming.RobotPosition -> {
                _state.update {
                    it.copy(robot = RobotState(msg.x, msg.y, msg.directionDeg))
                }
            }

            is Incoming.GridHex -> {
                // Default arena size (slides mention 20x15 commonly; script notes 20*15=300)
                val width = _state.value.arena?.width ?: 20
                val height = _state.value.arena?.height ?: 15
                val cells = decodeHexGrid(msg.hex, width, height)
                if (cells != null) {
                    _state.update { it.copy(arena = ArenaState(width, height, cells)) }
                } else {
                    appendLog(LogEntry.Kind.ERROR, "Failed to decode grid hex length=${msg.hex.length}")
                }
            }

            is Incoming.GridBinary -> {
                _state.update { it.copy(arena = ArenaState(msg.width, msg.height, msg.cells)) }
            }

            is Incoming.AddObstacle -> {
                // If we have an arena, flip that cell to obstacle=true
                val a = _state.value.arena ?: return
                val idx = msg.y * a.width + msg.x
                if (idx in a.obstacles.indices) {
                    val copy = a.obstacles.copyOf()
                    copy[idx] = true
                    _state.update { it.copy(arena = a.copy(obstacles = copy)) }
                }
            }

            is Incoming.RemoveObstacle -> {
                val a = _state.value.arena ?: return
                val idx = msg.y * a.width + msg.x
                if (idx in a.obstacles.indices) {
                    val copy = a.obstacles.copyOf()
                    copy[idx] = false
                    _state.update { it.copy(arena = a.copy(obstacles = copy)) }
                }
            }

            is Incoming.Msg -> {
                _state.update { it.copy(statusText = msg.text) }
            }

            is Incoming.Raw -> {
            }
        }
    }

    private fun appendLog(kind: LogEntry.Kind, text: String) {
        _state.update { s ->
            val next = (s.log + LogEntry(kind, text))
            val capped = if (next.size > 300) next.takeLast(300) else next
            s.copy(log = capped)
        }
    }

    /**
     * Decode AMD Tool JSON grid hex string into a BooleanArray.
     *
     * Spec: bitstring is row-major (top-left -> right, then next row), 0=no obstacle, 1=obstacle.
     * Hex encodes 4 bits per character; padded with zeros at end if needed.
     */
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
