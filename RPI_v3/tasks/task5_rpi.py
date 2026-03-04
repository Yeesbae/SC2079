"""
Task 5 RPi Implementation - Image Rec PC Communication Test
Simple test mode to verify communication between Image Recognition PC and RPi

The PC will send detected image results and RPi will print them out.
Message format from PC: "obstacle_id,confidence,image_id" or commands like "SEEN", "STITCH", "NONE"
"""
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Add project path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera.stream_server import StreamServer
from communication.pc import PC
from config.config import Config


class Task5RPI:
    def __init__(self, config: Config):
        """
        Initialize Task5 RPi - Communication test with Image Rec PC
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.pc = PC()
        
        # Thread related
        self.pc_receive_thread = None
        self.stream_thread = None
        self.running = True
        
        # Stats
        self.message_count = 0
        self.last_image = None

    def initialize(self):
        """
        Initialize connections and start threads
        """
        try:
            # Start video stream server first
            print("[Task5] Starting stream server...")
            self.stream_thread = threading.Thread(target=self.stream_start, daemon=True)
            self.stream_thread.start()
            time.sleep(0.1)
            
            # Connect to PC (TCP server - wait for PC to connect)
            print("[Task5] Waiting for Image Rec PC to connect...")
            self.pc.connect()
            print("[Task5] Image Rec PC connected!")
            
            # Start thread to receive messages from PC
            self.pc_receive_thread = threading.Thread(target=self.pc_receive, daemon=True)
            self.pc_receive_thread.start()
            
            print("[Task5] Initialization complete - Ready to receive image detection results")
            print("=" * 60)
            
        except Exception as e:
            print(f"[Task5] Initialization failed: {e}")
            self.running = False

    def stream_start(self):
        """
        Start UDP video stream server
        """
        try:
            StreamServer().start(
                framerate=15, 
                quality=45, 
                is_outdoors=self.config.is_outdoors
            )
        except Exception as e:
            print(f"[Task5] Stream server error: {e}")

    def pc_receive(self) -> None:
        """
        Receive recognition results and commands from PC
        
        Message formats from PC:
        1. Recognition result: "obstacle_id,confidence,image_id"
           Example: "1,0.95,38" (obstacle 1, 95% confidence, image ID 38)
        
        2. No detection: "NONE"
        
        3. Commands: "SEEN", "STITCH"
        """
        print("[Task5] PC receive thread started - listening for messages...")
        
        while self.running:
            try:
                message_rcv = self.pc.receive()
                
                if not message_rcv:
                    continue
                
                self.message_count += 1
                timestamp = time.strftime("%H:%M:%S")
                
                print("\n" + "=" * 60)
                print(f"[{timestamp}] MESSAGE #{self.message_count} FROM IMAGE REC PC:")
                print("-" * 60)
                
                # Parse the message
                if "NONE" in message_rcv.upper():
                    print("  Type: No detection")
                    print(f"  Raw: {message_rcv}")
                    self.last_image = "NONE"
                    
                elif "SEEN" in message_rcv.upper():
                    print("  Type: SEEN command (reset detection state)")
                    print(f"  Raw: {message_rcv}")
                    
                elif "STITCH" in message_rcv.upper():
                    print("  Type: STITCH command (prepare for image stitching)")
                    print(f"  Raw: {message_rcv}")
                    
                elif "," in message_rcv:
                    # Recognition result format: "obstacle_id,confidence,image_id"
                    msg_split = message_rcv.split(",")
                    
                    if len(msg_split) == 3:
                        obstacle_id, conf_str, image_id = msg_split
                        
                        try:
                            confidence = float(conf_str)
                            print("  Type: Image detection result")
                            print(f"  Obstacle ID: {obstacle_id}")
                            print(f"  Image ID: {image_id}")
                            print(f"  Confidence: {confidence:.2%}")
                            self.last_image = image_id
                        except ValueError:
                            print("  Type: Unknown (failed to parse confidence)")
                            print(f"  Raw: {message_rcv}")
                    else:
                        print("  Type: Unknown format")
                        print(f"  Raw: {message_rcv}")
                else:
                    print("  Type: Other")
                    print(f"  Raw: {message_rcv}")
                
                print("=" * 60)
                
            except Exception as e:
                if self.running:
                    print(f"\n[Task5] Error receiving from PC: {e}")
                    print("[Task5] Connection may have been lost")
                break
        
        print("[Task5] PC receive thread stopped")

    def get_last_image(self):
        """
        Get the last detected image ID
        
        Returns:
            Last image ID or None
        """
        return self.last_image

    def send_command(self, command: str) -> Optional[str]:
        """
        Send command to PC (for testing)
        
        Args:
            command: Command string to send
            
        Returns:
            Response from PC or None
        """
        try:
            self.pc.send(command)
            print(f"[Task5] Sent to PC: {command}")
            return f"ACK:{command}"
        except Exception as e:
            print(f"[Task5] Failed to send command: {e}")
            return None

    def stop(self):
        """
        Stop all threads and disconnect
        """
        print("[Task5] Stopping...")
        self.running = False
        
        # Give threads time to finish
        time.sleep(0.5)
        
        # Disconnect from PC
        try:
            self.pc.disconnect()
        except:
            pass
        
        print("[Task5] Stopped")
        print(f"[Task5] Total messages received: {self.message_count}")


# =============================================================================
# Standalone Test (Optional)
# =============================================================================
if __name__ == "__main__":
    """
    Standalone test mode for Task5
    Run directly: python task5_rpi.py
    """
    print("\n" + "=" * 60)
    print("TASK 5 - IMAGE REC PC COMMUNICATION TEST")
    print("=" * 60)
    print("\nThis test will:")
    print("  1. Start video stream server (UDP)")
    print("  2. Wait for Image Rec PC to connect (TCP)")
    print("  3. Print all messages received from PC")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)
    
    from config.config import get_config
    
    config = get_config()
    task5 = Task5RPI(config)
    
    try:
        task5.initialize()
        
        # Keep running until interrupted
        while task5.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[Task5] Interrupted by user")
    finally:
        task5.stop()
        print("[Task5] Test ended")
