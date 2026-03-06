from constants import ARENA_WIDTH, ARENA_HEIGHT, Direction, CELL_SIZE_CM


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


def image_command_generator(current_robot_position, current_ob_dict):
    # NORTH = 0
    # EAST = 2
    # SOUTH = 4
    # WEST = 6

    # Obstacle facing WEST, robot facing EAST
    if current_ob_dict['d'] == 6 and current_robot_position.direction == 2:
        if current_ob_dict['y'] > current_robot_position.y:
            return f"SNAP{current_robot_position.screenshot_id}_L"
        elif current_ob_dict['y'] == current_robot_position.y:
            return f"SNAP{current_robot_position.screenshot_id}_C"
        elif current_ob_dict['y'] < current_robot_position.y:
            return f"SNAP{current_robot_position.screenshot_id}_R"
        else:
            return f"SNAP{current_robot_position.screenshot_id}"

    # Obstacle facing EAST, robot facing WEST
    elif current_ob_dict['d'] == 2 and current_robot_position.direction == 6:
        if current_ob_dict['y'] > current_robot_position.y:
            return f"SNAP{current_robot_position.screenshot_id}_R"
        elif current_ob_dict['y'] == current_robot_position.y:
            return f"SNAP{current_robot_position.screenshot_id}_C"
        elif current_ob_dict['y'] < current_robot_position.y:
            return f"SNAP{current_robot_position.screenshot_id}_L"
        else:
            return f"SNAP{current_robot_position.screenshot_id}"

    # Obstacle facing NORTH, robot facing SOUTH
    elif current_ob_dict['d'] == 0 and current_robot_position.direction == 4:
        if current_ob_dict['x'] > current_robot_position.x:
            return f"SNAP{current_robot_position.screenshot_id}_L"
        elif current_ob_dict['x'] == current_robot_position.x:
            return f"SNAP{current_robot_position.screenshot_id}_C"
        elif current_ob_dict['x'] < current_robot_position.x:
            return f"SNAP{current_robot_position.screenshot_id}_R"
        else:
            return f"SNAP{current_robot_position.screenshot_id}"

    # Obstacle facing SOUTH, robot facing NORTH
    elif current_ob_dict['d'] == 4 and current_robot_position.direction == 0:
        if current_ob_dict['x'] > current_robot_position.x:
            return f"SNAP{current_robot_position.screenshot_id}_R"
        elif current_ob_dict['x'] == current_robot_position.x:
            return f"SNAP{current_robot_position.screenshot_id}_C"
        elif current_ob_dict['x'] < current_robot_position.x:
            return f"SNAP{current_robot_position.screenshot_id}_L"
        else:
            return f"SNAP{current_robot_position.screenshot_id}"


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

        # If previous state and current state are the same direction, then it could only be forward / backward
        # movement, because each turn is guaranteed to be 90 degrees.
        if states[i].direction == states[i - 1].direction:
            x_diff = states[i].x - states[i - 1].x
            y_diff = states[i].y - states[i - 1].y

            # Use abs() to ensure the distance is positive regardless of direction
            distance = (abs(x_diff) + abs(y_diff)) * CELL_SIZE_CM

            if (x_diff > 0 and states[i].direction == Direction.EAST) or (
                x_diff < 0 and states[i].direction == Direction.WEST) or (
                y_diff > 0 and states[i].direction == Direction.NORTH) or (
                y_diff < 0 and states[i].direction == Direction.SOUTH):
                commands.append(f"SF{distance:03d}")

            else:
                commands.append(f"SB{distance:03d}")

            # If any of these states has a valid screenshot ID, then add a SNAP command as well to take a picture
            if states[i].screenshot_id != -1:
                current_ob_dict = obstacles_dict[states[i].screenshot_id] # {'x': 9, 'y': 10, 'd': 6, 'id': 9}
                current_robot_position = states[i] # {'x': 1, 'y': 8, 'd': <Direction.NORTH: 0>, 's': -1}
                commands.append(image_command_generator(current_robot_position, current_ob_dict))

            continue

        # If previous state and current state are not the same direction, it means that there will be a turn command involved
        # Turn commands:
        # RF090: Right Forward turn 90°
        # LF090: Left Forward turn 90°
        # RB090: Right Backward turn 90°
        # LB090: Left Backward turn 90°
        #
        # Direction mapping (backward-left maneuver = right turn, backward-right = left turn):
        # Forward Right turn: North → East & x, y both increased = RF090
        # Backward Right turn: North → West & x increased, y decreased = RB090
        # Forward Left turn: North → West & x decreased, y increased = LF090
        # Backward Left turn: North → East & x, y both decreased = LB090

        turn_map = {
            Direction.NORTH: [
                ((1, 1), Direction.EAST, "RF"),
                ((-1, 1), Direction.WEST, "LF"),
                ((1, -1), Direction.WEST, "RB"),
                ((-1, -1), Direction.EAST, "LB"),
            ],
            Direction.SOUTH: [
                ((1, -1), Direction.EAST, "LF"),
                ((-1, -1), Direction.WEST, "RF"),
                ((1, 1), Direction.WEST, "LB"),
                ((-1, 1), Direction.EAST, "RB"),
            ],
            Direction.EAST: [
                ((1, 1), Direction.NORTH, "LF"),
                ((-1, 1), Direction.SOUTH, "LB"),
                ((-1, -1), Direction.NORTH, "RB"),
                ((1, -1), Direction.SOUTH, "RF"),
            ],
            Direction.WEST: [
                ((-1, 1), Direction.NORTH, "RF"),
                ((-1, -1), Direction.SOUTH, "LF"),
                ((1, 1), Direction.SOUTH, "RB"),
                ((1, -1), Direction.NORTH, "LB"), 
            ]
        }
            
        # Turn Cases
        for (x_check, y_check), end_dir, turn_type in turn_map[states[i - 1].direction]:
            x_change = states[i].x - states[i - 1].x
            y_change = states[i].y - states[i - 1].y
            if states[i].direction == end_dir and x_change * x_check > 0 and y_change * y_check > 0:
                commands.append(f"{turn_type}090")
                break

        # If any of these states has a valid screenshot ID, then add a SNAP command as well to take a picture
        if states[i].screenshot_id != -1:  
            current_ob_dict = obstacles_dict[states[i].screenshot_id] # {'x': 9, 'y': 10, 'd': 6, 'id': 9}
            current_robot_position = states[i] # {'x': 1, 'y': 8, 'd': <Direction.NORTH: 0>, 's': -1}
            commands.append(image_command_generator(current_robot_position, current_ob_dict))

    # Final command is the stop command (FIN)
    commands.append("FIN")  

    return commands


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


