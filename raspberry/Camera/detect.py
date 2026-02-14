"""
Single Detection Script for SC2079
Works on both Mac (dev) and Raspberry Pi (production)
"""

from ultralytics import YOLO
import cv2
import time
import platform

# ===== CONFIGURATION =====
MODEL_PATH = 'V5.pt'  # Model file in same directory
IMAGE_SIZE = 416
CONFIDENCE = 0.5

# Class names for SC2079_V4 dataset
CLASS_NAMES = {
    0: '1', 1: '2', 2: '3', 3: '4', 4: '5', 5: '6', 6: '7', 7: '8', 8: '9',
    9: 'A', 10: 'B', 11: 'Bullseye', 12: 'C', 13: 'D', 14: 'Down',
    15: 'E', 16: 'F', 17: 'G', 18: 'H', 19: 'Left', 20: 'Right',
    21: 'S', 22: 'Stop', 23: 'T', 24: 'U', 25: 'Up', 26: 'V',
    27: 'W', 28: 'X', 29: 'Y', 30: 'Z'
}

def get_device():
    """Get best device for current platform."""
    if platform.system() == 'Darwin':  # macOS
        return 'mps'
    return 'cpu'  # Raspberry Pi

def get_camera():
    """Initialize camera - tries picamera2 first, then OpenCV."""
    try:
        from picamera2 import Picamera2
        cam = Picamera2()
        config = cam.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        cam.configure(config)
        cam.start()
        print("[Camera] Using picamera2")
        return cam, 'picamera'
    except:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if cap.isOpened():
            print("[Camera] Using OpenCV webcam")
            return cap, 'opencv'
        return None, None

def main():
    print("=" * 50)
    print("SC2079 Detection")
    print("=" * 50)
    
    # Load model
    device = get_device()
    print(f"[Model] Loading {MODEL_PATH} on {device}...")
    model = YOLO(MODEL_PATH)
    print("[Model] Ready!")
    
    # Initialize camera
    camera, cam_type = get_camera()
    if camera is None:
        print("[Error] No camera found!")
        return
    
    print(f"[Config] Size: {IMAGE_SIZE}, Confidence: {CONFIDENCE}")
    print("Press 'q' to quit")
    print("=" * 50)
    
    # FPS tracking
    fps = 0
    frame_count = 0
    fps_time = time.time()
    
    try:
        while True:
            # Capture frame
            if cam_type == 'picamera':
                frame = camera.capture_array()
            else:
                ret, frame = camera.read()
                if not ret:
                    continue
            
            # Run detection
            results = model.predict(
                source=frame,
                imgsz=IMAGE_SIZE,
                conf=CONFIDENCE,
                device=device,
                verbose=False
            )
            
            # Draw results
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = CLASS_NAMES.get(cls, str(cls))
                    
                    # Draw box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw label
                    text = f'{label} {conf:.2f}'
                    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1-25), (x1+w, y1), (0, 255, 0), -1)
                    cv2.putText(frame, text, (x1, y1-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # Calculate FPS
            frame_count += 1
            if frame_count % 30 == 0:
                fps = 30 / (time.time() - fps_time)
                fps_time = time.time()
            
            cv2.putText(frame, f'FPS: {fps:.1f}', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Show
            cv2.imshow('SC2079 Detection', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if cam_type == 'picamera':
            camera.stop()
        else:
            camera.release()
        cv2.destroyAllWindows()
        print("Done.")

if __name__ == "__main__":
    main()
