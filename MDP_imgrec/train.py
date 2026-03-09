"""
YOLOv8 Training Script for MDP Image Recognition
Run on Windows PC with NVIDIA GPU

Usage:
    python train.py --data <path_to_data.yaml>

Example:
    python train.py --data C:/Users/YourName/Desktop/dataset/data.yaml
    python train.py --data C:/Users/YourName/Desktop/dataset/data.yaml --model yolov8m.pt --epochs 150
"""

import argparse
from ultralytics import YOLO


def train(args):
    # Load base model (pretrained on COCO)
    model = YOLO(args.model)

    # Train
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=640,
        batch=args.batch,
        name=args.name,
        pretrained=True,
        optimizer="auto",
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        warmup_momentum=0.8,
        # Augmentations - tuned for obstacle symbol detection
        degrees=15.0,       # rotation ±15°
        translate=0.1,
        scale=0.5,
        shear=10.0,          # shear to simulate perspective
        flipud=0.0,          # NO vertical flip (symbols have orientation)
        fliplr=0.0,          # NO horizontal flip (arrows, digits are directional)
        mosaic=1.0,
        mixup=0.0,
        erasing=0.4,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        # Training settings
        patience=50,         # early stopping patience
        workers=4,
        device=args.device,
        amp=True,            # mixed precision for faster training
        close_mosaic=10,     # disable mosaic for last 10 epochs
        deterministic=True,
        verbose=True,
        plots=True,
    )

    print("\n========== Training Complete ==========")
    print(f"Best model saved to: runs/detect/{args.name}/weights/best.pt")
    print(f"Last model saved to: runs/detect/{args.name}/weights/last.pt")
    return results


def validate(args):
    """Run validation on the best model"""
    best_path = f"runs/detect/{args.name}/weights/best.pt"
    model = YOLO(best_path)

    # Validate at different confidence thresholds
    for conf in [0.5, 0.6, 0.65, 0.7]:
        print(f"\n--- Validation @ conf={conf} ---")
        model.val(data=args.data, conf=conf, imgsz=640, device=args.device)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLOv8 for MDP image recognition")
    parser.add_argument("--data", type=str, required=True,
                        help="Path to data.yaml (from Roboflow download)")
    parser.add_argument("--model", type=str, default="yolov8s.pt",
                        help="Base model: yolov8n.pt, yolov8s.pt, yolov8m.pt (default: yolov8s.pt)")
    parser.add_argument("--epochs", type=int, default=100,
                        help="Number of training epochs (default: 100)")
    parser.add_argument("--batch", type=int, default=16,
                        help="Batch size, use -1 for auto (default: 16)")
    parser.add_argument("--device", type=str, default="0",
                        help="Device: '0' for GPU, 'cpu' for CPU (default: '0')")
    parser.add_argument("--name", type=str, default="mdp_digits_v2",
                        help="Run name for saving results (default: mdp_digits_v2)")
    parser.add_argument("--val-only", action="store_true",
                        help="Only run validation on existing best.pt")

    args = parser.parse_args()

    if args.val_only:
        validate(args)
    else:
        train(args)
        print("\nRunning validation on best model...")
        validate(args)
