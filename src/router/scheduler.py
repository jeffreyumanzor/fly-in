from __future__ import annotations

from dataclasses import dataclass, field

from src.models import Connection, Drone, Graph, Zone
from src.router import Pathfinder, PathStep


@dataclass(frozen=True)
class ScheduledMove:
    """Represents a scheduled movement action for a drone at a specific turn.

    Attributes:
        turn (int): The simulation turn when the move occurs.
        label (str): The display label or name associated with the target.
        target (Zone | Connection): The zone or connection targeted
        by the move.
    """
    turn: int
    label: str
    target: Zone | Connection


@dataclass
class DronePlan:
    """Represents the complete schedule of moves and final arrival time
    for a drone.

    Attributes:
        drone (Drone): The drone assigned to this plan.
        moves (list[ScheduledMove]): An ordered list of scheduled moves.
        arrival_turn (int): The simulation turn when the drone reaches
        its destination.
    """
    drone: Drone
    moves: list[ScheduledMove] = field(default_factory=list)
    arrival_turn: int = 0


class SchedulingError(Exception):
    """Exception raised when a drone's schedule or routing cannot be resolved.
    """
    pass


class ReservationTable:
    """Tracks occupancy and capacity constraints over time for zones and
    connections.
    """

    def __init__(self) -> None:
        """Initializes an empty reservation table."""
        self._zone_usage: dict[Zone, dict[int, int]] = {}
        self._link_usage: dict[Connection, dict[int, int]] = {}

    def zone_count(self, zone: Zone, turn: int) -> int:
        """Gets the number of drones occupying a specific zone at a given turn.

        Args:
            zone (Zone): The zone to check.
            turn (int): The simulation turn.

        Returns:
            int: The current count of drones in the zone.
        """
        return self._zone_usage.get(zone, {}).get(turn, 0)

    def link_count(self, connection: Connection, turn: int) -> int:
        """Gets the number of drones traversing a specific connection
        at a given turn.

        Args:
            connection (Connection): The connection link to check.
            turn (int): The simulation turn.

        Returns:
            int: The current count of drones on the link.
        """
        return self._link_usage.get(connection, {}).get(turn, 0)

    def zone_has_room(self, zone: Zone, turn: int) -> bool:
        """Checks whether a zone has available capacity at a specific turn.

        Args:
            zone (Zone): The zone to check.
            turn (int): The simulation turn.

        Returns:
            bool: True if the zone is under capacity, False otherwise.
        """
        return self.zone_count(zone, turn) < zone.max_drones

    def link_has_room(self, connection: Connection, turn: int) -> bool:
        """Checks whether a connection link has available capacity at
        a specific turn.

        Args:
            connection (Connection): The connection link to check.
            turn (int): The simulation turn.

        Returns:
            bool: True if the link is under capacity, False otherwise.
        """
        return self.link_count(connection, turn) < connection.max_link_capacity

    def reserve_zone(self, zone: Zone, turn: int) -> None:
        """Reserves a slot in a zone for a specific turn, incrementing
        its usage count.

        Args:
            zone (Zone): The zone to reserve.
            turn (int): The simulation turn.
        """
        turns = self._zone_usage.setdefault(zone, {})
        turns[turn] = turns.get(turn, 0) + 1

    def reserve_link(self, connection: Connection, turn: int) -> None:
        """Reserves a slot on a connection for a specific turn, incrementing
        its usage count.

        Args:
            connection (Connection): The connection link to reserve.
            turn (int): The simulation turn.
        """
        turns = self._link_usage.setdefault(connection, {})
        turns[turn] = turns.get(turn, 0) + 1


class Scheduler:
    """Manages scheduling and coordination of drone movements across
    the graph map.
    """

    MAX_WAIT_ITERATIONS = 5000

    def __init__(self, graph: Graph, drones: list[Drone]) -> None:
        """Initializes the Scheduler with the graph map and the list of drones.

        Args:
            graph (Graph): The graph structure containing zones
            and connections.
            drones (list[Drone]): The list of drones to be scheduled.
        """
        self.graph = graph
        self.drones = drones
        self.pathfinder = Pathfinder(graph)
        self.reservations = ReservationTable()

    def build_plans(self) -> list[DronePlan]:
        """Builds coordinated movement plans for all drones from start
        to end hub.

        Returns:
            list[DronePlan]: A list of complete movement plans for each drone.

        Raises:
            SchedulingError: If the graph lacks a start or end hub definition.
        """
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
        """Constructs a movement plan for a single drone along the ideal path.

        Args:
            drone (Drone): The drone being planned for.
            path (list[PathStep]): The optimal sequence of path steps
            to follow.
            start (Zone): The starting zone.

        Returns:
            DronePlan: The completed plan containing scheduled moves and
            arrival turn.
        """
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
        """Advances a drone through a single path step, resolving wait times
        for capacities.

        Args:
            plan (DronePlan): The drone plan being built.
            drone (Drone): The drone being moved.
            origin (Zone): The starting zone of the step.
            connection (Connection): The connection traversed.
            destination (Zone): The target destination zone.
            current_turn (int): The current simulation turn.

        Returns:
            int: The updated turn number after successfully reaching
            the destination.

        Raises:
            SchedulingError: If a deadlock prevents the drone from reaching
            the destination.
        """
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
        """Appends scheduled move records to a drone's plan based on
        travel cost.

        Args:
            plan (DronePlan): The drone plan to record moves into.
            connection (Connection): The connection being traversed.
            origin (Zone): The origin zone.
            destination (Zone): The destination zone.
            cost (int): The entry cost of the destination zone.
            transit_turn (int): The turn the drone enters transit.
            arrival_turn (int): The turn the drone arrives at the destination.
        """
        if cost == 1:
            plan.moves.append(
                ScheduledMove(
                    turn=transit_turn,
                    label=destination.name,
                    target=destination,
                )
            )
        else:
            plan.moves.append(
                ScheduledMove(
                    turn=transit_turn,
                    label=connection.get_name(origin),
                    target=connection,
                )
            )
            plan.moves.append(
                ScheduledMove(
                    turn=arrival_turn,
                    label=destination.name,
                    target=destination,
                )
            )
