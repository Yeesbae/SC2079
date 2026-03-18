"""
Task 2 RPi Implementation — Fastest Car

Protocol (all RPi→STM32 messages are 5 bytes, null-padded):
  RPi → STM32:  STRT\0, LEFT\0, RGHT\0, CONF\0
  STM32 → RPi:  IMG\r\n, BULL\n, FIN\r\n

Flow:
  1. Android sends START via Bluetooth → RPi
  2. RPi sends STRT to STM32 → car starts driving
  3. STM32 sends IMG → RPi captures photo, detects arrow, replies LEFT or RGHT
     (repeats for each obstacle)
  4. STM32 sends BULL → RPi checks for bull's-eye, replies CONF
  5. STM32 sends FIN → task complete
"""
import sys
import threading
import time
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_server import StreamServer
from communication.bluetooth import BluetoothHandler
from communication.pc import PC
from communication.stm32 import STM32
from config.config import Config


class Task2RPI:
    def __init__(self, config: Config):
        self.config = config
        self.bt = BluetoothHandler()
        self.pc = PC()
        self.stm = STM32()
        self.stm32_ok = False

        # Thread related
        self.bt_receive_thread = None
        self.stm32_receive_thread = None
        self.pc_receive_thread = None
        self.stream_thread = None

        # Image class IDs from the model
        self.LEFT_ARROW_ID = "39"
        self.RIGHT_ARROW_ID = "38"

        # ========== Task 2 Protocol Commands (RPi → STM32) ==========
        self.CMD_START   = "STRT"   # Begin Task 2 (padded to STRT\0)
        self.CMD_LEFT    = "LEFT"   # Arrow result: go left (LEFT\0)
        self.CMD_RIGHT   = "RGHT"   # Arrow result: go right (RGHT\0)
        self.CMD_CONFIRM = "CONF"   # Bull's-eye confirmed (CONF\0)
        # =============================================================

        # Event: Android sends START via BT → RPi forwards to STM32
        self.start_event = threading.Event()

        # Event used to pass recognition result from PC-receive thread
        self.recognition_event = threading.Event()
        self.recognition_result = None  # Will hold "LEFT"/"RGHT" or None

    def initialize(self):
        """Initialize connections and start threads."""
        try:
            # Connect Bluetooth (wait for Android)
            print("[Task2] Waiting for Android Bluetooth connection...")
            if not self.bt.connect():
                print("[Task2] Bluetooth connection failed!")

            # Connect STM32
            print("Connecting to STM32...")
            ports_to_try = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyAMA0"]
            for port in ports_to_try:
                self.stm.port = port
                if self.stm.connect():
                    self.stm32_ok = True
                    break

            if not self.stm32_ok:
                print("[Task2] STM32 not connected! Check USB cable.")

            # Start video stream server
            print("Starting stream server...")
            self.stream_thread = threading.Thread(target=self.stream_start, daemon=True)
            self.stream_thread.start()
            time.sleep(0.1)

            # Connect to PC (TCP server – waits for PC client)
            self.pc.connect()

            # Flush STM32 buffer after PC connection
            if self.stm32_ok:
                self.stm.flush_input()

            # Start Bluetooth receive thread (listens for START from Android)
            self.bt_receive_thread = threading.Thread(target=self.bt_receive_loop, daemon=True)
            self.bt_receive_thread.start()

            # Start a single persistent thread to receive PC results
            self.pc_receive_thread = threading.Thread(target=self.pc_receive_loop, daemon=True)
            self.pc_receive_thread.start()

            # Start thread that listens for STM32 snap commands
            self.stm32_receive_thread = threading.Thread(target=self.stm32_receive, daemon=True)
            self.stm32_receive_thread.start()

            print("Task2 RPi initialized successfully")
        except Exception as e:
            print(f"Initialization failed: {e}")

    def stream_start(self):
        """Start UDP video stream server."""
        StreamServer().start(
            framerate=15,
            quality=45,
            is_outdoors=self.config.is_outdoors,
        )

    # ------------------------------------------------------------------ #
    #  Android → RPi (BT) : listen for START, signal start_event
    # ------------------------------------------------------------------ #
    def bt_receive_loop(self) -> None:
        """
        Listen for Bluetooth messages from Android.
        When START is received, signal start_event so the STM32 thread
        can send STRT to STM32 and begin listening.
        """
        print("[Task2] BT receive thread started")
        while True:
            if not self.bt.is_connected():
                time.sleep(0.5)
                continue

            msg = self.bt.receive_nonblocking(timeout=0.1)
            if msg is None:
                continue

            msg = msg.strip().upper()
            print(f"[Task2] BT from Android: {msg}")

            if "START" in msg:
                print("[Task2] START received from Android")
                self.start_event.set()

    # ------------------------------------------------------------------ #
    #  Task 2 state machine (STM32 thread)
    # ------------------------------------------------------------------ #
    def stm32_receive(self) -> None:
        """
        Task 2 main loop:
        1. Wait for Android START
        2. Send STRT to STM32
        3. Loop: handle IMG / BULL / FIN messages
        """
        print("[Task2] STM32 thread started – waiting for START from Android")
        self.start_event.wait()
        print("[Task2] START received – sending STRT to STM32")

        if self.stm32_ok and self.stm.connected:
            self.stm.send(self.CMD_START)
        else:
            print("[Task2] WARNING: STM32 not connected, cannot send STRT")

        # Main message loop
        while True:
            if not self.stm32_ok or not self.stm.connected:
                time.sleep(0.5)
                continue

            msg = self.stm.receive_task2_message(timeout=30.0)
            if msg is None:
                continue

            if msg == "IMG":
                self.handle_img_request()
            elif msg == "BULL":
                self.handle_bull_request()
            elif msg == "FIN":
                self.handle_fin()
                break  # Task complete

    # ------------------------------------------------------------------ #
    #  IMG handler: capture photo → detect arrow → send LEFT or RGHT
    # ------------------------------------------------------------------ #
    def handle_img_request(self) -> None:
        """STM32 stopped at obstacle and needs arrow direction."""
        print("[Task2] IMG received – requesting image recognition from PC")

        self.recognition_event.clear()
        self.recognition_result = None

        # Tell PC to capture / recognise
        self.pc.send("CAPTURE")

        # Wait for pc_receive_loop to set the result
        got_result = self.recognition_event.wait(timeout=15.0)

        if got_result and self.recognition_result is not None:
            print(f"[Task2] Sending {self.recognition_result} to STM32")
            self.stm.send(self.recognition_result)
            # Tell PC this obstacle is done so it increments its counter
            self.pc.send("SEEN")
        else:
            print("[Task2] No valid arrow detection – not sending direction")

    # ------------------------------------------------------------------ #
    #  BULL handler: confirm bull's-eye → send CONF
    # ------------------------------------------------------------------ #
    def handle_bull_request(self) -> None:
        """STM32 facing carpark and needs bull's-eye confirmation."""
        print("[Task2] BULL received – confirming bull's-eye")

        # Capture an image for verification (optional: add actual detection)
        self.recognition_event.clear()
        self.recognition_result = None
        self.pc.send("CAPTURE")
        self.recognition_event.wait(timeout=10.0)

        # Always confirm for now (STM32 expects CONF to proceed)
        print(f"[Task2] Sending {self.CMD_CONFIRM} to STM32")
        self.stm.send(self.CMD_CONFIRM)

    # ------------------------------------------------------------------ #
    #  FIN handler: task complete
    # ------------------------------------------------------------------ #
    def handle_fin(self) -> None:
        """STM32 has parked. Task 2 is complete."""
        print("[Task2] FIN received – Task 2 complete! Robot has parked.")
        # Tell PC to generate the tiled collage of all recognized images
        self.pc.send("FIN")
        if self.bt.is_connected():
            self.bt.send("FIN")

    # ------------------------------------------------------------------ #
    #  PC → RPi : single persistent thread that reads PC messages
    # ------------------------------------------------------------------ #
    def pc_receive_loop(self) -> None:
        """
        Persistent thread that reads all messages from PC.
        When a recognition result arrives it sets recognition_result
        to the protocol command ("LEFT" or "RGHT") and signals
        recognition_event so the STM32 thread can proceed.
        """
        print("[Task2] PC receive thread started")
        while True:
            try:
                message_rcv = self.pc.receive()
                if message_rcv is None:
                    continue
                print(f"[Task2] Received from PC: {message_rcv}")

                if "NONE" in message_rcv:
                    print("[Task2] PC saw nothing")
                    self.recognition_event.set()
                    continue

                if "," in message_rcv:
                    msg_split = message_rcv.split(",")
                    if len(msg_split) == 2:
                        conf_str, object_id = msg_split
                        try:
                            confidence = float(conf_str)
                        except ValueError:
                            confidence = None
                        print(f"[Task2] OBJECT ID: {object_id}, Confidence: {confidence}")

                        if object_id == self.LEFT_ARROW_ID:
                            print("[Task2] Detected LEFT arrow")
                            self.recognition_result = self.CMD_LEFT
                        elif object_id == self.RIGHT_ARROW_ID:
                            print("[Task2] Detected RIGHT arrow")
                            self.recognition_result = self.CMD_RIGHT

                    self.recognition_event.set()

            except OSError as e:
                print(f"[Task2] Error receiving from PC: {e}")
                break

    def stop(self):
        """Stop all connections."""
        try:
            self.bt.disconnect(keep_server=False)
            self.pc.disconnect()
            if self.stm32_ok:
                self.stm.disconnect()
            print("Task2 RPi stopped")
        except Exception as e:
            print(f"Error stopping Task2 RPi: {e}")


def main(config: Config):
    """Task2 main function."""
    print("# ------------- Running Task 2, RPi ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    task2 = Task2RPI(config)
    task2.initialize()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        task2.stop()
