from ultralytics import YOLO
import os

# Change to the correct directory
os.chdir('/Users/I766692/project/yeesbae/SC2079/raspberry/Yukto S-C.v61i.yolov8')

# Load the trained model
model = YOLO('runs/detect/train/weights/best.pt')

# Run inference on test images
results = model.predict(
    source='test/images/',
    imgsz=416,
    device='mps',
    save=True,
    conf=0.25
)

print(f"\n✅ Inference complete! Results saved to: runs/detect/predict/")
print(f"Processed {len(results)} images")
