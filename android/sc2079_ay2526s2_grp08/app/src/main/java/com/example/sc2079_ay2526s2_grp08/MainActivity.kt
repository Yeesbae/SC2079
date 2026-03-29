package com.example.sc2079_ay2526s2_grp08

import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.viewmodel.MainViewModel
import com.google.android.material.bottomnavigation.BottomNavigationView

class MainActivity : AppCompatActivity() {

    private val bt by lazy { BluetoothManager(applicationContext) }
    private val vmFactory by lazy { MainViewModelFactory(bt) }
    val viewModel: MainViewModel by viewModels { vmFactory }

    private val btConnectPermLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                viewModel.startDefaultListening()
            } else {
                viewModel.sendRaw("STATUS,Bluetooth permission denied")
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        ensureBtConnectPermThenStartServer()

        val navHost =
            supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHost.navController

        findViewById<BottomNavigationView>(R.id.bottom_nav)
            .setupWithNavController(navController)
    }

    private fun ensureBtConnectPermThenStartServer() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S) {
            viewModel.startDefaultListening()
            return
        }

        val granted = ContextCompat.checkSelfPermission(
            this,
            android.Manifest.permission.BLUETOOTH_CONNECT
        ) == PackageManager.PERMISSION_GRANTED

        if (granted) {
            viewModel.startDefaultListening()
        } else {
            btConnectPermLauncher.launch(android.Manifest.permission.BLUETOOTH_CONNECT)
        }
    }
}
