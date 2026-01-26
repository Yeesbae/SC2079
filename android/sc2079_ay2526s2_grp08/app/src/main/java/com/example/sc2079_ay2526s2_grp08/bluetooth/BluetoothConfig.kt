package com.example.sc2079_ay2526s2_grp08.bluetooth

import java.util.UUID

object BluetoothConfig {
    val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
    const val SERVICE_NAME: String = "MDP"

    const val ECHO_WINDOW: Int = 32
    const val READ_BUF_SIZE: Int = 256

    const val SERVER_RETRY_BACKOFF_MS: Long = 200
}