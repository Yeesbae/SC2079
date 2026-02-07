from ultralytics import YOLO
import os

# Change to the correct directory
os.chdir('/Users/I766692/project/yeesbae/SC2079/raspberry/Yukto S-C.v61i.yolov8')

# Load the trained model
model = YOLO('runs/detect/train/weights/best.pt')

print("Starting real-time detection...")
print("Press 'q' to quit")

# Run inference on webcam (source=0 for default camera)
results = model.predict(
    source=0,           # Webcam
    imgsz=416,
    device='mps',
    conf=0.25,
    show=True,          # Display results in a window
    stream=True         # Stream mode for real-time
)

# Process results
for result in results:
    pass  # The show=True parameter will display the video automatically
