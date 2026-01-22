package com.example.sc2079_ay2526s2_grp08

import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

class MainActivity : AppCompatActivity() {
    private lateinit var tvStatus: TextView
    private lateinit var btnConnect: Button

    private val requestBtConnect =
        registerForActivityResult(ActivityResultContracts.RequestPermission()){ granted ->
            if(!granted){
                Toast.makeText(this, "Bluetooth Permission Required", Toast.LENGTH_SHORT).show()
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        btnConnect = findViewById(R.id.btnConnect)

        ensureBtConnectPermission()

        btnConnect.setOnClickListener{
            tvStatus.text = "Connect clicked"
        }

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
    }

    private fun hasBtConnectPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S){
            ContextCompat.checkSelfPermission(
                this,
                android.Manifest.permission.BLUETOOTH_CONNECT,
            ) == PackageManager.PERMISSION_GRANTED
        } else true
    }

    private fun ensureBtConnectPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !hasBtConnectPermission()) {
            requestBtConnect.launch(android.Manifest.permission.BLUETOOTH_CONNECT)
        }
    }
}