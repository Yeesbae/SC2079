package com.example.sc2079_ay2526s2_grp08

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager

/**
 * TEMP DEBUG ONLY.
 * Vithun will replace UI; do not build features here.
 */

class MainActivity : AppCompatActivity() {
    private enum class DeviceListMode { PAIRED, DISCOVERED }

    private val logLock = Any()
    private var listMode: DeviceListMode = DeviceListMode.PAIRED
    private var discoveredDevices: List<BluetoothDevice> = emptyList()
    private lateinit var tvStatus: TextView
    private lateinit var tvLog: TextView
    private lateinit var spDevices: Spinner
    private lateinit var btnScan: Button
    private lateinit var btnConnect: Button
    private lateinit var btnDisconnect: Button
    private lateinit var btnSendTest: Button

    private val bt by lazy { BluetoothManager(applicationContext) }
    private var pairedDevices: List<BluetoothDevice> = emptyList()

    private val requestBtPerms =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            val connectGranted = result[Manifest.permission.BLUETOOTH_CONNECT] == true
            val scanGranted = result[Manifest.permission.BLUETOOTH_SCAN] == true

            appendLog("BT_CONNECT=$connectGranted, BT_SCAN=$scanGranted")

            if (connectGranted) {
                getBtDevices()
                bt.startServer()
            } else toast("Bluetooth permission required")
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        tvLog = findViewById(R.id.tvLog)
        spDevices = findViewById(R.id.spDevices)
        btnScan = findViewById(R.id.btnScan)
        btnConnect = findViewById(R.id.btnConnect)
        btnDisconnect = findViewById(R.id.btnDisconnect)
        btnSendTest = findViewById(R.id.btnSendTest)

        bt.onEvent = { ev ->
            runOnUiThread {
                when (ev) {
                    is BluetoothManager.Event.StateChanged -> {
                        tvStatus.text = "Status: ${ev.state} (${ev.mode})"
                        ev.message?.let { appendLog("STATE: $it") }
                    }
                    is BluetoothManager.Event.Connected -> {
                        appendLog("CONNECTED: ${ev.label}")
                    }
                    is BluetoothManager.Event.Disconnected -> {
                        appendLog("DISCONNECTED: ${ev.reason} ${ev.message ?: ""}".trim())
                    }
                    is BluetoothManager.Event.DiscoveryStarted -> {
                        btnScan.text = "Stop"
                        appendLog("DISCOVERY_STARTED: ${ev.message ?: ""}".trim())
                        discoveredDevices = emptyList()
                        showDevicesInSpinner(discoveredDevices, DeviceListMode.DISCOVERED)
                    }
                    is BluetoothManager.Event.DeviceFound -> {
                        discoveredDevices = bt.getDiscoveredDevices()
                        showDevicesInSpinner(discoveredDevices, DeviceListMode.DISCOVERED)
                        appendLog("FOUND: ${ev.label}")
                    }
                    is BluetoothManager.Event.DiscoveryFinished -> {
                        btnScan.text = "Scan"
                        appendLog("DISCOVERY_FINISHED: found=${ev.foundCount}")
                        discoveredDevices = bt.getDiscoveredDevices()
                        showDevicesInSpinner(discoveredDevices, DeviceListMode.DISCOVERED)
                    }
                    is BluetoothManager.Event.LineReceived -> appendLog("IN: ${ev.line}")
                    is BluetoothManager.Event.EchoReceived -> appendLog("ECHO: ${ev.line}")
                    is BluetoothManager.Event.SendRejected -> {
                        appendLog("SEND_REJECTED: ${ev.reason} ${ev.message ?: ""}".trim())
                        if (ev.reason == BluetoothManager.SendRejectReason.NOT_CONNECTED) toast("Not connected")
                    }
                    is BluetoothManager.Event.Log -> appendLog(ev.message)
                }
            }
        }

        btnScan.setOnClickListener {
            ensureBtPermissionsThen {
                val isScanningNow = try { BluetoothAdapter.getDefaultAdapter()?.isDiscovering == true } catch (_: Exception) { false }

                if (!isScanningNow) {
                    discoveredDevices = emptyList()
                    showDevicesInSpinner(discoveredDevices, DeviceListMode.DISCOVERED)
                    bt.startDiscovery()
                } else {
                    bt.stopDiscovery()
                }
            }
        }

        btnConnect.setOnClickListener {
            ensureBtPermissionsThen {
                val d = getSelectedDeviceOrNull()
                if (d == null) {
                    toast("No device selected")
                    return@ensureBtPermissionsThen
                }
                bt.connect(d)
            }
        }
        btnDisconnect.setOnClickListener {
            bt.disconnectClient()
            bt.stopServer()
            ensureBtPermissionsThen { bt.startServer() }
        }
        btnSendTest.setOnClickListener {
            bt.sendLine("MOVE,F")
            appendLog("OUT: MOVE,F (attempt)")
        }

        ensureBtPermissionsThen {
            getBtDevices()
            bt.startServer()
        }
    }

    private fun getBtDevices() {
        if (!bt.isSupported()) {
            toast("Bluetooth not supported on this device")
            return
        }
        if (!bt.isEnabled()) {
            toast("Please enable Bluetooth in settings")
            return
        }

        ensureBtPermissionsThen {
            try{
                pairedDevices = bt.getPairedDevices()
                if (listMode == DeviceListMode.PAIRED) {
                    showDevicesInSpinner(pairedDevices, DeviceListMode.PAIRED)
                }

                appendLog("Paired devices: ${pairedDevices.size}")
            } catch (se: SecurityException){
                toast("Bluetooth permission required")
            }

        }
    }

    private fun showDevicesInSpinner(devices: List<BluetoothDevice>, mode: DeviceListMode) {
        listMode = mode

        val labels = devices.map { d ->
            val name = try { d.name } catch (_: SecurityException) { null } ?: "Unknown"
            val addr = try { d.address } catch (_: SecurityException) { "??:??:??:??:??:??" }
            "$name ($addr)"
        }

        spDevices.adapter = ArrayAdapter(
            this,
            android.R.layout.simple_spinner_dropdown_item,
            labels.ifEmpty {
                if (mode == DeviceListMode.PAIRED) listOf("No paired devices")
                else listOf("No devices found (yet)")
            }
        )
    }


    private fun getSelectedDeviceOrNull(): BluetoothDevice? {
        val list = when (listMode) {
            DeviceListMode.PAIRED -> pairedDevices
            DeviceListMode.DISCOVERED -> discoveredDevices
        }
        if (list.isEmpty()) return null
        val pos = spDevices.selectedItemPosition
        if (pos < 0 || pos >= list.size) return null
        return list[pos]
    }

    private fun ensureBtPermissionsThen(block: () -> Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val connectGranted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.BLUETOOTH_CONNECT
            ) == PackageManager.PERMISSION_GRANTED

            val scanGranted = ContextCompat.checkSelfPermission(
                this, Manifest.permission.BLUETOOTH_SCAN
            ) == PackageManager.PERMISSION_GRANTED

            appendLog("BT_CONNECT granted=$connectGranted, BT_SCAN granted=$scanGranted (SDK=${Build.VERSION.SDK_INT})")

            if (!connectGranted || !scanGranted) {
                requestBtPerms.launch(arrayOf(
                    Manifest.permission.BLUETOOTH_CONNECT,
                    Manifest.permission.BLUETOOTH_SCAN
                ))
                return
            }
        }
        block()
    }


    private fun appendLog(msg: String) {
        synchronized(logLock) {
            tvLog.append("$msg\n")
        }
    }

    private fun toast(msg: String) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }
}