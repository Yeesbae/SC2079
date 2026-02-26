# RPi Code Documentation

## File Structure

```
RPI_v1/
├── camera/              # Camera-related modules
│   ├── __init__.py
│   └── stream_server.py  # UDP video stream server (sends video to PC)
├── communication/        # Communication module
│   ├── __init__.py
│   └── pc.py             # TCP server (receives messages from PC)
├── config/               # Configuration module
│   ├── __init__.py
│   └── config.py         # Config class (model paths, parameters, etc.)
├── tasks/                # Task-related code
│   ├── __init__.py
│   ├── task1_rpi.py      # Task 1 main logic
│   └── task2_rpi.py      # Task 2 main logic
├── main.py               # Entry point
└── requirements.txt      # Python dependencies
```

## Environment Setup

### 1. Create a Virtual Environment (recommended)

```bash
# Enter project directory
cd RPI_v1

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2. Install System Dependencies (Debian Bookworm)

`picamera2` requires the system-installed `libcamera` Python bindings:

```bash
sudo apt update
sudo apt install python3-libcamera python3-picamera2
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If the virtual environment cannot find the `libcamera` module, add the system package path:

```bash
# Create a .pth file in the virtual environment's site-packages directory
echo "/usr/lib/python3/dist-packages" > venv/lib/python3.11/site-packages/system-packages.pth
```

### 4. Using the Virtual Environment

Activate the virtual environment before running the project each time:
```bash
source venv/bin/activate
```

To deactivate:
```bash
deactivate
```

## Running the Project

```bash
python main.py
```

Then follow the prompts:
1. Select task number (1 or 2)
2. Select indoor/outdoor (y/n)

## Feature Overview

### Task 1
- Starts UDP video stream server (port 5005)
- Starts TCP server (port 5000), waits for PC connection
- Receives detection results from PC: `"obstacle_id,confidence,image_id"`
- Receives commands from PC: `"DETECT,obstacle_id"` or `"PERFORM STITCHING,num"`

### Task 2
- Starts UDP video stream server (port 5005)
- Starts TCP server (port 5000), waits for PC connection
- Receives detection results from PC: `"confidence,image_id"`
- Receives commands from PC: `"SEEN"` or `"STITCH"`

## Notes

1. **Ensure RPi and PC are on the same network**
2. **Ensure firewall allows UDP port 5005 and TCP port 5000**
3. **Start the RPi side first, then the PC side**
4. **Task 1 and Task 2 share the same communication module; only the processing logic differs**
