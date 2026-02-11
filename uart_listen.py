"""
Simple UART Listener
====================
Just listens and prints everything received from STM32.
Press Ctrl+C to exit.
"""

import serial
import time

PORT = 'COM3'  # Change this if needed
BAUD = 115200

print(f"Opening {PORT} at {BAUD} baud...")

try:
    ser = serial.Serial(PORT, BAUD, timeout=0.5)
    print(f"Connected! Listening for data...\n")
    print("-" * 50)

    hb_count = 0

    while True:
        data = ser.read(100)
        if data:
            text = data.decode('utf-8', errors='replace')
            hb_count += text.count('HB')
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {repr(text)}  (HB count: {hb_count})")

except KeyboardInterrupt:
    print(f"\n\nExiting. Total heartbeats received: {hb_count}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'ser' in locals():
        ser.close()
