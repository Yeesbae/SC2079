package com.example.sc2079_ay2526s2_grp08

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.example.sc2079_ay2526s2_grp08.bluetooth.BluetoothManager
import com.example.sc2079_ay2526s2_grp08.viewmodel.MainViewModel

class MainViewModelFactory(
    private val bt: BluetoothManager
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(MainViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return MainViewModel(bt) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
