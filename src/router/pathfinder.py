from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import TypeAlias

from src.models import Connection, Graph, Zone, ZoneTypes


@dataclass(frozen=True)
class PathStep:
    connection: Connection
    zone: Zone


class PathfindingError(Exception):
    pass


Cost: TypeAlias = tuple[int, int]  # (real cost, penalization)


class Pathfinder:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def shortest_path(self, start: Zone, end: Zone) -> list[PathStep]:
        if start is end:
            return []

        previous: dict[str, PathStep] = {}
        best_cost: dict[str, Cost] = {start.name: (0, 0)}
        visited: set[str] = set()

        counter = 0
        heap: list[tuple[Cost, int, str]] = [
            ((0, 0), counter, start.name)]

        while heap:
            cost, _, zone_name = heapq.heappop(heap)

            if zone_name in visited:
                continue
            visited.add(zone_name)

            if zone_name == end.name:
                break

            for neighbor, connection in self.graph.get_neighbors(zone_name):
                if neighbor.name in visited:
                    continue

                penalty = 0 if neighbor.type == ZoneTypes.PRIORITY else 1
                new_cost: Cost = (
                    cost[0] + neighbor.entry_cost,
                    cost[1] + penalty,
                )

                if (
                    neighbor.name not in best_cost
                    or new_cost < best_cost[neighbor.name]
                ):
                    best_cost[neighbor.name] = new_cost
                    previous[neighbor.name] = PathStep(connection, neighbor)
                    counter += 1
                    heapq.heappush(heap, (new_cost, counter, neighbor.name))

        if end.name not in previous:
            raise PathfindingError(
                f"No path found between '{start.name}' and '{end.name}'."
            )

        path: list[PathStep] = []
        zone_name = end.name
        while zone_name != start.name:
            step = previous[zone_name]
            path.append(step)
            zone_name = step.connection.get_other_end(step.zone).name

        path.reverse()
        return path
