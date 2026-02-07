package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.domain.AppState

/**
 * Pure connection/scanning state transitions derived from BluetoothManager events.
 * Side effects (startServer/stopDiscovery/etc) stay in VM.
 */
object ConnectionReducer {

    fun onStateChanged(state: AppState, ev: BluetoothManager.Event.StateChanged): AppState {
        return state.copy(
            mode = ev.mode,
            conn = ev.state,
            statusText = ev.message ?: state.statusText
        )
    }

    fun onDiscoveryStarted(state: AppState): AppState = state.copy(isScanning = true)

    fun onDiscoveryFinished(state: AppState): AppState = state.copy(isScanning = false)
}
