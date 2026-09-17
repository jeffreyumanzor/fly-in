from __future__ import annotations

from src.models import Connection
from src.models import Zone


class Graph:
    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.adjacent: dict[str, dict[str, Connection]] = {}
        self.start_hub: Zone | None = None
        self.end_hub: Zone | None = None

    def add_zone(self, zone: Zone) -> None:
        if zone.name not in self.zones:
            self.zones[zone.name] = zone
            self.adjacent[zone.name] = {}

        if zone.is_start:
            self.start_hub = zone
        if zone.is_end:
            self.end_hub = zone

    def add_connection(self, connection: Connection) -> None:
        name_a = connection.point_a.name
        name_b = connection.point_b.name

        self.add_zone(connection.point_a)
        self.add_zone(connection.point_b)

        self.adjacent[name_a][name_b] = connection
        self.adjacent[name_b][name_a] = connection

    def get_connection(
        self, zone_a: str, zone_b: str
    ) -> Connection | None:
        return self.adjacent.get(zone_a, {}).get(zone_b)

    def get_neighbors(self, zone_name: str) -> list[tuple[Zone, Connection]]:
        neighbors: list[tuple[Zone, Connection]] = []
        for target_name, conn in self.adjacent.get(zone_name, {}).items():
            target_zone = self.zones[target_name]
            if target_zone.is_walkable:
                neighbors.append((target_zone, conn))
        return neighbors
