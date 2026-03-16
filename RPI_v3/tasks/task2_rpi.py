"""
Task 2 RPi Implementation

Flow:
1. STM32 sends a command to RPi to take a picture
2. RPi tells PC to capture/recognise from the video stream
3. PC sends back the recognition result
4. RPi sends the turn command (left/right) back to STM32
"""
import sys
import threading
import time
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_server import StreamServer
from communication.pc import PC
from communication.stm32 import STM32
from config.config import Config


class Task2RPI:
    def __init__(self, config: Config):
        self.config = config
        self.pc = PC()
        self.stm = STM32()
        self.stm32_ok = False

        # Thread related
        self.stm32_receive_thread = None
        self.pc_receive_thread = None
        self.stream_thread = None

        # Left and right arrow IDs (adjust according to your model)
        self.LEFT_ARROW_ID = "39"
        self.RIGHT_ARROW_ID = "38"

        # ========== STM32 commands for Task 2 ==========
        self.STM32_ACK_TIMEOUT = 10.0
        self.STM32_SNAP_CMD = "SNAP"       # Command STM32 sends to request a picture
        self.LEFT_COMMANDS = ["LF090"]      # Left forward turn 90°
        self.RIGHT_COMMANDS = ["RF090"]     # Right forward turn 90°
        # ================================================

        # Event used to pass recognition result from PC-receive to STM32-receive flow
        self.recognition_event = threading.Event()
        self.recognition_result = None      # Will hold the turn commands list or None

    def initialize(self):
        """Initialize connections and start threads."""
        try:
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
    #  STM32 → RPi : listen for snap command, request recognition, reply
    # ------------------------------------------------------------------ #
    def stm32_receive(self) -> None:
        """
        Listen for commands from STM32.
        When STM32 sends the snap command, tell PC to capture an image,
        wait for the recognition result (set by pc_receive_loop),
        then send the turn command back to STM32.
        """
        print("[Task2] STM32 receive thread started")
        while True:
            if not self.stm32_ok or not self.stm.connected:
                time.sleep(0.5)
                continue

            response = self.stm.receive(timeout=1.0)
            if response is None:
                continue

            print(f"[Task2] STM32 says: {response}")

            if self.STM32_SNAP_CMD in response.upper():
                print("[Task2] Snap command received – requesting recognition from PC")

                # Reset event before requesting
                self.recognition_event.clear()
                self.recognition_result = None

                # Tell PC to capture / recognise
                self.pc.send("CAPTURE")

                # Wait for pc_receive_loop to set the result
                got_result = self.recognition_event.wait(timeout=15.0)

                if got_result and self.recognition_result is not None:
                    self.send_stm32_commands(self.recognition_result)
                else:
                    print("[Task2] No valid recognition result – not sending turn command")

    # ------------------------------------------------------------------ #
    #  PC → RPi : single persistent thread that reads PC messages
    # ------------------------------------------------------------------ #
    def pc_receive_loop(self) -> None:
        """
        Persistent thread that reads all messages from PC.
        When a recognition result arrives it sets recognition_result
        and signals recognition_event so stm32_receive can proceed.
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
                            self.recognition_result = self.LEFT_COMMANDS
                        elif object_id == self.RIGHT_ARROW_ID:
                            print("[Task2] Detected RIGHT arrow")
                            self.recognition_result = self.RIGHT_COMMANDS

                    self.recognition_event.set()

            except OSError as e:
                print(f"[Task2] Error receiving from PC: {e}")
                break

    # ------------------------------------------------------------------ #
    #  RPi → STM32 : send turn commands
    # ------------------------------------------------------------------ #
    def send_stm32_commands(self, commands):
        """Send a list of commands to STM32, waiting for ACK after each."""
        if not self.stm32_ok or not self.stm.connected:
            print("[Task2] STM32 not connected - command not sent")
            return

        for cmd in commands:
            print(f"[Task2] -> STM32: {cmd}")
            if self.stm.send(cmd):
                response = self.stm.receive(timeout=self.STM32_ACK_TIMEOUT)
                if response:
                    print(f"[Task2] <- STM32 ACK: {response}")
                else:
                    print(f"[Task2] STM32 no ACK for {cmd}")
            else:
                print(f"[Task2] Failed to send {cmd}")

    def stop(self):
        """Stop all connections."""
        try:
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
