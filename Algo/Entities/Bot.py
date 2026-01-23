class Bot:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction

    def __hash__(self):
        return hash((self.x, self.y, self.direction))

    def __eq__(self, other):
        return (self.x, self.y, self.direction) == (other.x, other.y, other.direction)
