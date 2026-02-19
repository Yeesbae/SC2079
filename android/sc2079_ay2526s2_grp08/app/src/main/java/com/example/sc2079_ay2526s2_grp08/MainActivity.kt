package com.example.sc2079_ay2526s2_grp08

import android.Manifest
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
    private val logLock = Any()
    private lateinit var tvStatus: TextView
    private lateinit var tvLog: TextView
    private lateinit var spDevices: Spinner
    private lateinit var btnScan: Button
    private lateinit var btnConnect: Button
    private lateinit var btnDisconnect: Button
    private lateinit var btnSendTest: Button

    private val bt = BluetoothManager()
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

        btnScan.setOnClickListener { ensureBtPermissionsThen { getBtDevices() } }
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
                val labels = pairedDevices.map { d ->
                    val name = d.name ?: "Unknown"
                    "$name (${d.address})"
                }

                spDevices.adapter = ArrayAdapter(
                    this,
                    android.R.layout.simple_spinner_dropdown_item,
                    labels.ifEmpty { listOf("No paired devices") }
                )
                appendLog("Paired devices: ${pairedDevices.size}")
            } catch (se: SecurityException){
                toast("Bluetooth permission required")
            }

        }
    }

    private fun getSelectedDeviceOrNull(): BluetoothDevice? {
        if (pairedDevices.isEmpty()) return null
        val pos = spDevices.selectedItemPosition
        if (pos < 0 || pos >= pairedDevices.size) return null
        return pairedDevices[pos]
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