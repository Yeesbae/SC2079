# Message Protocol
## ANDROID → RPI
### A) Start Exploration
1. Trigger exploration
```
S,E\n
```
Meaning:
- RPi enters "planned exploration config" mode
- RPi should prepare to receive the arena configuration next (R + O...)
- RPi should NOT start moving yet until it has received configuration and computed the planned route

2. Robot Rectangle
```
R,blX,blY,w,h,face\n
```
Where:
- blX, blY = bottom-left coords
- w,h = footprint size (cells)
- face = direction

Example: R,0,0,3,3,N

3. Obstacle rectangles (repeat per obstacle)
```
O,id,blX,blY,w,h,face\n
```
Example:

- O,B1,2,3,2,2,N
- O,B2,6,5,2,2,E

Notes:
- All messages are newline-delimited (\n).
- <face> is one of: N, E, S, W

### B) Start Fastest Path
```
S,F\n
```

### C) Manual D-Pad Controls
Minimal payload:
```
f\n
r\n
tl\n
tr\n
```

## RPI -> Android
### A) Robot Position Update
```
P,x,y,face\n
```
Example: P,4,6,E

### B) Image Detection + Binary Image Transfer
```
T,B2,11,N,J,10240\n
<10240 raw bytes>
```
Where:
- J is JPEG

### C) Status Message
```
M,message\n
```
Example:
- M,Exploring
- M,TargetFound
- M,Completed

### D) Planned path sequence
RPi returns the full planned route as a stream of pose lines, framed by PATH_BEGIN / PATH_END:
```
PATH_BEGIN,<count>
P,<x>,<y>,<face>
P,<x>,<y>,<face>
...
PATH_END
```
Where:
- count is the number of P lines that follow (optional for validation).
- P lines represent the robot pose sequence (grid coordinates + facing).

## Message Prefix Summary
|   Prefix  |   Meaning |
|---|---|
|   S	|   Start command   |
|   R	|   Robot configuration  |
|   O	|   Obstacle configuration  |
|   P   |   Robot position update   |
|   T	|   Target detection    |
|   M	|   Status message  |
| PATH_BEGIN / PATH_END | Planned path framing |
|   f/r/tl/tr	|   Manual movement |