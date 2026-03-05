# Message Protocol
## ANDROID → RPI
### A) Start Exploration

Android sends the entire arena configuration in one JSON message.

Example:
```json
{
  "cmd": "START_EXPLORE",
  "grid_size": {
    "x": 40,
    "y": 40
  },
  "robot": {
    "x": 1,
    "y": 2,
    "d": 0
  },
  "obstacles": [
    {
      "id": 1,
      "x": 27,
      "y": 30,
      "width": 2,
      "length": 2,
      "d": 4
    },
    {
      "id": 2,
      "x": 27,
      "y": 4,
      "width": 2,
      "length": 2,
      "d": 2
    }
  ]
}
```

Fields:

| Field | Meaning |
|---|---|
| cmd | Command type |
| grid_size | Arena size |
| robot | Initial robot position |
| obstacles | List of obstacle rectangles |

Robot:

| Field | Meaning |
|---|---|
| x | robot x coordinate |
| y | robot y coordinate |
| d | direction |

Direction mapping:

| Value | Direction |
|---|---|
| 0 | North | 
| 2	| East |
| 4 | South |
| 6 | West |

Obstacles:

| Field | Meaning |
|---|---|
| id | obstacle id |
| x | bottom-left x |
| y | bottom-left y |
| width | width in cells |
| length | height in cells |
| d | face direction |

### B) Start Fastest Path

Android sends a simple JSON command:
```json
{
  "cmd": "START_FASTEST"
}
```
### C) Manual D-Pad Commands

The D-Pad sends STM32 movement commands.

Format:

- [CMD][DIR][MAG]

Examples:

```
SF005\n   -> move forward 5cm
SB005\n   -> move backward 5cm
RF090\n   -> turn right 90°
LF090\n   -> turn left 90°
```

Where:

| Part | Meaning |
|---|---|
| S | Straight |
| R	| Right turn |
| L | Left turn |
| F | Forward |
| B | Backward |
| MAG | magnitude |

Current configuration:

| Action | Command |
|---|---|
| Forward | SF005 |
| Backward | SB005 |
| Turn Right | RF090 |
| Turn Left | LF090 |

## RPI → ANDROID
### A) Planned Path Return

RPi returns the entire planned path as a JSON list.

Example:

```
[
  {"x":1,"y":1,"d":0,"s":0},
  {"x":2,"y":1,"d":0,"s":0},
  {"x":3,"y":1,"d":2,"s":0},
  {"x":3,"y":2,"d":2,"s":1}
]
```

Fields

| Field | Meaning |
|---|---|
| x | robot x coordinate |
| y | robot y coordinate |
| d	| robot direction |
| s | obstacle id detected at that position

s meaning:

| Value | Meaning |
|---|---|
| -1	no | obstacle detectionm | 
1..N	| pobstacle id to scan |

Example:
"s": 3

means the robot should scan obstacle B3 at that pose.

### B) Robot Position Update

RPi may send incremental updates:
```
P,x,y,face
```
Example:

P,4,6,E

### C) Image Detection

When an obstacle image is detected:
```
TARGET,B2,11
```
Meaning:

Field	Meaning
B2	obstacle ID
11	detected image ID

### D) Image Transfer

Image is transferred as Base64.
```
IMG,B2,11,<base64>
```
Example:

IMG,B2,11,/9j/4AAQSkZJRgABAQE...

Android decodes the Base64 payload into JPEG.

## Protocol Summary
| Direction | Message |
|---|---|
| Android → RPi | START_EXPLORE JSON |
| Android → RPi | START_FASTEST JSON |
| Android → RPi	| DPad movement commands |
| RPi → Android	| Path coordinate list |
| RPi → Android	| Position updates |
| RPi → Android	| arget detection |
| RPi → Android	| Image transfer |

Important Notes
- Messages are newline terminated: \n
- Images must be sent as one Base64 line
IMG,B2,11,<base64>\n
- Path return must be valid JSON

Android parses the path using JSON deserialization.