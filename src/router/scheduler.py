from __future__ import annotations

from dataclasses import dataclass, field

from src.models import Connection, Drone, Graph, Zone
from src.router import Pathfinder, PathStep


@dataclass(frozen=True)
class ScheduledMove:
    turn: int
    label: str


@dataclass
class DronePlan:
    drone: Drone
    moves: list[ScheduledMove] = field(default_factory=list)
    arrival_turn: int = 0


class SchedulingError(Exception):
    pass


class ReservationTable:
    def __init__(self) -> None:
        self._zone_usage: dict[Zone, dict[int, int]] = {}
        self._link_usage: dict[Connection, dict[int, int]] = {}

    def zone_count(self, zone: Zone, turn: int) -> int:
        return self._zone_usage.get(zone, {}).get(turn, 0)

    def link_count(self, connection: Connection, turn: int) -> int:
        return self._link_usage.get(connection, {}).get(turn, 0)

    def zone_has_room(self, zone: Zone, turn: int) -> bool:
        return self.zone_count(zone, turn) < zone.max_drones

    def link_has_room(self, connection: Connection, turn: int) -> bool:
        return self.link_count(connection, turn) < connection.max_link_capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        turns = self._zone_usage.setdefault(zone, {})
        turns[turn] = turns.get(turn, 0) + 1

    def reserve_link(self, connection: Connection, turn: int) -> None:
        turns = self._link_usage.setdefault(connection, {})
        turns[turn] = turns.get(turn, 0) + 1


class Scheduler:
    MAX_WAIT_ITERATIONS = 5000

    def __init__(self, graph: Graph, drones: list[Drone]) -> None:
        self.graph = graph
        self.drones = drones
        self.pathfinder = Pathfinder(graph)
        self.reservations = ReservationTable()

    def build_plans(self) -> list[DronePlan]:
        start = self.graph.start_hub
        end = self.graph.end_hub
        if start is None or end is None:
            raise SchedulingError("Graph has no start_hub/end_hub defined")

        ideal_path = self.pathfinder.shortest_path(start, end)

        ordered_drones = sorted(self.drones, key=lambda d: d.drone_id)

        return [
            self._build_single_plan(drone, ideal_path, start)
            for drone in ordered_drones
        ]

    def _build_single_plan(
        self, drone: Drone, path: list[PathStep], start: Zone
    ) -> DronePlan:
        plan = DronePlan(drone=drone)
        current_turn = 0
        current_zone = start

        for step in path:
            current_turn = self._advance_through_step(
                plan, drone, current_zone, step.connection, step.zone,
                current_turn,
            )
            current_zone = step.zone

        plan.arrival_turn = current_turn
        return plan

    def _advance_through_step(
        self,
        plan: DronePlan,
        drone: Drone,
        origin: Zone,
        connection: Connection,
        destination: Zone,
        current_turn: int,
    ) -> int:
        cost = destination.entry_cost
        depart_turn = current_turn

        for _ in range(self.MAX_WAIT_ITERATIONS):
            transit_turn = depart_turn + 1
            arrival_turn = depart_turn + cost

            if self.reservations.link_has_room(
                connection, transit_turn
            ) and self.reservations.zone_has_room(destination, arrival_turn):
                self.reservations.reserve_link(connection, transit_turn)
                self.reservations.reserve_zone(destination, arrival_turn)
                self._record_moves(
                    plan, connection, origin, destination, cost,
                    transit_turn, arrival_turn,
                )
                return arrival_turn

            if not origin.is_start:
                self.reservations.reserve_zone(origin, depart_turn + 1)
            depart_turn += 1

        raise SchedulingError(
            f"Drone {drone.name} could not reach '{destination.name}' "
            "(possible deadlock: capacity never freed up)."
        )

    def _record_moves(
        self,
        plan: DronePlan,
        connection: Connection,
        origin: Zone,
        destination: Zone,
        cost: int,
        transit_turn: int,
        arrival_turn: int,
    ) -> None:
        self,
        if cost == 1:
            plan.moves.append(ScheduledMove(transit_turn, destination.name))
        else:
            plan.moves.append(ScheduledMove(arrival_turn, destination.name))
