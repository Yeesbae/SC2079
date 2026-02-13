# Message Protocol
## ANDROID → RPI
### A) Start Exploration
1. Trigger exploration
```
S,E\n
```
Immediately signals RPI to:
- Prepare to receive configuration
- Enter exploration mode

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

## Message Prefix Summary
|   Prefix  |   Meaning |
|---|---|
|   S	|   Start command   |
|   R	|   Robot configuration  |
|   O	|   Obstacle configuration  |
|   P   |   Robot position update   |
|   T	|   Target detection    |
|   M	|   Status message  |
|   f/r/tl/tr	|   Manual movement |