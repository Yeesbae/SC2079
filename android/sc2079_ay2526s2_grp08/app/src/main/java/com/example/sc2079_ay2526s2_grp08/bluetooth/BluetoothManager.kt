package com.example.sc2079_ay2526s2_grp08.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket

class BluetoothManager {

    enum class Mode { NONE, SERVER, CLIENT }
    enum class State { DISCONNECTED, LISTENING, CONNECTING, CONNECTED }
    enum class DisconnectReason { LOCAL, REMOTE, ERROR }
    enum class SendRejectReason { NOT_CONNECTED, PERMISSION_DENIED, IO_ERROR, BUSY }

    sealed class Event {
        data class StateChanged(val mode: Mode, val state: State, val message: String? = null) : Event()
        data class Connected(val label: String) : Event()
        data class Disconnected(val reason: DisconnectReason, val message: String? = null) : Event()
        data class LineReceived(val line: String) : Event()
        data class EchoReceived(val line: String) : Event()
        data class SendRejected(val reason: SendRejectReason, val message: String? = null) : Event()
        data class Log(val message: String) : Event()
    }

    var onEvent: ((Event) -> Unit)? = null

    private val adapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()

    @Volatile var mode: Mode = Mode.NONE
        private set
    @Volatile var state: State = State.DISCONNECTED
        private set

    @Volatile private var serverRunning: Boolean = false
    @Volatile private var intentionalDisconnect: Boolean = false

    private var serverSocket: BluetoothServerSocket? = null
    private var serverThread: Thread? = null

    private val comm = BluetoothCommunicationService().apply {
        onLine = { line, isEcho ->
            if (isEcho) onEvent?.invoke(Event.EchoReceived(line))
            else onEvent?.invoke(Event.LineReceived(line))
        }
        onSendError = { msg ->
            onEvent?.invoke(Event.SendRejected(SendRejectReason.IO_ERROR, msg))
        }
        onSessionEnded = { reason, msg ->
            handleSessionEnded(reason, msg)
        }
    }

    fun isSupported(): Boolean = adapter != null
    fun isEnabled(): Boolean = adapter?.isEnabled == true

    @SuppressLint("MissingPermission")
    fun getPairedDevices(): List<BluetoothDevice> {
        val a = adapter ?: return emptyList()
        return try {
            a.bondedDevices?.toList() ?: emptyList()
        } catch (se: SecurityException) {
            onEvent?.invoke(Event.SendRejected(SendRejectReason.PERMISSION_DENIED, "Missing Bluetooth permission"))
            emptyList()
        }
    }

    // -------- Server mode (AMD Tool/RPI connects to AA) --------

    @SuppressLint("MissingPermission")
    fun startServer(serviceName: String = BluetoothConfig.SERVICE_NAME) {
        val a = adapter ?: run {
            emitState(Mode.NONE, State.DISCONNECTED, "Bluetooth not supported")
            onEvent?.invoke(Event.Disconnected(DisconnectReason.ERROR, "Bluetooth not supported"))
            return
        }

        if (mode == Mode.SERVER && (state == State.LISTENING || state == State.CONNECTED)) return

        if (state != State.DISCONNECTED) {
            onEvent?.invoke(Event.SendRejected(SendRejectReason.BUSY, "Already $state ($mode)"))
            return
        }

        mode = Mode.SERVER
        intentionalDisconnect = false
        serverRunning = true

        // ensure any old client session is gone
        comm.closeSession(DisconnectReason.LOCAL, null)
        comm.resetParsers()

        setState(State.LISTENING, "Waiting for incoming connection...")

        serverThread = Thread {
            while (serverRunning && mode == Mode.SERVER) {
                val ss = try {
                    a.listenUsingInsecureRfcommWithServiceRecord(serviceName, BluetoothConfig.SPP_UUID)
                } catch (e: Exception) {
                    onEvent?.invoke(Event.Disconnected(DisconnectReason.ERROR, "Server listen failed: ${e.message ?: e.javaClass.simpleName}"))
                    setState(State.DISCONNECTED, "Listen failed")
                    break
                }

                serverSocket = ss
                try {
                    val s = ss.accept()
                    safeClose(ss)
                    serverSocket = null

                    if (!serverRunning || mode != Mode.SERVER) {
                        safeClose(s)
                        break
                    }

                    setState(State.CONNECTED, "Incoming connection accepted")
                    onEvent?.invoke(Event.Connected("Incoming connection (AMD Tool)"))
                    comm.startSession(s)

                    // Wait for session to end; handleSessionEnded() decides next step.
                    // If session ended REMOTE and serverRunning is true, loop continues and listens again.
                    // If stopServer() called, serverRunning false breaks the loop.

                    while (serverRunning && mode == Mode.SERVER && comm.isActive()) {
                        try { Thread.sleep(50) } catch (_: Exception) {}
                    }

                    if (serverRunning && mode == Mode.SERVER) {
                        setState(State.LISTENING, "Waiting for incoming connection...")
                        try { Thread.sleep(50) } catch (_: Exception) {}
                    }
                } catch (e: Exception) {
                    safeClose(ss)
                    serverSocket = null
                    if (!serverRunning || intentionalDisconnect) break
                    try { Thread.sleep(BluetoothConfig.SERVER_RETRY_BACKOFF_MS) } catch (_: Exception) {}
                }
            }

            // final cleanup
            safeClose(serverSocket)
            serverSocket = null
            if (mode == Mode.SERVER) {
                mode = Mode.NONE
                setState(State.DISCONNECTED, "Server stopped")
            }
        }.also { it.start() }
    }

