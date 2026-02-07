package com.example.sc2079_ay2526s2_grp08.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build

class BluetoothManager (private val appCtx: Context) {

    enum class Mode { NONE, SERVER, CLIENT }
    enum class State { DISCONNECTED, LISTENING, CONNECTING, CONNECTED }
    enum class DisconnectReason { LOCAL, REMOTE, ERROR }
    enum class SendRejectReason { NOT_CONNECTED, PERMISSION_DENIED, IO_ERROR, BUSY }

    sealed class Event {
        data class StateChanged(val mode: Mode, val state: State, val message: String? = null) : Event()
        data class Connected(val label: String) : Event()
        data class Disconnected(val reason: DisconnectReason, val message: String? = null) : Event()
        data class DiscoveryStarted(val message: String? = null) : Event()
        data class DeviceFound(val label: String, val device: BluetoothDevice) : Event()
        data class DiscoveryFinished(val foundCount: Int) : Event()
        data class LineReceived(val line: String) : Event()
        data class EchoReceived(val line: String) : Event()
        data class SendRejected(val reason: SendRejectReason, val message: String? = null) : Event()
        data class Log(val message: String) : Event()
    }

    var onEvent: ((Event) -> Unit)? = null

    private val context = appCtx.applicationContext
    private val adapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()
    private val discovered = LinkedHashMap<String, BluetoothDevice>()

    @Volatile private var discoveryActive = false
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

    fun getDiscoveredDevices(): List<BluetoothDevice> = discovered.values.toList()
    fun clearDiscoveredDevices() { discovered.clear() }

    fun buildRequestDiscoverableIntent(durationSec: Int = 300): Intent {
        return Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE).apply {
            putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, durationSec.coerceIn(1, 300))
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
    }


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

    private val discoveryReceiver = object : BroadcastReceiver() {
        @SuppressLint("MissingPermission")
        override fun onReceive(ctx: Context, intent: Intent) {
            when (intent.action) {
                BluetoothAdapter.ACTION_DISCOVERY_STARTED -> {
                    discoveryActive = true
                    onEvent?.invoke(Event.DiscoveryStarted("Scanning for nearby devices..."))
                }
                BluetoothDevice.ACTION_FOUND -> {
                    val device: BluetoothDevice? =
                        if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java)
                        else
                            @Suppress("DEPRECIATION")
                            intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)

                    if (device != null) {
                        val key = device.address
                        if ( !discovered.containsKey(key)) {
                            discovered[key] = device
                            onEvent?.invoke(Event.DeviceFound(device.name ?: device.address, device))
                        }
                    }
                }
                BluetoothAdapter.ACTION_DISCOVERY_FINISHED -> {
                    discoveryActive = false
                    safeUnregisterDiscoveryReceiver()
                    onEvent?.invoke(Event.DiscoveryFinished(discovered.size))
                }
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun startDiscovery() {
        val a = adapter ?: run {
            onEvent?.invoke(Event.Log("Bluetooth not supported"))
            return
        }
        if (!a.isEnabled) {
            onEvent?.invoke(Event.Log("Bluetooth disabled"))
            return
        }

        if (state == State.CONNECTED || state == State.CONNECTING) {
            onEvent?.invoke(Event.SendRejected(SendRejectReason.BUSY, "Cannot scan while $state"))
            return
        }

        discovered.clear()

        if (a.isDiscovering) {
            try { a.cancelDiscovery() } catch (_: Exception) {}
        }

        val filter = IntentFilter().apply {
            addAction(BluetoothAdapter.ACTION_DISCOVERY_STARTED)
            addAction(BluetoothDevice.ACTION_FOUND)
            addAction(BluetoothAdapter.ACTION_DISCOVERY_FINISHED)
        }

        try {
            context.registerReceiver(discoveryReceiver, filter)
        } catch (_: Exception) {}

        discoveryActive = true

        val started = try { a.startDiscovery() } catch (_: Exception) { false }
        if (!started) {
            discoveryActive = false
            safeUnregisterDiscoveryReceiver()
            onEvent?.invoke(Event.Log("startDiscovery() failed"))
        }
    }

    @SuppressLint("MissingPermission")
    fun stopDiscovery() {
        val a = adapter ?: return
        if (a.isDiscovering) {
            try { a.cancelDiscovery() } catch (_: Exception) {}
        }
        discoveryActive = false
        safeUnregisterDiscoveryReceiver()
    }

    private fun safeUnregisterDiscoveryReceiver() {
        try { context.unregisterReceiver(discoveryReceiver) } catch (_: Exception) {}
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
        onEvent?.invoke(Event.Disconnected(reason, msg))
        if (mode == Mode.CLIENT) mode = Mode.NONE
        setState(State.DISCONNECTED, msg)
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
