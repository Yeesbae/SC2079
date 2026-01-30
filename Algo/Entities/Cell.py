from constants import Direction

class CellState:
    """Base class for all objects on the arena, such as cells, obstacles, etc"""

    def __init__(self, x, y, direction: Direction = Direction.NORTH, screenshot_id=-1, penalty=0):
        self.x = x
        self.y = y
        self.direction = direction
        # If screenshot_od != -1, the snapshot is taken at that position is for the obstacle with id = screenshot_id
        self.screenshot_id = screenshot_id
        self.penalty = penalty  # Penalty for the view point of taking picture

    def cmp_position(self, x, y) -> bool:
        """Compare given (x,y) position with cell state's position

        Args:
            x (int): x coordinate
            y (int): y coordinate

        Returns:
            bool: True if same, False otherwise
        """
        return self.x == x and self.y == y

    def is_eq(self, x, y, direction):
        """Compare given x, y, direction with cell state's position and direction

        Args:
            x (int): x coordinate
            y (int): y coordinate
            direction (Direction): direction of cell

        Returns:
            bool: True if same, False otherwise
        """
        return self.x == x and self.y == y and self.direction == direction

    def __repr__(self):
        return "x: {}, y: {}, d: {}, screenshot: {}".format(self.x, self.y, self.direction, self.screenshot_id)

    def set_screenshot(self, screenshot_id):
        """Set screenshot id for cell

        Args:
            screenshot_id (int): screenshot id of cell
        """
        self.screenshot_id = screenshot_id

    def get_dict(self):
        """Returns a dictionary representation of the cell

        Returns:
            dict: {x,y,direction,screeshot_id}
        """
        return {'x': self.x, 'y': self.y, 'd': self.direction, 's': self.screenshot_id}
    