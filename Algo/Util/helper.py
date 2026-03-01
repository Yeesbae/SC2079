from constants import ARENA_WIDTH, ARENA_HEIGHT, Direction
import random
import math

def is_valid(center_x: int, center_y: int):
    """Checks if given position is within bounds

    Inputs
    ------
    center_x (int): x-coordinate
    center_y (int): y-coordinate

    Returns
    -------
    bool: True if valid, False otherwise
    """
    return center_x > 0 and center_y > 0 and center_x < ARENA_WIDTH - 1 and center_y < ARENA_HEIGHT - 1


def command_generator(states, obstacles):
    """
    This function takes in a list of states and generates a list of commands for the robot to follow
    
    Inputs
    ------
    states: list of State objects
    obstacles: list of obstacles, each obstacle is a dictionary with keys "x", "y", "d", and "id"

    Returns
    -------
    commands: list of commands for the robot to follow
    """

    # Convert the list of obstacles into a dictionary with key as the obstacle id and value as the obstacle
    obstacles_dict = {ob['id']: ob for ob in obstacles}
    
    # Initialize commands list
    commands = []

    # Iterate through each state in the list of states
    for i in range(1, len(states)):
        steps = "00"

        # If previous state and current state are the same direction,
        if states[i].direction == states[i - 1].direction:
            # Forward - Must be (east facing AND x value increased) OR (north facing AND y value increased)
            if (states[i].x > states[i - 1].x and states[i].direction == Direction.EAST) or (states[i].y > states[i - 1].y and states[i].direction == Direction.NORTH):
                commands.append("FW10")
            # Forward - Must be (west facing AND x value decreased) OR (south facing AND y value decreased)
            elif (states[i].x < states[i-1].x and states[i].direction == Direction.WEST) or (
                    states[i].y < states[i-1].y and states[i].direction == Direction.SOUTH):
                commands.append("FW10")
            # Backward - All other cases where the previous and current state is the same direction
            else:
                commands.append("BW10")

            # If any of these states has a valid screenshot ID, then add a SNAP command as well to take a picture
            if states[i].screenshot_id != -1:
                # NORTH = 0
                # EAST = 2
                # SOUTH = 4
                # WEST = 6

                current_ob_dict = obstacles_dict[states[i].screenshot_id] # {'x': 9, 'y': 10, 'd': 6, 'id': 9}
                current_robot_position = states[i] # {'x': 1, 'y': 8, 'd': <Direction.NORTH: 0>, 's': -1}

                # Obstacle facing WEST, robot facing EAST
                if current_ob_dict['d'] == 6 and current_robot_position.direction == 2:
                    if current_ob_dict['y'] > current_robot_position.y:
                        commands.append(f"SNAP{states[i].screenshot_id}_L")
                    elif current_ob_dict['y'] == current_robot_position.y:
                        commands.append(f"SNAP{states[i].screenshot_id}_C")
                    elif current_ob_dict['y'] < current_robot_position.y:
                        commands.append(f"SNAP{states[i].screenshot_id}_R")
                    else:
                        commands.append(f"SNAP{states[i].screenshot_id}")
                
                # Obstacle facing EAST, robot facing WEST
                elif current_ob_dict['d'] == 2 and current_robot_position.direction == 6:
                    if current_ob_dict['y'] > current_robot_position.y:
                        commands.append(f"SNAP{states[i].screenshot_id}_R")
                    elif current_ob_dict['y'] == current_robot_position.y:
                        commands.append(f"SNAP{states[i].screenshot_id}_C")
                    elif current_ob_dict['y'] < current_robot_position.y:
                        commands.append(f"SNAP{states[i].screenshot_id}_L")
                    else:
                        commands.append(f"SNAP{states[i].screenshot_id}")

                # Obstacle facing NORTH, robot facing SOUTH
                elif current_ob_dict['d'] == 0 and current_robot_position.direction == 4:
                    if current_ob_dict['x'] > current_robot_position.x:
                        commands.append(f"SNAP{states[i].screenshot_id}_L")
                    elif current_ob_dict['x'] == current_robot_position.x:
                        commands.append(f"SNAP{states[i].screenshot_id}_C")
                    elif current_ob_dict['x'] < current_robot_position.x:
                        commands.append(f"SNAP{states[i].screenshot_id}_R")
                    else:
                        commands.append(f"SNAP{states[i].screenshot_id}")

                # Obstacle facing SOUTH, robot facing NORTH
                elif current_ob_dict['d'] == 4 and current_robot_position.direction == 0:
                    if current_ob_dict['x'] > current_robot_position.x:
                        commands.append(f"SNAP{states[i].screenshot_id}_R")
                    elif current_ob_dict['x'] == current_robot_position.x:
                        commands.append(f"SNAP{states[i].screenshot_id}_C")
                    elif current_ob_dict['x'] < current_robot_position.x:
                        commands.append(f"SNAP{states[i].screenshot_id}_L")
                    else:
                        commands.append(f"SNAP{states[i].screenshot_id}")
            continue

        # If previous state and current state are not the same direction, it means that there will be a turn command involved
        # Assume there are 4 turning command: FR, FL, BL, BR (the turn command will turn the robot 90 degrees)
        # FR00 | FR30: Forward Right;
        # FL00 | FL30: Forward Left;
        # BR00 | BR30: Backward Right;
        # BL00 | BL30: Backward Left;

        # Facing north previously
        if states[i - 1].direction == Direction.NORTH:
            # Facing east afterwards
            if states[i].direction == Direction.EAST:
                commands.append("BL{}".format(steps))
            # Facing west afterwards
            elif states[i].direction == Direction.WEST:
                commands.append("BR{}".format(steps))
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.EAST:
            if states[i].direction == Direction.NORTH:
                commands.append("BR{}".format(steps))

            elif states[i].direction == Direction.SOUTH:
                commands.append("BL{}".format(steps))
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.SOUTH:
            if states[i].direction == Direction.EAST:
                commands.append("BR{}".format(steps))

            elif states[i].direction == Direction.WEST:
                commands.append("BL{}".format(steps))
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.WEST:
            if states[i].direction == Direction.NORTH:
                commands.append("BL{}".format(steps))
            elif states[i].direction == Direction.SOUTH:
                commands.append("BR{}".format(steps))
            else:
                raise Exception("Invalid turing direction")
        else:
            raise Exception("Invalid position")

        # If any of these states has a valid screenshot ID, then add a SNAP command as well to take a picture
        if states[i].screenshot_id != -1:  
            # NORTH = 0
            # EAST = 2
            # SOUTH = 4
            # WEST = 6

            current_ob_dict = obstacles_dict[states[i].screenshot_id] # {'x': 9, 'y': 10, 'd': 6, 'id': 9}
            current_robot_position = states[i] # {'x': 1, 'y': 8, 'd': <Direction.NORTH: 0>, 's': -1}

            # Obstacle facing WEST, robot facing EAST
            if current_ob_dict['d'] == 6 and current_robot_position.direction == 2:
                if current_ob_dict['y'] > current_robot_position.y:
                    commands.append(f"SNAP{states[i].screenshot_id}_L")
                elif current_ob_dict['y'] == current_robot_position.y:
                    commands.append(f"SNAP{states[i].screenshot_id}_C")
                elif current_ob_dict['y'] < current_robot_position.y:
                    commands.append(f"SNAP{states[i].screenshot_id}_R")
                else:
                    commands.append(f"SNAP{states[i].screenshot_id}")
            
            # Obstacle facing EAST, robot facing WEST
            elif current_ob_dict['d'] == 2 and current_robot_position.direction == 6:
                if current_ob_dict['y'] > current_robot_position.y:
                    commands.append(f"SNAP{states[i].screenshot_id}_R")
                elif current_ob_dict['y'] == current_robot_position.y:
                    commands.append(f"SNAP{states[i].screenshot_id}_C")
                elif current_ob_dict['y'] < current_robot_position.y:
                    commands.append(f"SNAP{states[i].screenshot_id}_L")
                else:
                    commands.append(f"SNAP{states[i].screenshot_id}")

            # Obstacle facing NORTH, robot facing SOUTH
            elif current_ob_dict['d'] == 0 and current_robot_position.direction == 4:
                if current_ob_dict['x'] > current_robot_position.x:
                    commands.append(f"SNAP{states[i].screenshot_id}_L")
                elif current_ob_dict['x'] == current_robot_position.x:
                    commands.append(f"SNAP{states[i].screenshot_id}_C")
                elif current_ob_dict['x'] < current_robot_position.x:
                    commands.append(f"SNAP{states[i].screenshot_id}_R")
                else:
                    commands.append(f"SNAP{states[i].screenshot_id}")

            # Obstacle facing SOUTH, robot facing NORTH
            elif current_ob_dict['d'] == 4 and current_robot_position.direction == 0:
                if current_ob_dict['x'] > current_robot_position.x:
                    commands.append(f"SNAP{states[i].screenshot_id}_R")
                elif current_ob_dict['x'] == current_robot_position.x:
                    commands.append(f"SNAP{states[i].screenshot_id}_C")
                elif current_ob_dict['x'] < current_robot_position.x:
                    commands.append(f"SNAP{states[i].screenshot_id}_L")
                else:
                    commands.append(f"SNAP{states[i].screenshot_id}")

    # Final command is the stop command (FIN)
    commands.append("FIN")  

    # Compress commands if there are consecutive forward or backward commands
    compressed_commands = [commands[0]]

    for i in range(1, len(commands)):
        # If both commands are BW
        if commands[i].startswith("BW") and compressed_commands[-1].startswith("BW"):
            # Get the number of steps of previous command
            steps = int(compressed_commands[-1][2:])
            # If steps are not 30, add 10 to the steps
            if steps != 30:
                compressed_commands[-1] = "BW{}".format(steps + 10)
                continue

        # If both commands are FW
        elif commands[i].startswith("FW") and compressed_commands[-1].startswith("FW"):
            # Get the number of steps of previous command
            steps = int(compressed_commands[-1][2:])
            # If steps are not 30, add 10 to the steps
            if steps != 30:
                compressed_commands[-1] = "FW{}".format(steps + 10)
                continue
        
        # Otherwise, just add as usual
        compressed_commands.append(commands[i])

    return compressed_commands