@staticmethod
def compress_path(path):
    if not path:
        return []

    compressed = [path[0]]
    prev = path[0]
    current_move = 0  # 0 unset, 1 forward, -1 backward

    for i in range(1, len(path)):
        curr = path[i]

        # -------- TURN --------
        if prev.direction != curr.direction:
            # close previous segment
            if compressed[-1] is not prev:
                compressed.append(prev)

            # turn is its own segment
            compressed.append(curr)

            current_move = 0
            prev = curr
            continue

        # -------- SCREENSHOT --------
        if prev.screenshot_id != -1:
            if compressed[-1] is not prev:
                compressed.append(prev)

            current_move = 0
            prev = curr
            continue

        # -------- STRAIGHT --------
        dx = curr.x - prev.x
        dy = curr.y - prev.y

        if prev.direction == Direction.NORTH:
            move = 1 if dy > 0 else -1
        elif prev.direction == Direction.SOUTH:
            move = 1 if dy < 0 else -1
        elif prev.direction == Direction.EAST:
            move = 1 if dx > 0 else -1
        else:  # WEST
            move = 1 if dx < 0 else -1

        if current_move == 0:
            current_move = move
        elif move != current_move:
            if compressed[-1] is not prev:
                compressed.append(prev)
            current_move = move

        prev = curr

    # close final segment
    if compressed[-1] is not path[-1]:
        compressed.append(path[-1])

    return compressed
