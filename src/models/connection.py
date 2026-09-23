from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Drone
    from src.models import Zone


class Connection:
    """Represents a bidirectional edge between two zones."""
    def __init__(
        self,
        point_a: Zone,
        point_b: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        """Initialize a Connection instance.

        Args:
            point_a (Zone): First endpoint zone.
            point_b (Zone): Second endpoint zone.
            max_link_capacity (int, optional): Maximum number of drones
            traversing at once.
        """
        self.point_a: Zone = point_a
        self.point_b: Zone = point_b
        self.max_link_capacity: int = max_link_capacity
        self.traffic: list[Drone] = []

    def get_name(self, from_zone: Zone) -> str:
        """Return the connection name in traversal order (e.g., 'hub-roof1').

        Args:
            from_zone (Zone): The zone from which the connection
            is being traversed.

        Returns:
            str: Formatted connection string as required by the
            simulation output.
        """
        other = self.point_b if from_zone == self.point_a else self.point_a
        return f"{from_zone.name}-{other.name}"

    def get_other_end(self, current: Zone) -> Zone:
        """Get the connected zone opposite to the current one.

        Args:
            current (Zone): One of the connection's endpoints.

        Returns:
            Zone: The opposite Zone endpoint.
        """
        return self.point_b if current == self.point_a else self.point_a

    def __repr__(self) -> str:
        """
        Returns:
            str: Return string representation of the connection.
        """
        return f"Connection{self.point_a.name}<->{self.point_b.name}"
