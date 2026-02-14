"""
Communication Package
=====================
Multiprocessing-based communication handlers for MDP robot.

Modules:
- android.py: Bluetooth RFCOMM communication with Android tablet
- algorithm.py: WiFi TCP/IP communication with algorithm computer
- rpi.py: USB/UART communication with STM32 microcontroller

Usage:
    from Communication.android import start_bluetooth_process
    from Communication.algorithm import start_wifi_process
    from Communication.rpi import start_stm32_process
"""

from .android import start_bluetooth_process, BluetoothProcess
from .algorithm import start_wifi_process, WiFiProcess
from .rpi import start_stm32_process, STM32Process

__all__ = [
    'start_bluetooth_process',
    'start_wifi_process', 
    'start_stm32_process',
    'BluetoothProcess',
    'WiFiProcess',
    'STM32Process'
]
