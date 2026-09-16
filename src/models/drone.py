from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.connection import Connection
    from src.models.zone import Zone


class Drone:
    def __init__(self, drone_id: int, initial_zone: Zone) -> None:
        self.drone_id: int = drone_id
        self.name: str = f"D{drone_id}"