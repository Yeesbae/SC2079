# PC-Side Code Documentation

## File Structure

```
MDP_imgrec/
├── camera/                  # Camera-related modules
│   ├── __init__.py
│   └── stream_listener.py   # UDP video stream client + YOLO recognition
├── communication/           # Communication module
│   ├── __init__.py
│   └── pc_client.py         # TCP client (sends messages to RPi)
├── config/                  # Configuration module
│   ├── __init__.py
│   └── config.py            # Config class (model paths, parameters, etc.)
├── stitching/               # Image stitching module
│   ├── __init__.py
│   └── stitching.py        # Stitching functions
├── tasks/                   # Task-related code
│   ├── __init__.py
│   ├── task1_pc.py         # Task 1 recognition logic
│   └── task2_pc.py         # Task 2 recognition logic
├── main.py                  # Entry point
└── requirements.txt         # Python dependencies
```

## Configuration (What to Modify)

### 1. IP Address Configuration

**File: `camera/stream_listener.py`**
```python
# Line 15
self.HOST_ADDR = ("192.168.14.14", 5005)  # Change to your RPi IP address
```

**File: `communication/pc_client.py`**
```python
# Line 20 (default parameter)
def __init__(self, host="192.168.14.14", port=5000):  # Change to your RPi IP address
```

**File: `tasks/task1_pc.py`**
```python
# Line 30
self.host = "192.168.14.14"  # Change to your RPi IP address
```

**File: `tasks/task2_pc.py`**
```python
# Line 30
self.host = "192.168.14.14"  # Change to your RPi IP address
```

### 2. Model File Paths

**File: `config/config.py`**
```python
# Lines 14 and 20
Config.__init__(self, 'v12_task1.pt', 'v9_task2.pt')  # Change to your model file paths
```

Ensure model files are accessible from the PC.

### 3. Task1-Specific Configuration

**File: `tasks/task1_pc.py`**
```python
# Line 35 - Blacklist (image IDs to skip during recognition)
self.IMG_BLACKLIST = ["marker"]  # Modify as needed

# Lines 38-39 - Time matching parameters
self.time_advance_ns = 0.75e9    # Adjust as needed
self.time_threshold_ns = 1.5e9

# Line 45 - Stitching output file prefix
self.filename = "task1"  # Modify as needed
```

### 4. Task2-Specific Configuration

**File: `tasks/task2_pc.py`**
```python
# Lines 40-41 - Left/right arrow IDs (adjust according to your model)
self.LEFT_ARROW_ID = "39"
self.RIGHT_ARROW_ID = "38"

# Line 35 - Stitching output file prefix
self.filename = "task2"  # Modify as needed

# Line 50 - Confidence threshold
conf_threshold=0.65  # Adjust as needed
```

## Installing Dependencies

```bash
pip install -r requirements.txt
```

**Note:** Installing `torch` and `torchvision` may take a while; consider using a GPU-enabled PyTorch build for faster inference.

## How to Run

```bash
python main.py
```

Then follow the prompts:
1. Select task number (1 or 2, must match RPi side)
2. Select indoor/outdoor (y/n, must match RPi side)

## Video Display

When the program runs, it automatically opens a video window that shows:
- **Received video frames**: Real-time video stream from RPi
- **Recognition overlay**: YOLO detection boxes, labels, and confidence scores on the video

### Usage
- **View video and recognition results**: A window named "Stream" opens after startup
- **Close video window**: With the video window focused, press `q` to quit (disconnects the stream)

### Disable Video Display
To hide the video window (e.g. to save resources), edit these files:

**File: `tasks/task1_pc.py`**
```python
# Line 68
show_video=False  # Set to False to disable video display
```

**File: `tasks/task2_pc.py`**
```python
# Line 65
show_video=False  # Set to False to disable video display
```

## Feature Overview

### Task 1
- Connect to RPi UDP video stream (port 5005)
- Real-time image recognition with YOLO
- Send recognition results to RPi: `"obstacle_id,confidence,image_id"`
- Receive commands from RPi:
  - `"DETECT,obstacle_id"` - Match image for specified obstacle
  - `"PERFORM STITCHING,num"` - Stitch num images

### Task 2
- Connect to RPi UDP video stream (port 5005)
- Real-time image recognition with YOLO (left/right arrows only)
- Send recognition results to RPi: `"confidence,image_id"`
- Receive commands from RPi:
  - `"SEEN"` - Arrow seen, ready for next
  - `"STITCH"` - Stitch images

## Notes

1. **PC and RPi must be on the same network**
2. **Allow UDP 5005 and TCP 5000 in firewall**
3. **Start RPi side first, then PC side**
4. **Task1 and Task2 must use the same task number and indoor/outdoor setting**
5. **Model file paths must be correct and accessible from PC**
6. **For GPU use, ensure CUDA is installed correctly**
7. **macOS video display**: On macOS, if the video window fails to show (OpenCV error), the program continues without it. Recognition still works. This is a known OpenCV GUI limitation on macOS.

## Output Files

Stitched images are saved in the current directory with filenames:
- Task1: `task1_collage_HHMMSS.jpg`
- Task2: `task2_collage_HHMMSS.jpg`
