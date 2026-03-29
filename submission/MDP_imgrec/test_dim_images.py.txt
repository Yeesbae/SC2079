"""
Test YOLO detection on artificially dimmed images
Simulates dark/low-light conditions without physical images
"""
import cv2
import numpy as np
import os
from ultralytics import YOLO

# ========== Configuration ==========
MODEL_PATH = "models/best.pt"  # Path to your model
TEST_IMAGE_DIR = "test_images"  # Put your test images here
OUTPUT_DIR = "dim_test_results"
# ===================================


def dim_image(img, factor):
    """
    Dim an image by a factor (0.0 = black, 1.0 = original)
    
    Args:
        img: Input image (BGR)
        factor: Dimming factor (0.1 = very dark, 0.5 = half brightness, 1.0 = original)
    
    Returns:
        Dimmed image
    """
    return np.clip(img * factor, 0, 255).astype(np.uint8)


def add_noise(img, noise_level=10):
    """Add noise to simulate low-light camera noise"""
    noise = np.random.normal(0, noise_level, img.shape).astype(np.int16)
    noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return noisy


def test_image_at_brightness_levels(model, img_path, output_dir):
    """
    Test detection at various brightness levels
    """
    img = cv2.imread(img_path)
    if img is None:
        print(f"Could not load: {img_path}")
        return
    
    filename = os.path.basename(img_path)
    name, ext = os.path.splitext(filename)
    
    # Test at different dimness levels
    brightness_levels = [1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
    
    print(f"\n{'='*60}")
    print(f"Testing: {filename}")
    print(f"{'='*60}")
    print(f"{'Brightness':<12} {'Detected':<15} {'Confidence':<12} {'Classes'}")
    print("-" * 60)
    
    for brightness in brightness_levels:
        # Dim the image
        dimmed = dim_image(img, brightness)
        
        # Add noise for more realistic simulation at low brightness
        if brightness < 0.5:
            noise_level = int((1 - brightness) * 20)  # More noise when darker
            dimmed = add_noise(dimmed, noise_level)
        
        # Run YOLO prediction
        results = model.predict(dimmed, verbose=False, conf=0.3)[0]
        
        # Get detection results
        num_detected = len(results.boxes)
        if num_detected > 0:
            classes = [results.names[int(box.cls[0])] for box in results.boxes]
            confs = [f"{box.conf[0]:.2f}" for box in results.boxes]
            detected_str = f"{num_detected} object(s)"
            conf_str = ", ".join(confs)
            class_str = ", ".join(classes)
        else:
            detected_str = "None"
            conf_str = "-"
            class_str = "-"
        
        print(f"{brightness:<12.1f} {detected_str:<15} {conf_str:<12} {class_str}")
        
        # Save annotated result
        annotated = results.plot()
        out_path = os.path.join(output_dir, f"{name}_brightness_{brightness:.1f}{ext}")
        cv2.imwrite(out_path, annotated)
    
    print()


def create_test_image_from_camera():
    """
    If no test images, capture from webcam
    """
    print("No test images found. Opening webcam to capture...")
    print("Press 's' to save image, 'q' to quit")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open webcam")
        return None
    
    saved_path = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow("Capture Test Image (s=save, q=quit)", frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('s'):
            os.makedirs(TEST_IMAGE_DIR, exist_ok=True)
            saved_path = os.path.join(TEST_IMAGE_DIR, "captured_test.jpg")
            cv2.imwrite(saved_path, frame)
            print(f"Saved: {saved_path}")
        elif key == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return saved_path


def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load model
    print(f"Loading model: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        print("Please update MODEL_PATH to point to your best.pt file")
        return
    
    model = YOLO(MODEL_PATH)
    print("Model loaded successfully!\n")
    
    # Check for test images
    if not os.path.exists(TEST_IMAGE_DIR):
        os.makedirs(TEST_IMAGE_DIR)
        print(f"Created {TEST_IMAGE_DIR}/ directory")
        print(f"Please put test images in {TEST_IMAGE_DIR}/ and run again")
        print("OR press Enter to capture from webcam...")
        
        input()
        img_path = create_test_image_from_camera()
        if img_path:
            test_image_at_brightness_levels(model, img_path, OUTPUT_DIR)
        return
    
    # Get all images in test directory
    test_images = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
        import glob
        test_images.extend(glob.glob(os.path.join(TEST_IMAGE_DIR, ext)))
        test_images.extend(glob.glob(os.path.join(TEST_IMAGE_DIR, ext.upper())))
    
    if not test_images:
        print(f"No images found in {TEST_IMAGE_DIR}/")
        print("Supported formats: jpg, jpeg, png, bmp")
        return
    
    print(f"Found {len(test_images)} test image(s)")
    
    # Test each image
    for img_path in test_images:
        test_image_at_brightness_levels(model, img_path, OUTPUT_DIR)
    
    print(f"\nResults saved to: {OUTPUT_DIR}/")
    print("Check the annotated images to see detection boxes at each brightness level")


if __name__ == "__main__":
    main()
