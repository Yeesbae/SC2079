package com.example.sc2079_ay2526s2_grp08.viewmodel.reducers

import android.bluetooth.BluetoothDevice
import com.example.sc2079_ay2526s2_grp08.domain.AppState
import com.example.sc2079_ay2526s2_grp08.domain.BtDevice

/**
 * Pure device discovery state transitions.
 * Bluetooth scanning actions are still owned by BluetoothManager.
 */
object DiscoveryReducer {

    fun setPairedDevices(state: AppState, paired: List<BtDevice>): AppState {
        return state.copy(pairedDevices = paired)
    }

    fun startScan(state: AppState): AppState {
        return state.copy(scannedDevices = emptyList(), isScanning = true)
    }

    fun stopScan(state: AppState): AppState {
        return state.copy(isScanning = false)
    }

    fun clearScanResults(state: AppState): AppState {
        return state.copy(scannedDevices = emptyList())
    }

    fun onDiscoveryStarted(state: AppState): AppState {
        return state.copy(isScanning = true)
    }

    fun onDiscoveryFinished(state: AppState): AppState {
        return state.copy(isScanning = false)
    }

    fun onDeviceFound(state: AppState, device: BtDevice): AppState {
        val next = (state.scannedDevices + device).distinctBy { it.address }
        return state.copy(scannedDevices = next)
    }
}
