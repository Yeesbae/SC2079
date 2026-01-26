package com.example.sc2079_ay2526s2_grp08.domain

import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager

data class RobotState(
    val x: Int,
    val y: Int,
    val directionDeg: Int
)

data class ArenaState(
    val width: Int,
    val height: Int,
    val obstacles: BooleanArray
)

data class LogEntry(
    val kind: Kind,
    val text: String
) {
    enum class Kind { INFO, IN, OUT, ERROR }
}

data class AppState(
    val mode: BluetoothManager.Mode = BluetoothManager.Mode.NONE,
    val conn: BluetoothManager.State = BluetoothManager.State.DISCONNECTED,
    val statusText: String? = null,

    val robot: RobotState? = null,
    val arena: ArenaState? = null,

    val log: List<LogEntry> = emptyList()
)
