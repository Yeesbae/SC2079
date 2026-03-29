package com.example.sc2079_ay2526s2_grp08.bluetooth

import android.bluetooth.BluetoothDevice
import com.example.sc2079_ay2526s2_grp08.domain.BtDevice

/**
 * Android-specific mapping helpers.
 * Keeps MainViewModel cleaner and avoids repeating permission-guarded property access.
 */
object BtDeviceMapper {

    fun toBtDevice(device: BluetoothDevice, bonded: Boolean? = null): BtDevice {
        val safeName = try { device.name } catch (_: SecurityException) { null }
        val safeAddr = try { device.address } catch (_: SecurityException) { "unknown" }
        val isBonded = bonded ?: run {
            try { device.bondState == BluetoothDevice.BOND_BONDED } catch (_: SecurityException) { false }
        }
        return BtDevice(name = safeName, address = safeAddr, bonded = isBonded)
    }
}