def overlap(r1: tuple, r2: tuple):
    # Rectangle 1 bounds
    min_x1 = r1[0][0]  # top-left x
    max_x1 = r1[1][0]  # top-right x
    max_y1 = r1[0][1]  # top-left y
    min_y1 = r1[2][1]  # bottom-left y

    # Rectangle 2 bounds
    min_x2 = r2[0][0]
    max_x2 = r2[1][0]
    max_y2 = r2[0][1]
    min_y2 = r2[2][1]

    return not (
        max_x1 < min_x2 or
        max_x2 < min_x1 or
        max_y1 < min_y2 or
        max_y2 < min_y1
    )

def capture_image():
    """Simulate image capture from robot's camera

    Returns:
        str: either 'LEFT' or 'RIGHT'
    """
    result = random.choice(["LEFT", "RIGHT"])
    print(f"Captured image indicates turn: {result}")
    return result

@staticmethod
def path_to_stm_commands(path_list):
        """Convert a list of waypoint dicts into STM32 motor commands.

        The argument is the same structure returned by :meth:`_calculate_path`:
        a list of ``{'x':..., 'y':..., 'd':...}`` dictionaries.  Movement is
        interpreted as follows:

        * each grid-cell difference corresponds to 5 cm of motion;
        * consecutive straight steps in the same direction are merged into a
          single ``S<F|B><distance>`` command (three-digit distance in cm);
        * any step where both ``x`` and ``y`` change is treated as a 90° turn.
          The turn direction is determined from the old/new orientation, and
          whether the robot was moving forward or in reverse at the time.
          Commands look like ``RF090``, ``LB090`` etc.

        The helper is deliberately a static method so it can be invoked without
        needing an ``AlgoServer`` instance.  It does **not** modify the input
        list.
        """
        if not path_list:
            return []

        commands = []

        # normalize entries to dictionaries so we can handle CellState or dict
        def to_dict(elem):
            if isinstance(elem, dict):
                return elem
            # fall back to attribute access
            x = getattr(elem, 'x', None)
            y = getattr(elem, 'y', None)
            d = None
            if hasattr(elem, 'direction'):
                d = getattr(elem.direction, 'value', None)
            elif hasattr(elem, 'd'):
                d = getattr(elem, 'd')
            return {'x': x, 'y': y, 'd': d}

        prev = to_dict(path_list[0])
        current_dir = Direction(prev['d'])

        move_dir = None  # 'F' or 'B'
        move_dist = 0

        # unit vectors for each direction (used to determine forward/back)
        vector_map = {
            Direction.NORTH: (0, 1),
            Direction.SOUTH: (0, -1),
            Direction.EAST: (1, 0),
            Direction.WEST: (-1, 0),
        }

        for cell_raw in path_list[1:]:
            cell = to_dict(cell_raw)
            dx = cell['x'] - prev['x']
            dy = cell['y'] - prev['y']
            new_dir = Direction(cell.get('d', current_dir.value))

            # turning event when both coordinates change
            if dx != 0 and dy != 0:
                # flush any ongoing straight move
                if move_dist:
                    commands.append(f"S{move_dir}{move_dist:03d}")
                    move_dist = 0
                    move_dir = None

                # determine left/right based on orientation change
                cur_idx = current_dir.value // 2
                new_idx = new_dir.value // 2

                diff = (new_idx - cur_idx) % 4

                if diff == 1:
                    turn_lr = 'R'
                elif diff == 3:
                    turn_lr = 'L'
                elif diff == 2:
                    # 180° — shouldn't normally happen in your planner
                    turn_lr = 'R'
                else:
                    turn_lr = 'R'

                # was movement forward or backward relative to previous dir?
                forward = (dx * vector_map[current_dir][0]
                           + dy * vector_map[current_dir][1]) > 0
                turn_fb = 'F' if forward else 'B'
                commands.append(f"{turn_lr}{turn_fb}090")
                current_dir = new_dir
            else:
                # straight motion along one axis
                if dx > 0:
                    abs_dir = Direction.EAST
                elif dx < 0:
                    abs_dir = Direction.WEST
                elif dy > 0:
                    abs_dir = Direction.NORTH
                elif dy < 0:
                    abs_dir = Direction.SOUTH
                else:
                    abs_dir = current_dir

                # determine forward/back relative to orientation
                if abs_dir == current_dir:
                    fb = 'F'
                elif abs_dir == {
                    Direction.NORTH: Direction.SOUTH,
                    Direction.SOUTH: Direction.NORTH,
                    Direction.EAST: Direction.WEST,
                    Direction.WEST: Direction.EAST,
                }[current_dir]:
                    fb = 'B'
                else:
                    # orientation mismatch (shouldn't happen)
                    fb = 'F'

                # aggregate distance (5 cm per grid unit)
                step_cm = 5
                if move_dist and fb == move_dir:
                    move_dist += step_cm
                else:
                    if move_dist:
                        commands.append(f"S{move_dir}{move_dist:03d}")
                    move_dir = fb
                    move_dist = step_cm

                current_dir = new_dir

            prev = cell

        # flush any remaining straight move after loop
        if move_dist:
            commands.append(f"S{move_dir}{move_dist:03d}")

        return commands
