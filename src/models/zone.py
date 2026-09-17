from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Drone


class ZoneTypes(Enum):
    NORMAL = 'normal'
    BLOCKED = 'blocked'
    RESTRICTED = 'restricted'
    PRIORITY = 'priority'


class Zone:
    def __init__(
        self,
        name: str,
        x_location: int,
        y_location: int,
        color: str | None = None,
        zone_type: ZoneTypes = ZoneTypes.NORMAL,
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        self.name: str = name
        self.x_location: int = x_location
        self.y_location: int = y_location
        self.color: str | None = color
        self.type: ZoneTypes = zone_type
        self.is_start: bool = is_start
        self.is_end: bool = is_end

        self.max_drones: float = (
            float("inf") if (is_start or is_end) else float(max_drones)
        )

        self.occupants: list['Drone'] = []

    @property
    def entry_cost(self) -> int:
        if self.type == ZoneTypes.RESTRICTED:
            return 2
        return 1

    @property
    def is_walkable(self) -> bool:
        return self.type != ZoneTypes.BLOCKED

    def __repr__(self) -> str:
        """Return string representation of the drone."""
        return f"Drone({self.name}, location={self.type.value})"