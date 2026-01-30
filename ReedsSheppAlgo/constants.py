"""
constants.py

Single source of truth for all physical, geometric, and planning parameters.
All units are in centimeters (cm) and radians unless stated otherwise.

Coordinate convention:
- (x, y) refers to the BOTTOM-LEFT corner of an object
- Robot pose (x, y, θ):
    (x, y) = bottom-left corner of robot bounding box
    θ      = robot forward direction (camera faces forward)
"""

# =========================
# ARENA / ENVIRONMENT
# =========================

ARENA_WIDTH = 200.0
ARENA_HEIGHT = 200.0

# Safety margin from arena boundary (after inflation)
ARENA_MARGIN = 2.0


# =========================
# ROBOT GEOMETRY
# =========================

# Robot body dimensions
ROBOT_LENGTH = 21.0      # front to back
ROBOT_WIDTH = 20.0       # left to right

# Reference frame:
# Pose (x, y) is the bottom-left corner of the robot
# Heading θ points along +forward direction

# Distance from bottom-left corner to robot center
ROBOT_CENTER_OFFSET_X = ROBOT_LENGTH / 2.0
ROBOT_CENTER_OFFSET_Y = ROBOT_WIDTH / 2.0

# Camera properties
CAMERA_OFFSET_FROM_FRONT = 0.0   # camera mounted at front face
CAMERA_CAPTURE_DISTANCE = 20.0   # required distance from image plane

# Turning constraints
MIN_TURNING_RADIUS = 25.0        # Reeds–Shepp turning radius

# Approximate robot footprint radius (used for inflation)
# Half-diagonal of robot rectangle
ROBOT_FOOTPRINT_RADIUS = ((ROBOT_LENGTH ** 2 + ROBOT_WIDTH ** 2) ** 0.5) / 2.0


# =========================
# OBSTACLES
# =========================

# Default obstacle dimensions (Task 1: square obstacles)
DEFAULT_OBSTACLE_WIDTH = 10.0
DEFAULT_OBSTACLE_HEIGHT = 10.0

# Obstacles may be rectangular in Task 2
# (actual width/height supplied per obstacle)

# Inflation margins
OBSTACLE_INFLATION_MARGIN = 5.0  # tuning knob for safety

# Total inflation applied to obstacles for collision checking
TOTAL_OBSTACLE_INFLATION = (
    ROBOT_FOOTPRINT_RADIUS
    + CAMERA_CAPTURE_DISTANCE
    + OBSTACLE_INFLATION_MARGIN
)


# =========================
# WALLS (TASK 2)
# =========================

# Walls are treated as obstacles with large rectangles
WALL_THICKNESS = 5.0

# Extra margin to prevent scraping along walls
WALL_INFLATION_MARGIN = 5.0


# =========================
# REEDS–SHEPP PLANNING
# =========================

# Sampling resolution along RS curves
RS_PATH_SAMPLE_STEP = 2.0     # cm per sample

# Angle normalization tolerance
ANGLE_EPSILON = 1e-6

# Penalty factors (optional, can be tuned)
REVERSE_MOTION_PENALTY = 1.2   # discourage reversing slightly
GEAR_SWITCH_PENALTY = 5.0      # discourage frequent gear changes


# =========================
# VIEWPOINT GENERATION
# =========================

# How far to offset viewpoints from obstacle faces
VIEWPOINT_DISTANCE = CAMERA_CAPTURE_DISTANCE

# Allowable angular tolerance when facing image (radians)
VIEWPOINT_ANGLE_TOLERANCE = 0.15


# =========================
# GRAPH / TSP SOLVER
# =========================

# Large cost used to invalidate impossible edges
INFINITE_COST = 1e9

# Maximum number of viewpoints per obstacle
MAX_VIEWPOINTS_PER_OBSTACLE = 4

# Enable pruning of unreachable viewpoints
PRUNE_INVALID_VIEWPOINTS = True


# =========================
# NUMERICAL / DEBUG
# =========================

# Small epsilon for geometric comparisons
EPSILON = 1e-6

# Enable verbose logging / debugging
DEBUG_MODE = False
