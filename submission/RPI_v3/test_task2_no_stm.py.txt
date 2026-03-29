#!/usr/bin/env python3
"""
Task 2 Test — No STM32 (with Android Bluetooth)
=================================================
Simulates the STM32 side so you can test the full
RPi ↔ ImgRec PC communication (stream, CAPTURE, detection, stitching)
with real Android Bluetooth for START, but no STM32 hardware.

What this tests:
  - Android → RPi Bluetooth START command
  - RPi video stream → PC
  - PC image recognition (YOLO inference)
  - PC → RPi detection results
  - Image saving with bounding boxes
  - Tiled collage generation on FIN

How to run:
  1. Start this script on RPi:   python3 test_task2_no_stm.py
  2. Start task2 on ImgRec PC:   python3 main.py  (select task 2)
  3. Pair Android phone and send START via Bluetooth
  4. Type commands in this terminal to simulate STM32 messages:
       img    → simulates STM32 sending IMG (take photo)
       bull   → simulates STM32 sending BULL (confirm bull's-eye)
       fin    → simulates STM32 sending FIN (task complete)
       auto   → runs the full sequence automatically (img → img → bull → fin)
       q      → quit

What you should see:
  - Script waits for Android START via Bluetooth before accepting commands
  - After 'img': PC captures, runs YOLO, sends result back.
    RPi prints LEFT/RGHT and the image is saved in MDP_imgrec/images/task_2/
  - After 'fin': PC generates and displays the tiled collage
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from camera.stream_server import StreamServer
from communication.bluetooth import BluetoothHandler
from communication.pc import PC
from config.config import get_config


class MockSTM32:
    """Fake STM32 that logs commands instead of sending over UART."""

    def __init__(self):
        self.connected = True
        self.commands_received = []

    def connect(self):
        return True

    def send(self, cmd):
        self.commands_received.append(cmd)
        print(f"  [MockSTM32] ← RPi sent: {cmd}")
        return True

    def receive(self, timeout=1.0):
        # Simulate ACK for reverse commands etc.
        print(f"  [MockSTM32] → ACK (simulated)")
        return "A"

    def receive_task2_message(self, timeout=30.0):
        # Not used in this test — we inject messages manually
        time.sleep(timeout)
        return None

    def flush_input(self):
        return 0

    def disconnect(self):
        self.connected = False


def main():
    config = get_config()

    print("\n" + "=" * 60)
    print("TASK 2 TEST — No STM32 (with Android Bluetooth)")
    print("=" * 60)

    # --- Set up real connections ---
    bt = BluetoothHandler()
    pc = PC()
    mock_stm = MockSTM32()
    start_event = threading.Event()

    # --- Connect Bluetooth ---
    print("\nWaiting for Android Bluetooth connection...")
    if bt.connect():
        print("Android Bluetooth connected!")
    else:
        print("Bluetooth connection failed! Continuing without BT.")

    # --- BT receive thread: wait for START from Android ---
    def bt_receive_loop():
        while True:
            if not bt.is_connected():
                time.sleep(0.5)
                continue
            msg = bt.receive_nonblocking(timeout=0.1)
            if msg is None:
                continue
            msg = msg.strip().upper()
            print(f"  [BT ← Android] {msg}")
            if "START" in msg:
                print("  → START received from Android!")
                start_event.set()

    bt_thread = threading.Thread(target=bt_receive_loop, daemon=True)
    bt_thread.start()

    print("\nStarting video stream server...")
    stream_thread = threading.Thread(
        target=lambda: StreamServer().start(
            framerate=15, quality=45, is_outdoors=config.is_outdoors
        ),
        daemon=True,
    )
    stream_thread.start()
    time.sleep(0.1)

    print("Waiting for ImgRec PC to connect (TCP)...")
    pc.connect()
    print("ImgRec PC connected!\n")

    # --- Recognition result handling (same as task2_rpi) ---
    recognition_event = threading.Event()
    recognition_result_holder = [None]  # mutable container

    LEFT_ARROW_ID = "39"
    RIGHT_ARROW_ID = "38"
    BULLSEYE_ID = "41"
    CMD_LEFT = "W"
    CMD_RIGHT = "E"
    CMD_CONFIRM = "CONF"

    obstacle_count = [0]

    def pc_receive_loop():
        """Listen for results from ImgRec PC."""
        while True:
            try:
                msg = pc.receive()
                if msg is None:
                    continue
                print(f"  [PC → RPi] {msg}")

                if "NONE" in msg:
                    print("  → PC saw nothing")
                    recognition_event.set()
                    continue

                if "," in msg:
                    parts = msg.strip().split(",")
                    if len(parts) == 2:
                        conf_str, obj_id = parts
                        try:
                            conf = float(conf_str)
                        except ValueError:
                            conf = None
                        print(f"  → Object ID: {obj_id}, Confidence: {conf}")
                        if obj_id == LEFT_ARROW_ID:
                            recognition_result_holder[0] = CMD_LEFT
                        elif obj_id == RIGHT_ARROW_ID:
                            recognition_result_holder[0] = CMD_RIGHT
                        elif obj_id == BULLSEYE_ID:
                            recognition_result_holder[0] = "BULL"
                    recognition_event.set()

            except OSError as e:
                print(f"  [PC receive error] {e}")
                break

    recv_thread = threading.Thread(target=pc_receive_loop, daemon=True)
    recv_thread.start()

    # --- Command handlers ---
    def do_img():
        """Simulate STM32 IMG request."""
        obstacle_count[0] += 1
        print(f"\n[SIM] === IMG (obstacle {obstacle_count[0]}) ===")
        recognition_event.clear()
        recognition_result_holder[0] = None

        pc.send("CAPTURE")
        print("  [RPi → PC] CAPTURE")

        got = recognition_event.wait(timeout=20.0)
        if got and recognition_result_holder[0] is not None:
            direction = recognition_result_holder[0]
            print(f"  [RPi → STM32] {direction}")
            mock_stm.send(direction)
            pc.send("SEEN")
            print(f"  [RPi → PC] SEEN (obstacle {obstacle_count[0]} done)")
        else:
            print("  → No valid detection. In real flow, RPi would reverse and retry.")

    def do_bull():
        """Simulate STM32 BULL request."""
        print(f"\n[SIM] === BULL (confirm bull's-eye) ===")
        recognition_event.clear()
        recognition_result_holder[0] = None
        pc.send("CAPTURE_BULL")
        print("  [RPi → PC] CAPTURE_BULL (bullseye-only mode)")
        recognition_event.wait(timeout=10.0)
        if recognition_result_holder[0] == "BULL":
            print(f"  → Bullseye detected!")
        else:
            print(f"  → No bullseye detected (result: {recognition_result_holder[0]})")
        print(f"  [RPi → STM32] {CMD_CONFIRM}")
        mock_stm.send(CMD_CONFIRM)

    def do_fin():
        """Simulate STM32 FIN."""
        print(f"\n[SIM] === FIN (task complete) ===")
        pc.send("FIN")
        print("  [RPi → PC] FIN — collage should appear on PC")

    def do_auto():
        """Run the full Task 2 sequence automatically."""
        print("\n[AUTO] Running full Task 2 sequence...")
        print("[AUTO] Simulating: START → IMG → IMG → BULL → FIN\n")
        time.sleep(0.5)

        do_img()
        time.sleep(1)

        do_img()
        time.sleep(1)

        do_bull()
        time.sleep(1)

        do_fin()
        print("\n[AUTO] Sequence complete!")

    # --- Wait for Android START via Bluetooth ---
    print("\n" + "=" * 60)
    print("Waiting for Android to send START via Bluetooth...")
    print("(Press Ctrl+C to skip and proceed without START)")
    print("=" * 60)

    try:
        start_event.wait(timeout=120.0)  # 2 minute timeout
        if start_event.is_set():
            print("\n[OK] START received! Ready for commands.")
        else:
            print("\n[TIMEOUT] No START received after 2 minutes. Proceeding anyway.")
    except KeyboardInterrupt:
        print("\n[SKIP] Skipping START wait. Proceeding to commands.")

    # --- Interactive loop ---
    print("\n" + "=" * 60)
    print("Commands:")
    print("  img    — simulate STM32 IMG (triggers CAPTURE)")
    print("  bull   — simulate STM32 BULL (triggers CAPTURE + CONF)")
    print("  fin    — simulate STM32 FIN (triggers collage)")
    print("  auto   — run full sequence: img → img → bull → fin")
    print("  q      — quit")
    print("=" * 60)

    try:
        while True:
            cmd = input("\n>> ").strip().lower()
            if cmd == "q":
                break
            elif cmd == "img":
                do_img()
            elif cmd == "bull":
                do_bull()
            elif cmd == "fin":
                do_fin()
            elif cmd == "auto":
                do_auto()
            else:
                print("Unknown command. Use: start, img, bull, fin, auto, q")
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    finally:
        pc.disconnect()
        bt.disconnect(keep_server=False)
        print("\n[Test] Done. Check MDP_imgrec/images/task_2/ for saved images.")
        print("[Test] Commands STM32 would have received:", mock_stm.commands_received)


if __name__ == "__main__":
    main()
