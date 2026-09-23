from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Drone


class ZoneTypes(Enum):
    """Enumeration of all supported zone types.
    """
    NORMAL = 'normal'
    BLOCKED = 'blocked'
    RESTRICTED = 'restricted'
    PRIORITY = 'priority'


class Zone:
    """Represents a node (zone) in the network graph.
    """
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
        """Initialize a Zone instance.

        Args:
            name (str): Unique name of the zone (no spaces or dashes).
            x_location (int): Integer X coordinate.
            y_location (int): Integer Y coordinate.
            color (str | None, optional): Optional color string for
            visualization. Defaults to None.
            zone_type (ZoneTypes):Zone type defining movement properties.
            Defaults to ZoneTypes.NORMAL.
            max_drones (int, optional): Maximum concurrent occupants
            (ignored for start/end). Defaults to 1.
            is_start (bool, optional): True if this is the start hub.
            Defaults to False.
            is_end (bool, optional): True if this is the end hub.
            Defaults to False.
        """
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
        """
        Returns:
            int: Return the turn cost to move into this zone.
        """
        if self.type == ZoneTypes.RESTRICTED:
            return 2
        return 1

    @property
    def is_walkable(self) -> bool:
        """
        Returns:
            bool: Return True if drones can traverse this zone.
        """
        return self.type != ZoneTypes.BLOCKED

    def __repr__(self) -> str:
        """
        Returns:
            str: Return string representation of the drone.
        """
        return f"Zone({self.name}, location={self.type.value})"
