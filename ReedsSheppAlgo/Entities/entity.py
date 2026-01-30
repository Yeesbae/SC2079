from dataclasses import dataclass
from typing import Tuple


@dataclass
class Entity:
    """
    Base class for all physical entities in the environment.

    Coordinate convention:
    - (x, y) represents the bottom-left corner of the entity
    - theta represents orientation in radians
    """

    x: float
    y: float
    theta: float

    def bottom_left(self) -> Tuple[float, float]:
        return self.x, self.y

    def pose(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.theta