    fun stopServer() {
        intentionalDisconnect = true
        serverRunning = false

        safeClose(serverSocket)
        serverSocket = null

        val st = serverThread
        serverThread = null
        try { st?.interrupt() } catch (_: Exception) {}
        try { if (st != null && st != Thread.currentThread()) st.join(300) } catch (_: Exception) {}

        if (mode == Mode.SERVER) mode = Mode.NONE

        val hadSession = comm.isActive()
        comm.closeSession(DisconnectReason.LOCAL, "Server stopped")

        if (!hadSession) {
            setState(State.DISCONNECTED, "Server stopped")
            onEvent?.invoke(Event.Disconnected(DisconnectReason.LOCAL, "Server stopped"))
        }
    }

    // -------- Client mode (AA connects to selected device) --------

    @SuppressLint("MissingPermission")
    fun connect(device: BluetoothDevice) {
        val a = adapter ?: run {
            onEvent?.invoke(Event.Disconnected(DisconnectReason.ERROR, "Bluetooth not supported"))
            return
        }

        if (mode == Mode.SERVER){
            stopServer()
        }

        if (state != State.DISCONNECTED) {
            onEvent?.invoke(Event.SendRejected(SendRejectReason.BUSY, "Already $state ($mode)"))
            return
        }

        serverRunning = false
        safeClose(serverSocket)
        serverSocket = null

        mode = Mode.CLIENT
        intentionalDisconnect = false
        setState(State.CONNECTING, "Connecting to ${device.name ?: device.address}...")

        Thread {
            try {
                try { a.cancelDiscovery() } catch (_: Exception) {}
                val s = device.createInsecureRfcommSocketToServiceRecord(BluetoothConfig.SPP_UUID)
                s.connect()

                setState(State.CONNECTED, "Connected")
                onEvent?.invoke(Event.Connected("Connected to ${device.name ?: device.address}"))
                comm.startSession(s)
            } catch (se: SecurityException) {
                setState(State.DISCONNECTED, "Permission denied")
                onEvent?.invoke(Event.Disconnected(DisconnectReason.ERROR, "Permission denied"))
            } catch (e: Exception) {
                setState(State.DISCONNECTED, "Connect failed")
                onEvent?.invoke(Event.Disconnected(DisconnectReason.ERROR, "Connect failed: ${e.message ?: e.javaClass.simpleName}"))
            }
        }.start()
    }

    fun disconnectClient() {
        intentionalDisconnect = true

        val hadSession = comm.isActive()
        comm.closeSession(DisconnectReason.LOCAL, "Disconnected")

        if (mode == Mode.CLIENT) mode = Mode.NONE

        if (!hadSession){
            setState(State.DISCONNECTED, "Disconnected")
            onEvent?.invoke(Event.Disconnected(DisconnectReason.LOCAL, "Disconnected"))
        }
    }

    fun sendLine(line: String) {
        val ok = comm.sendLine(line)
        if (!ok) {
            onEvent?.invoke(Event.SendRejected(SendRejectReason.NOT_CONNECTED, "Not connected"))
        }
    }

    private fun handleSessionEnded(reason: DisconnectReason, msg: String?) {
        if (mode == Mode.SERVER && serverRunning && reason == DisconnectReason.REMOTE && !intentionalDisconnect) {
            onEvent?.invoke(Event.Disconnected(reason, msg))
            return
        }

        onEvent?.invoke(Event.Disconnected(reason, msg))
        if (mode == Mode.CLIENT) mode = Mode.NONE
        setState(State.DISCONNECTED, msg)

        if (!intentionalDisconnect) {
            Thread {
                try { Thread.sleep(150) } catch (_: Exception) {}
                startServer()
            }.start()
        }
    }

    private fun setState(newState: State, msg: String? = null) {
        state = newState
        emitState(mode, state, msg)
    }

    private fun emitState(m: Mode, s: State, msg: String?) {
        onEvent?.invoke(Event.StateChanged(m, s, msg))
    }

    private fun safeClose(ss: BluetoothServerSocket?) {
        try { ss?.close() } catch (_: Exception) {}
    }

    private fun safeClose(s: BluetoothSocket?) {
        try { s?.close() } catch (_: Exception) {}
    }
}
