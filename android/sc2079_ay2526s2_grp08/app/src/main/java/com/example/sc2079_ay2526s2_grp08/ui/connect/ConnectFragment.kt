package com.example.sc2079_ay2526s2_grp08.ui.connect

import android.Manifest
import android.bluetooth.BluetoothDevice
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.example.sc2079_ay2526s2_grp08.MainActivity
import com.example.sc2079_ay2526s2_grp08.R
import com.example.sc2079_ay2526s2_grp08.domain.BtDevice
import kotlinx.coroutines.launch

class ConnectFragment : Fragment(R.layout.fragment_connect) {

    private val vm by lazy { (requireActivity() as MainActivity).viewModel }

    private lateinit var tvStatus: TextView
    private lateinit var btnRefresh: Button
    private lateinit var btnScan: Button
    private lateinit var spDevices: Spinner
    private lateinit var btnConnect: Button
    private lateinit var btnDisconnect: Button
    private lateinit var btnSendTest: Button
    private lateinit var tvLog: TextView

    // NEW: what the spinner is currently showing (paired OR scanned)
    private var shown: List<BtDevice> = emptyList()

    // We need to know if we are requesting scan perms or just connect perms
    private var pendingAction: (() -> Unit)? = null

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { _ ->
            // After permission dialog, run whatever action user intended
            val action = pendingAction
            pendingAction = null
            action?.invoke()
        }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        tvStatus = view.findViewById(R.id.tvStatus)
        btnRefresh = view.findViewById(R.id.btnRefreshPaired)
        btnScan = view.findViewById(R.id.btnScan) // ✅ requires you to add this button in XML
        spDevices = view.findViewById(R.id.spDevices)
        btnConnect = view.findViewById(R.id.btnConnect)
        btnDisconnect = view.findViewById(R.id.btnDisconnect)
        btnSendTest = view.findViewById(R.id.btnSendTest)
        tvLog = view.findViewById(R.id.tvLog)

        btnRefresh.setOnClickListener {
            ensureBtPermissionsThen(scan = false) { refreshPairedDevices() }
        }

        btnScan.setOnClickListener {
            ensureBtPermissionsThen(scan = true) {
                vm.startScan()
                // Keep paired list fresh too (good UX)
                refreshPairedDevices()
            }
        }

        btnConnect.setOnClickListener {
            ensureBtPermissionsThen(scan = false) {
                val idx = spDevices.selectedItemPosition
                val picked = shown.getOrNull(idx)
                if (picked == null) {
                    toast("No device selected")
                    return@ensureBtPermissionsThen
                }

                vm.connectToDevice(picked)

            }
        }

        btnDisconnect.setOnClickListener {
            vm.disconnectAndReturnToListening()
        }

        btnSendTest.setOnClickListener {
            vm.sendRaw("MOVE,F")
        }

        // Observe state (Status + Log + update spinner list)
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                vm.state.collect { s ->
                    val statusLine = buildString {
                        append("Status: ")
                        append(s.conn.name)
                        s.statusText?.let {
                            append(" — ")
                            append(it)
                        }
                        if (s.isScanning) {
                            append(" — Scanning...")
                        }
                    }
                    tvStatus.text = statusLine

                    // ✅ Choose what to show in spinner:
                    // Prefer scanned devices if any, otherwise paired devices from AppState
                    shown = if (s.scannedDevices.isNotEmpty()) s.scannedDevices else s.pairedDevices

                    val labels = if (shown.isEmpty()) {
                        listOf("(no devices)")
                    } else {
                        shown.map { it.label }
                    }

                    val adapter = ArrayAdapter(
                        requireContext(),
                        android.R.layout.simple_spinner_dropdown_item,
                        labels
                    )
                    spDevices.adapter = adapter

                    // Show last ~200 log lines to avoid UI lag
                    val logs = s.log.takeLast(200).joinToString("\n") { e ->
                        "[${e.kind}] ${e.text}"
                    }
                    tvLog.text = "Log:\n$logs"
                }
            }
        }

        // Initial load
        ensureBtPermissionsThen(scan = false) {
            refreshPairedDevices()
            vm.startDefaultListening()
        }
    }

    private fun refreshPairedDevices() {
        if (!vm.isBluetoothSupported()) { toast("Bluetooth not supported"); return }
        if (!vm.isBluetoothEnabled()) { toast("Bluetooth is OFF — turn it on first") }
        vm.refreshPairedDevices()
    }

    /**
     * scan=false: only BLUETOOTH_CONNECT on Android 12+ (paired list + connect)
     * scan=true : include scan permission (Android 12+) OR location (Android <12)
     */
    private fun ensureBtPermissionsThen(scan: Boolean, onGranted: () -> Unit) {
        val needed = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            // Android 12+
            needed += Manifest.permission.BLUETOOTH_CONNECT
            if (scan) needed += Manifest.permission.BLUETOOTH_SCAN
        } else {
            // Android 9/10/11 discovery often requires Location permission
            if (scan) needed += Manifest.permission.ACCESS_FINE_LOCATION
        }

        val notGranted = needed.filter {
            ContextCompat.checkSelfPermission(requireContext(), it) != PackageManager.PERMISSION_GRANTED
        }

        if (notGranted.isNotEmpty()) {
            pendingAction = onGranted
            permissionLauncher.launch(notGranted.toTypedArray())
            return
        }

        onGranted()
    }

    private fun toast(msg: String) {
        Toast.makeText(requireContext(), msg, Toast.LENGTH_SHORT).show()
    }
}
