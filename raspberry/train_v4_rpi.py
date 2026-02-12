"""
YOLOv8 Training Script for SC2079_V4 Dataset
Optimized for Raspberry Pi 4 Model B with Camera Module 2.1

This script trains YOLOv8n (nano) model for best performance on RPi4.
Camera Module 2.1 supports 3280x2464 (8MP) but we use smaller input for speed.
"""

from ultralytics import YOLO
import os
import torch

# Configuration
DATASET_PATH = '/Users/I766692/project/yeesbae/SC2079/raspberry/Datasets/SC2079_V4'
DATA_YAML = os.path.join(DATASET_PATH, 'data.yaml')

# Training parameters optimized for RPi4 deployment
TRAINING_CONFIG = {
    'data': DATA_YAML,
    'epochs': 100,                    # Train for 100 epochs
    'imgsz': 416,                     # Image size - good balance for RPi4
    'batch': 16,                      # Adjust based on your GPU memory
    'patience': 20,                   # Early stopping patience
    'device': 'mps',                  # Use 'mps' for Apple Silicon, 'cuda' for NVIDIA, '0' for GPU
    'workers': 8,                     # Data loader workers
    'project': os.path.join(DATASET_PATH, 'runs/detect'),
    'name': 'train_v4_rpi',
    'exist_ok': True,
    
    # Optimization settings
    'optimizer': 'AdamW',             # Optimizer
    'lr0': 0.001,                     # Initial learning rate
    'lrf': 0.01,                      # Final learning rate factor
    'momentum': 0.937,                # SGD momentum/Adam beta1
    'weight_decay': 0.0005,           # Weight decay
    
    # Augmentation settings
    'hsv_h': 0.015,                   # HSV-Hue augmentation
    'hsv_s': 0.7,                     # HSV-Saturation augmentation
    'hsv_v': 0.4,                     # HSV-Value augmentation
    'degrees': 10.0,                  # Rotation augmentation
    'translate': 0.1,                 # Translation augmentation
    'scale': 0.5,                     # Scale augmentation
    'shear': 2.0,                     # Shear augmentation
    'flipud': 0.0,                    # Vertical flip (disabled - text orientation matters)
    'fliplr': 0.5,                    # Horizontal flip
    'mosaic': 1.0,                    # Mosaic augmentation
    'mixup': 0.1,                     # Mixup augmentation
    
    # Other settings
    'verbose': True,
    'seed': 42,
    'amp': True,                      # Automatic Mixed Precision
    'cache': True,                    # Cache images for faster training
}

def main():
    print("=" * 60)
    print("YOLOv8n Training for Raspberry Pi 4 + Camera Module 2.1")
    print("=" * 60)
    
    # Check device
    if torch.backends.mps.is_available():
        device = 'mps'
        print("Using Apple Silicon MPS for training")
    elif torch.cuda.is_available():
        device = 'cuda'
        print(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = 'cpu'
        print("Using CPU for training (this will be slow)")
    
    TRAINING_CONFIG['device'] = device
    
    # Check for existing checkpoint to resume training
    last_checkpoint = os.path.join(DATASET_PATH, 'runs/detect/train_v4_rpi/weights/last.pt')
    
    if os.path.exists(last_checkpoint):
        print(f"\nFound existing checkpoint: {last_checkpoint}")
        print("Resuming training from last checkpoint...")
        model = YOLO(last_checkpoint)
        TRAINING_CONFIG['resume'] = True
    else:
        # Load YOLOv8n (nano) - best for Raspberry Pi
        print("\nLoading YOLOv8n model (optimized for edge devices)...")
        model = YOLO('yolov8n.pt')
    
    # Display dataset info
    print(f"\nDataset: {DATASET_PATH}")
    print("Classes: 31 (Numbers 1-9, Letters A-Z, Arrows, Bullseye, Stop)")
    print(f"Image size: {TRAINING_CONFIG['imgsz']}x{TRAINING_CONFIG['imgsz']}")
    print(f"Epochs: {TRAINING_CONFIG['epochs']}")
    print(f"Batch size: {TRAINING_CONFIG['batch']}")
    
    # Start training
    print("\n" + "=" * 60)
    print("Starting Training...")
    print("=" * 60 + "\n")
    
    results = model.train(**TRAINING_CONFIG)
    
    # Training complete
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    
    # Show best model path
    best_model_path = os.path.join(DATASET_PATH, 'runs/detect/train_v4_rpi/weights/best.pt')
    print(f"\nBest model saved to: {best_model_path}")
    
    # Validate the model
    print("\nRunning validation on the best model...")
    best_model = YOLO(best_model_path)
    val_results = best_model.val(
        data=DATA_YAML,
        imgsz=416,
        batch=16,
        device=device
    )
    
    print("\n" + "=" * 60)
    print("Model Export for Raspberry Pi 4")
    print("=" * 60)
    
    # Export to NCNN format (recommended for Raspberry Pi 4)
    print("\nExporting to NCNN format (best for RPi4)...")
    try:
        ncnn_model = best_model.export(
            format='ncnn',
            imgsz=416,
            half=False,  # RPi4 doesn't support FP16 well
            simplify=True
        )
        print(f"NCNN model exported successfully!")
    except Exception as e:
        print(f"NCNN export failed: {e}")
        print("You can manually export later with: model.export(format='ncnn')")
    
    # Also export to ONNX as backup
    print("\nExporting to ONNX format...")
    try:
        onnx_model = best_model.export(
            format='onnx',
            imgsz=416,
            simplify=True,
            opset=12
        )
        print(f"ONNX model exported successfully!")
    except Exception as e:
        print(f"ONNX export failed: {e}")
    
    print("\n" + "=" * 60)
    print("TRAINING SUMMARY")
    print("=" * 60)
    print(f"Best model: {best_model_path}")
    print(f"Input size: 416x416")
    print(f"Target device: Raspberry Pi 4 Model B")
    print(f"Camera: Camera Module 2.1 (8MP)")
    print("\nFor deployment on Raspberry Pi 4:")
    print("1. Copy the NCNN model files to your RPi4")
    print("2. Install ultralytics and opencv-python")
    print("3. Use picamera2 for camera capture")
    print("4. Run inference at 416x416 resolution for best speed")
    print("=" * 60)

if __name__ == "__main__":
    main()
