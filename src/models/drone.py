from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Connection
    from src.models import Zone


class Drone:
    def __init__(self, drone_id: int, initial_zone: Zone) -> None:
        self.drone_id: int = drone_id
        self.name: str = f"D{drone_id}"
        self.current_zone: Zone | None = initial_zone
        self.current_connection: Connection | None = None
        self.target_zone: Zone | None = None
        self.remaining_turns: int = 0
        self.is_delivered: bool = False

    def __repr__(self) -> str:
        loc = self.current_zone.name if self.current_zone else "in_transit"
        return f"Drone({self.name}, location={loc})"
