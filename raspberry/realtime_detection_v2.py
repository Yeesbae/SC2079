from ultralytics import YOLO
import os

# Change to the correct directory
os.chdir('/Users/I766692/project/yeesbae/SC2079/raspberry/Datasets/SC2079.v2i.yolov8')

# Load the newly trained model (with numbers 1-9, letters A-Z, symbols)
model = YOLO('runs/detect/train/weights/best.pt')

print("Starting real-time detection with new model...")
print("Model detects: Numbers 1-9, Letters A-Z, Arrows, Bulls Eye, Stop")
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
