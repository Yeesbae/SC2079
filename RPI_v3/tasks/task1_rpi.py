"""
Task 1 RPi Implementation
Contains image recognition + STM32 movement control

Pipeline (Algorithm Mode):
1. Algo PC sends STM32 commands: ["FW10","BL00","FW20","SNAP3_C","FW10",...,"FIN"]
2. RPi executes each command sequentially via STM32 serial
3. At SNAP commands: send SNAP to Image Rec PC, wait for detection result
4. Forward detection result to Android via Bluetooth
5. Continue to next command after detection is confirmed

PC AUTO-SEND MODE (Hardcoded):
- PC automatically sends detected images: "obstacle_id,confidence,image_id"
- RPi receives and executes STM32 commands based on IMAGE_COMMANDS mapping
"""
import sys
import threading
import time
from pathlib import Path
from queue import Queue, Empty
from typing import Optional

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_server import StreamServer
from communication.pc import PC
from communication.stm32 import STM32
from config.config import Config


class Task1RPI:
    # ========== Movement Mode ==========
    # "hardcoded" - Use IMAGE_COMMANDS mapping (for simple tasks)
    # "algorithm" - Use STM32 commands from Algorithm PC
    # ===================================
    
    # ========== Image ID to STM32 Command Mapping ==========
    # Only used when mode = "hardcoded"
    IMAGE_COMMANDS = {
        "38": "RF090",   # Right arrow → turn right 90°
        "39": "LF090",   # Left arrow → turn left 90°
        "bullseye": "STOP",
    }
    # =======================================================
    
    # Max time to wait for image detection at each obstacle (seconds)
    DETECTION_TIMEOUT = 30.0
    # Time to wait for STM32 acknowledgment (seconds)
    STM32_ACK_TIMEOUT = 10.0
    
    def __init__(self, config: Config, mode: str = "hardcoded"):
        """
        Initialize Task1 RPi
        
        Args:
            config: Configuration object
            mode: "hardcoded" or "algorithm"
        """
        self.config = config
        self.mode = mode
        self.pc = PC()
        self.stm32 = STM32()
        
        # Thread related
        self.pc_receive_thread = None
        self.stream_thread = None
        
        # Store last received image ID
        self.last_image = None
        
        # Path execution state
        self.executing_path = False
        self.current_obstacle_id = None
        
        # Detection result queue - pc_receive puts results here,
        # execute_commands reads from here when waiting at SNAP
        self.detection_queue = Queue()
        
        # Callbacks for external communication (e.g., Bluetooth to Android)
        self.on_image_detected = None  # Callback: on_image_detected(obstacle_id, image_id, confidence)
        self.on_image_binary = None    # Callback: on_image_binary(obstacle_id, image_id, b64jpeg)

    def initialize(self):
        """Initialize connections and start threads"""
        try:
            # Connect to STM32 - try multiple ports
            print("Connecting to STM32...")
            stm32_connected = False
            ports_to_try = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyAMA0"]
            for port in ports_to_try:
                self.stm32.port = port
                if self.stm32.connect():
                    stm32_connected = True
                    break
            if not stm32_connected:
                print("[WARNING] STM32 not connected - movements disabled")
            
            # Start video stream server first
            print("Starting stream server...")
            self.stream_thread = threading.Thread(target=self.stream_start, daemon=True)
            self.stream_thread.start()
            time.sleep(0.1)
            
            # Connect to PC (TCP server - waits for Image Rec PC to connect)
            self.pc.connect()
            
            # Start thread to receive messages from PC
            self.pc_receive_thread = threading.Thread(target=self.pc_receive, daemon=True)
            self.pc_receive_thread.start()
            
            print("Task1 RPi initialized successfully")
        except Exception as e:
            print(f"Initialization failed: {e}")

    def stream_start(self):
        """Start UDP video stream server"""
        StreamServer().start(
            framerate=15, 
            quality=45, 
            is_outdoors=self.config.is_outdoors
        )

    def pc_receive(self) -> None:
        """
        Receive recognition results from Image Rec PC.
        
        Message format: "obstacle_id,confidence,image_id"
        
        Detection results are placed into self.detection_queue
        so that execute_commands() can consume them when waiting.
        
        Auto-reconnects when ImgPC disconnects: reuses the existing server
        socket to accept a new client without rebinding.
        
        Supports both newline-delimited messages (updated pc_client) and
        legacy messages without newlines (old pc_client).
        """
        print("[Task1] PC receive thread started")
        recv_buf = b""         # raw byte buffer for accumulating TCP data
        
        while True:
            # If not connected, wait until initialize() connects us
            if not self.pc.connected:
                time.sleep(0.5)
                continue

            try:
                # Read available data from the socket
                chunk = self.pc.client_socket.recv(4096)
                
                # Empty bytes = client disconnected cleanly
                if not chunk:
                    print("[Task1] ImgPC disconnected (empty recv)")
                    self.pc.connected = False
                    recv_buf = b""
                    self._wait_for_imgpc_reconnect()
                    continue
                
                recv_buf += chunk
                
                # Process all complete messages in the buffer.
                # Messages may or may not be newline-terminated depending on
                # whether the ImgRec PC has the updated pc_client.py.
                while recv_buf:
                    # If buffer contains a newline, split on it
                    if b"\n" in recv_buf:
                        line, recv_buf = recv_buf.split(b"\n", 1)
                        message_rcv = line.decode("utf-8", errors="ignore").strip()
                    else:
                        # No newline yet — check if this looks like a complete
                        # short message (legacy mode without \n delimiters).
                        # IMG_DATA messages are large and need \n to know when
                        # they're complete, so keep buffering those.
                        tentative = recv_buf.decode("utf-8", errors="ignore").strip()
                        if tentative.startswith("IMG_DATA:"):
                            break  # keep buffering until \n arrives
                        # Short messages (detections, NONE, DETECT, etc.)
                        # are < 100 bytes — treat as complete
                        message_rcv = tentative
                        recv_buf = b""
                    
                    if not message_rcv:
                        continue
                    
                    self._handle_imgpc_message(message_rcv)

            except OSError as e:
                print(f"[Task1] ImgPC connection error: {e}")
                self.pc.connected = False
                recv_buf = b""
                self._wait_for_imgpc_reconnect()

    def _handle_imgpc_message(self, message_rcv: str):
        """Process a single complete message from the Image Rec PC."""
        display = message_rcv[:120] + ('...' if len(message_rcv) > 120 else '')
        print(f"[Task1] Received from ImgPC: {display}")

        if "NONE" in message_rcv:
            self.last_image = "NONE"

        elif message_rcv.startswith("IMG_DATA:"):
            # Format: IMG_DATA:<obstacle_id>:<image_id>:<base64_jpeg>
            try:
                parts = message_rcv[len("IMG_DATA:"):].split(":", 2)
                if len(parts) == 3:
                    img_obstacle_id, img_image_id, b64_jpeg = parts
                    # Use the obstacle ID from the current SNAP command
                    # (authoritative) instead of the one from ImgPC
                    authoritative_id = self.current_obstacle_id if self.current_obstacle_id else img_obstacle_id
                    print(f"[Task1] IMG_DATA received: obstacle={authoritative_id} "
                          f"(imgpc said {img_obstacle_id}), "
                          f"image={img_image_id}, size={len(b64_jpeg)} b64 chars")
                    if self.on_image_binary:
                        self.on_image_binary(authoritative_id, img_image_id, b64_jpeg)
                else:
                    print("[Task1] Malformed IMG_DATA message (expected 3 parts)")
            except Exception as img_err:
                print(f"[Task1] Failed to handle IMG_DATA: {img_err}")

        elif "," in message_rcv:
            # Recognition result: "obstacle_id,confidence,image_id"
            msg_split = message_rcv.split(",")
            if len(msg_split) == 3:
                obstacle_id, conf_str, image_id = msg_split
                confidence = None
                try:
                    confidence = float(conf_str)
                except ValueError:
                    pass

                print(f"[Task1] DETECTED: Image {image_id} for obstacle {obstacle_id} (conf: {confidence})")
                self.last_image = image_id

                # Put detection into queue for execute_commands to consume
                self.detection_queue.put({
                    'obstacle_id': obstacle_id,
                    'image_id': image_id,
                    'confidence': confidence
                })

                # Notify external listeners (e.g., send to Android via Bluetooth)
                if self.on_image_detected:
                    self.on_image_detected(obstacle_id, image_id, confidence)

                # In hardcoded mode, also execute movement
                if self.mode == "hardcoded":
                    self._handle_hardcoded_detection(image_id)

            elif "DETECT" in message_rcv:
                obstacle_id = message_rcv.split(",")[1]
                print(f"[Task1] Received DETECT command for obstacle {obstacle_id}")
                self.current_obstacle_id = obstacle_id

            elif "PERFORM STITCHING" in message_rcv:
                num = int(message_rcv.split(",")[1])
                print(f"[Task1] Received STITCH command for {num} images")

    def _wait_for_imgpc_reconnect(self):
        """
        Accept a new ImgPC client on the existing server socket.
        Called when the current client disconnects.
        """
        if self.pc.server_socket is None:
            print("[Task1] No server socket available - cannot wait for ImgPC reconnect")
            return
        try:
            print("[Task1] Waiting for ImgPC to reconnect (TCP port 5000)...")
            self.pc.client_socket, addr = self.pc.server_socket.accept()
            self.pc.connected = True
            self.pc._recv_buffer = b""  # reset line buffer for new connection
            print(f"[Task1] ImgPC reconnected from {addr}")
        except Exception as e:
            print(f"[Task1] ImgPC reconnect failed: {e}")
    
    def _handle_hardcoded_detection(self, image_id: str):
        """Handle detection in hardcoded mode - execute mapped STM32 command"""
        if image_id in self.IMAGE_COMMANDS:
            command = self.IMAGE_COMMANDS[image_id]
            if command:
                print(f"[Task1] Image {image_id} triggers: {command}")
                self.stm32.send(command)
                response = self.stm32.receive(timeout=5.0)
                if response:
                    print(f"[Task1] STM32 response: {response}")
        else:
            print(f"[Task1] Image {image_id} has no hardcoded command")

    def execute_commands(self, commands: list):
        """
        Execute a list of STM32 commands from Algorithm PC.
        
        At each SNAP command, pauses to wait for image detection from
        the Image Rec PC before continuing.
        
        Args:
            commands: List of STM32 commands from Algo PC, e.g.:
                ["SF010", "RF090", "SF020", "SNAP3_C", "SF010", "LF090", "SNAP5_L", "FIN"]
                
                Command types:
                - SFxxx: Forward xxx cm (e.g., SF010 = 10cm, SF020 = 20cm)
                - SBxxx: Backward xxx cm
                - LFyyy: Left forward turn yyy degrees (e.g., LF090 = 90°)
                - RFyyy: Right forward turn yyy degrees (e.g., RF090 = 90°)
                - LByyy: Left backward turn yyy degrees (e.g., LB090 = 90°)
                - RByyy: Right backward turn yyy degrees (e.g., RB090 = 90°)
                - SNAP{id}_{L/C/R}: Take photo for obstacle {id}, camera position L/C/R
                - FIN: Finished - all obstacles visited
        """
        self.executing_path = True
        total = len(commands)
        print(f"\n{'='*60}")
        print(f"[Task1] Starting command execution: {total} commands")
        print(f"[Task1] Commands: {commands}")
        print(f"{'='*60}\n")
        
        for i, cmd in enumerate(commands):
            if not self.executing_path:
                print("[Task1] Execution stopped by user")
                break
            
            cmd = cmd.strip()
            print(f"\n[Task1] [{i+1}/{total}] Executing: {cmd}")
            
            # ---- FIN: Done ----
            if cmd == "FIN":
                print("[Task1] ✓ All obstacles visited! Path complete.")
                # Notify Android
                if self.on_image_detected:
                    self.on_image_detected("DONE", "FIN", 1.0)
                break
            
            # ---- SNAP: Image detection ----
            if cmd.startswith("SNAP"):
                self._handle_snap_command(cmd)
                continue
            
            # ---- Movement commands: SF, SB, LF, RF, LB, RB ----
            if cmd.startswith(("SF", "SB", "LF", "RF", "LB", "RB")):
                self._send_stm32_and_wait(cmd)
                continue
            
            # ---- Unknown command ----
            print(f"[Task1] WARNING: Unknown command '{cmd}', skipping")
        
        self.executing_path = False
        print(f"\n{'='*60}")
        print("[Task1] Command execution complete")
        print(f"{'='*60}\n")
    
    def _send_stm32_and_wait(self, command: str):
        """
        Send a movement command to STM32 and wait for ACK.
        
        Args:
            command: STM32 command string (e.g., "SF010", "RF090")
        """
        if not self.stm32.connected:
            print(f"[Task1] STM32 not connected - skipping {command}")
            return
        
        print(f"[Task1] → STM32: {command}")
        if self.stm32.send(command):
            # Wait for STM32 acknowledgment ('A')
            response = self.stm32.receive(timeout=self.STM32_ACK_TIMEOUT)
            if response:
                print(f"[Task1] ← STM32 ACK: {response}")
            else:
                print(f"[Task1] ⚠ STM32 no ACK for {command} (timeout {self.STM32_ACK_TIMEOUT}s)")
        else:
            print(f"[Task1] ✗ Failed to send {command} to STM32")
    
    def _handle_snap_command(self, snap_cmd: str):
        """
        Handle a SNAP command: trigger image detection and wait for result.
        
        SNAP format: "SNAP{obstacle_id}_{position}" where position is L/C/R
        e.g., "SNAP3_C" means take photo for obstacle 3, camera centered
        
        Flow:
        1. Parse obstacle ID from command
        2. Send SNAP command to Image Rec PC (triggers detection)
        3. Wait for detection result from pc_receive thread (via detection_queue)
        4. Forward result to Android via callback
        5. Continue execution
        
        Args:
            snap_cmd: SNAP command string (e.g., "SNAP3_C")
        """
        # Parse obstacle ID: "SNAP3_C" → obstacle_id = "3"
        snap_body = snap_cmd[4:]  # Remove "SNAP" prefix → "3_C"
        parts = snap_body.split("_")
        obstacle_id = parts[0]
        position = parts[1] if len(parts) > 1 else "C"
        
        self.current_obstacle_id = obstacle_id
        print(f"[Task1] 📸 SNAP obstacle {obstacle_id} (position: {position})")
        
        # Clear any stale detections from queue
        while not self.detection_queue.empty():
            try:
                stale = self.detection_queue.get_nowait()
                print(f"[Task1] Discarding stale detection: {stale}")
            except Empty:
                break
        
        # Send SNAP command to Image Rec PC to trigger detection
        # The PC will analyze the current frame and send back result
        self.pc.send(snap_cmd)
        print(f"[Task1] → ImgPC: {snap_cmd}")
        
        # Wait for detection result from Image Rec PC
        print(f"[Task1] Waiting for detection (timeout: {self.DETECTION_TIMEOUT}s)...")
        try:
            detection = self.detection_queue.get(timeout=self.DETECTION_TIMEOUT)
            
            det_obstacle = detection['obstacle_id']
            det_image = detection['image_id']
            det_conf = detection['confidence']
            
            print(f"[Task1] ✓ Detection received: obstacle={det_obstacle}, "
                  f"image={det_image}, confidence={det_conf}")
            
            # Forward to Android via Bluetooth callback
            if self.on_image_detected:
                self.on_image_detected(obstacle_id, det_image, det_conf)
            
        except Empty:
            print(f"[Task1] ⚠ Detection timeout for obstacle {obstacle_id}!")
            # Still notify Android of timeout
            if self.on_image_detected:
                self.on_image_detected(obstacle_id, "TIMEOUT", 0.0)
    
    def execute_path(self, path_data):
        """
        Execute path data received from Algorithm PC.
        
        Accepts either:
        - dict with "commands" key (new format from updated algo_client)
        - list of waypoints (legacy format - just logs warning)
        
        Args:
            path_data: Either a dict {"commands": [...], "path": [...]} 
                       or a list of waypoint dicts
        """
        if isinstance(path_data, dict) and "commands" in path_data:
            commands = path_data["commands"]
            print(f"[Task1] Received {len(commands)} STM32 commands from Algo PC")
            self.execute_commands(commands)
        elif isinstance(path_data, list):
            # Legacy format - check if it looks like a commands list
            if path_data and isinstance(path_data[0], str):
                # It's already a list of command strings
                self.execute_commands(path_data)
            else:
                print("[Task1] ⚠ Received raw waypoint path (legacy format)")
                print("[Task1]   Update Algo PC to send STM32 commands instead")
                print(f"[Task1]   Path has {len(path_data)} waypoints")
        else:
            print(f"[Task1] Unknown path format: {type(path_data)}")
    
    def send_command(self, command: str) -> Optional[str]:
        """
        Send a direct command to STM32 (used for Bluetooth manual control)
        
        Args:
            command: STM32 command string (e.g., "FW050", "TR090", "STOP")
            
        Returns:
            Response from STM32 or None
        """
        if not self.stm32.connected:
            print("[Task1] STM32 not connected")
            return None
        
        print(f"[Task1] Manual command → STM32: {command}")
        if self.stm32.send(command):
            response = self.stm32.receive(timeout=3.0)
            return response
        return None

    def get_last_image(self) -> str:
        """Get last received image ID"""
        return self.last_image
    
    def send_seen_command(self):
        """Send SEEN command to PC to reset detection state"""
        try:
            self.pc.send("SEEN")
            print("[Task1] Sent SEEN command to PC")
        except Exception as e:
            print(f"[Task1] Failed to send SEEN command: {e}")

    def stop(self):
        """Stop all threads and connections"""
        self.executing_path = False
        try:
            self.stm32.stop()
            self.stm32.disconnect()
            self.pc.disconnect()
            print("Task1 RPi stopped")
        except Exception as e:
            print(f"Error stopping Task1 RPi: {e}")


def main(config: Config):
    """
    Task1 main function
    """
    print("# ------------- Running Task 1, RPi ---------------- #")
    print(f"You are {'out' if config.is_outdoors else 'in'}doors.")
    task1 = Task1RPI(config)
    task1.initialize()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        task1.stop()
