"""
Test dim images from dataset against the trained model.
Simulates poor lighting conditions to evaluate model robustness.

Usage:
    python test_dim_dataset.py                          # Default: 50% brightness, 10 random images
    python test_dim_dataset.py --brightness 0.3         # 30% brightness (darker)
    python test_dim_dataset.py --brightness 0.7 --num 50  # 70% brightness, 50 images
    python test_dim_dataset.py --all                    # Test all validation images
"""

import os
import sys
import cv2
import numpy as np
import random
import argparse
from pathlib import Path
from ultralytics import YOLO

# Dataset path - relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRIPT_DIR, "dataset", "test5.v1i.yolov8")
VALID_IMAGES = os.path.join(DATASET_PATH, "valid", "images")
VALID_LABELS = os.path.join(DATASET_PATH, "valid", "labels")

# Model path
MODEL_PATH = "models/best.pt"

# Class names (11-41)
CLASS_NAMES = [str(i) for i in range(11, 42)]


def dim_image(img, brightness=0.5):
    """
    Reduce image brightness.
    
    Args:
        img: Input image (BGR)
        brightness: 0.0 = black, 1.0 = original brightness
    
    Returns:
        Dimmed image
    """
    return (img * brightness).astype(np.uint8)


def get_ground_truth(image_path):
    """
    Get ground truth labels for an image.
    
    Args:
        image_path: Path to the image
    
    Returns:
        List of class IDs from the label file
    """
    # Get corresponding label file
    label_path = image_path.replace("/images/", "/labels/").replace(".jpg", ".txt").replace(".png", ".txt")
    
    if not os.path.exists(label_path):
        return []
    
    classes = []
    with open(label_path, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if parts:
                class_idx = int(parts[0])
                if 0 <= class_idx < len(CLASS_NAMES):
                    classes.append(CLASS_NAMES[class_idx])
    
    return classes


def test_single_image(model, image_path, brightness=0.5, show=False, conf_threshold=0.5):
    """
    Test a single image at reduced brightness.
    
    Returns:
        dict with results
    """
    # Load image
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    # Get ground truth
    gt_classes = get_ground_truth(image_path)
    
    # Dim the image
    dim_img = dim_image(img, brightness)
    
    # Run inference
    results = model(dim_img, verbose=False, conf=conf_threshold)
    
    # Get detections
    detections = []
    for r in results:
        for box in r.boxes:
            cls_idx = int(box.cls[0])
            conf = float(box.conf[0])
            if cls_idx < len(CLASS_NAMES):
                detections.append({
                    'class': CLASS_NAMES[cls_idx],
                    'confidence': conf
                })
    
    # Check if detection matches ground truth
    detected_classes = [d['class'] for d in detections]
    correct = any(d in gt_classes for d in detected_classes) if gt_classes else len(detections) == 0
    
    result = {
        'image': os.path.basename(image_path),
        'brightness': brightness,
        'ground_truth': gt_classes,
        'detections': detections,
        'detected_classes': detected_classes,
        'correct': correct
    }
    
    if show:
        # Show side by side
        combined = np.hstack([img, dim_img])
        
        # Add text
        cv2.putText(combined, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(combined, f"Dimmed ({brightness*100:.0f}%)", (img.shape[1] + 10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Show ground truth and detection
        gt_text = f"GT: {gt_classes}" if gt_classes else "GT: None"
        det_text = f"Det: {detected_classes}" if detected_classes else "Det: None"
        cv2.putText(combined, gt_text, (10, img.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(combined, det_text, (10, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.imshow("Dim Test", combined)
        key = cv2.waitKey(0)
        if key == ord('q'):
            return None  # Signal to quit
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Test dim images against YOLO model")
    parser.add_argument("--brightness", type=float, default=0.5,
                        help="Brightness level (0.0-1.0, default: 0.5)")
    parser.add_argument("--num", type=int, default=10,
                        help="Number of random images to test (default: 10)")
    parser.add_argument("--all", action="store_true",
                        help="Test all validation images")
    parser.add_argument("--show", action="store_true",
                        help="Show each image (press any key to continue, 'q' to quit)")
    parser.add_argument("--conf", type=float, default=0.5,
                        help="Confidence threshold (default: 0.5)")
    parser.add_argument("--model", type=str, default=MODEL_PATH,
                        help="Path to model (default: models/best.pt)")
    parser.add_argument("--sweep", action="store_true",
                        help="Test multiple brightness levels (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)")
    args = parser.parse_args()
    
    # Check paths
    if not os.path.exists(VALID_IMAGES):
        print(f"Error: Dataset not found at {VALID_IMAGES}")
        print("Make sure test5.v1i.yolov8 is on your Desktop")
        sys.exit(1)
    
    if not os.path.exists(args.model):
        print(f"Error: Model not found at {args.model}")
        sys.exit(1)
    
    # Load model
    print(f"Loading model: {args.model}")
    model = YOLO(args.model)
    
    # Get image list
    all_images = [os.path.join(VALID_IMAGES, f) for f in os.listdir(VALID_IMAGES) 
                  if f.endswith(('.jpg', '.png', '.jpeg'))]
    
    if not all_images:
        print("No images found in validation set")
        sys.exit(1)
    
    print(f"Found {len(all_images)} validation images")
    
    # Select images to test
    if args.all:
        test_images = all_images
    else:
        test_images = random.sample(all_images, min(args.num, len(all_images)))
    
    print(f"Testing {len(test_images)} images")
    
    if args.sweep:
        # Test multiple brightness levels
        brightness_levels = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
        print(f"\n{'='*70}")
        print("BRIGHTNESS SWEEP TEST")
        print(f"{'='*70}")
        
        for brightness in brightness_levels:
            correct = 0
            total = 0
            detected = 0
            
            for img_path in test_images:
                result = test_single_image(model, img_path, brightness, show=False, conf_threshold=args.conf)
                if result:
                    total += 1
                    if result['correct']:
                        correct += 1
                    if result['detections']:
                        detected += 1
            
            accuracy = (correct / total * 100) if total > 0 else 0
            detection_rate = (detected / total * 100) if total > 0 else 0
            print(f"Brightness {brightness*100:3.0f}%: Accuracy={accuracy:5.1f}%, DetectionRate={detection_rate:5.1f}% ({detected}/{total})")
    else:
        # Test single brightness level
        print(f"\n{'='*70}")
        print(f"TESTING AT {args.brightness*100:.0f}% BRIGHTNESS (conf={args.conf})")
        print(f"{'='*70}\n")
        
        correct = 0
        total = 0
        results = []
        
        for i, img_path in enumerate(test_images):
            result = test_single_image(model, img_path, args.brightness, show=args.show, conf_threshold=args.conf)
            
            if result is None and args.show:
                print("\nQuitting...")
                break
            
            if result:
                results.append(result)
                total += 1
                if result['correct']:
                    correct += 1
                
                # Print result
                status = "✓" if result['correct'] else "✗"
                gt = result['ground_truth'][0] if result['ground_truth'] else "?"
                det = result['detected_classes'][0] if result['detected_classes'] else "None"
                conf = result['detections'][0]['confidence'] if result['detections'] else 0
                
                print(f"[{i+1:3d}/{len(test_images)}] {status} GT={gt:>2s} Det={det:>4s} Conf={conf:.2f} - {result['image']}")
        
        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Brightness: {args.brightness*100:.0f}%")
        print(f"Confidence threshold: {args.conf}")
        print(f"Total tested: {total}")
        print(f"Correct: {correct}")
        print(f"Accuracy: {correct/total*100:.1f}%" if total > 0 else "N/A")
        
        # Show misses
        misses = [r for r in results if not r['correct']]
        if misses:
            print(f"\nMissed detections ({len(misses)}):")
            for m in misses[:10]:  # Show first 10
                print(f"  {m['image']}: GT={m['ground_truth']} Det={m['detected_classes']}")
    
    if args.show:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
