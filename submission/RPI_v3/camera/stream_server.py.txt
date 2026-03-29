import base64
import socket
import time
from threading import Thread

import cv2
from picamera2 import Picamera2
from libcamera import Transform


class StreamServer:
    # define constants.
    def define_constants(self):
        self.BUFF_SIZE = 65536
        # ========== MODIFY: Change to your RPi IP address ==========
        self.HOST_ADDR = ("192.168.8.1", 5005)
        # =============================================================
        self.REQ_STREAM = b"stream_request"

    def __init__(self):
        # define constants.
        self.define_constants()

        # initialise socket.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        self.sock.bind(self.HOST_ADDR)
        print(f"Bound stream server to {self.HOST_ADDR}.")
        self.sock.settimeout(1)

        # define client address (used to send stream to).
        self.client_addr = None

        # start receiving thread (and exit flag).
        self.exit = False
        Thread(target=self.receive_proc).start()

    # thread processto listen to incoming requests, and set client address accordingly.
    def receive_proc(self):
        while not self.exit:
            try:
                msg, client_addr = self.sock.recvfrom(self.BUFF_SIZE)
                print(f"received {msg} from {client_addr}.")
                if msg == self.REQ_STREAM:
                    print(f"Redirecting stream to {client_addr}.")
                    self.client_addr = client_addr
            except:
                pass

    # main server thread.
    def start(self, resolution=(640, 480), framerate=15, quality=45, is_outdoors=False, brighten=False):
        # NOTE: Resolution/quality tuning for RPi stability:
        # - (640, 480) @ quality=45  → ~15-25KB per frame (most stable)
        # - (960, 720) @ quality=35  → ~30-45KB per frame (balanced)
        # - (1280, 720) @ quality=30 → ~50-65KB per frame (may crash on RPi 3)
        # Max UDP packet: 65536 bytes. If frames exceed this, they're skipped.
        
        equalizeHist = brighten  # Enable to improve contrast in dim conditions
        # start main camera.
        # ========== NOTE: If not using Raspberry Pi camera, replace picamera2 section ==========
        picam2 = Picamera2()
        
        # Configure camera for video streaming with flip transform
        config = picam2.create_video_configuration(
            main={"size": resolution, "format": "RGB888"},
            transform=Transform(hflip=1, vflip=1)
        )
        picam2.configure(config)
        picam2.start()
        
        time.sleep(0.1)  # Allow camera to initialize
        
        # ========== Camera auto-exposure settings ==========
        # By default, auto-exposure (AE) is ON - camera auto-adjusts to lighting
        # These settings fine-tune the auto-exposure behavior
        try:
            picam2.set_controls({
                "AeEnable": True,           # Keep auto-exposure ON (auto-adjusts to bright/dim)
                "AwbEnable": True,          # Keep auto white balance ON
                "Brightness": 0.0,          # Fine-tune: -1.0 (darker) to 1.0 (brighter), 0 = neutral
                "Contrast": 1.0,            # Fine-tune: 0.0 to 2.0, 1.0 = default
                # "AeExposureMode": 0,      # 0=Normal, 1=Short, 2=Long, 3=Custom
                # "AeConstraintMode": 0,    # 0=Normal, 1=Highlight (avoids overexposure)
            })
            print("Camera auto-exposure enabled (auto-adjusts to lighting)")
        except Exception as e:
            print(f"Note: Camera controls adjustment skipped: {e}")
        # ===================================================
        
        # Set camera controls for outdoor conditions
        # Note: picamera2 control API differs from old picamera
        # For outdoor settings, we'll rely on automatic exposure/AWB
        # If you need manual control, check available controls with:
        # print(picam2.camera_controls)
        if is_outdoors:
            # Try to set controls if available (may vary by camera model)
            try:
                # Adjust exposure and gain for bright outdoor conditions
                # These control names may need adjustment based on your camera
                controls = {}
                # Some cameras support these, but names may differ
                # picam2.set_controls(controls)  # Uncomment and adjust if needed
                pass
            except Exception as e:
                print(f"Note: Camera controls adjustment skipped: {e}")
            # equalizeHist = True
        
        # Main capture loop
        frame_errors = 0
        frame_count = 0
        while not self.exit:
            try:
                # Capture frame
                img = picam2.capture_array()
                
                # Validate frame was captured
                if img is None:
                    print(f"[WARN] Empty frame captured, skipping")
                    time.sleep(0.1)
                    continue
                
                # Check frame dimensions are valid
                if img.shape[0] == 0 or img.shape[1] == 0:
                    print(f"[WARN] Invalid frame dimensions: {img.shape}, skipping")
                    time.sleep(0.1)
                    continue
                
                frame_count += 1
                if frame_count % 100 == 0:
                    print(f"[Stream] Frames sent: {frame_count}")
                
                # Convert RGB to BGR for OpenCV
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                if equalizeHist:
                    tmp = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    img = cv2.equalizeHist(tmp)
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

                # get encoding.
                encode_result = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
                if not encode_result[0]:
                    print(f"[WARN] Failed to encode frame, skipping")
                    continue
                buffer = encode_result[1]
                
                # encode in base64 for further compression.
                buffer = base64.b64encode(buffer)
                
                # send to client address.
                if not self.client_addr is None:
                    buf_len = len(buffer)
                    if buf_len < self.BUFF_SIZE:
                        try:
                            self.sock.sendto(buffer, self.client_addr)
                        except Exception as send_err:
                            print(f"[WARN] Send error: {send_err}, skipping frame")
                    else:
                        print(f"Frame too long, skipping: {buf_len}")
                
                # Reset error counter on successful frame
                frame_errors = 0
                
            except MemoryError:
                frame_errors += 1
                print(f"[WARN] Memory error during capture (attempt {frame_errors})")
                # Force garbage collection
                import gc
                gc.collect()
                if frame_errors > 5:
                    print("[ERROR] Too many memory errors, waiting...")
                    time.sleep(1.0)
                    frame_errors = 0
                continue
            except Exception as e:
                frame_errors += 1
                print(f"[WARN] Frame capture error: {e} (attempt {frame_errors})")
                if frame_errors > 10:
                    print("[ERROR] Too many errors, stopping stream")
                    break
                time.sleep(0.1)  # Brief pause before retry
                continue
            
            # Control framerate
            time.sleep(1.0 / framerate)
        
        # Clean up
        picam2.stop()
        picam2.close()
        # =======================================================================

    # close the server.
    def close(self):
        self.exit = True
