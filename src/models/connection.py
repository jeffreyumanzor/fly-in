from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Drone
    from src.models import Zone


class Connection:
    def __init__(
        self,
        point_a: Zone,
        point_b: Zone,
        max_link_capacity: int = 1,
    ) -> None:
        self.point_a: Zone = point_a
        self.point_b: Zone = point_b
        self.max_link_capacity: int = max_link_capacity
        self.traffic: list[Drone] = []

    def get_name(self, from_zone: Zone) -> str:
        other = self.point_b if from_zone == self.point_a else self.point_a
        return f"{from_zone.name}-{other.name}"

    def get_other_end(self, current: Zone) -> Zone:
        return self.point_b if current == self.point_a else self.point_a

    def __repr__(self) -> str:
        return f"Connection{self.point_a.name}<->{self.point_b.name}"
