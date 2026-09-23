from __future__ import annotations

from dataclasses import dataclass

from src.models import Connection, Drone, Graph, Zone
from src.router import DronePlan, ScheduledMove


class SimulationError(Exception):
    """Base class for simulation errors encountered during execution."""
    pass


@dataclass
class SimulationResult:
    """Represents the outcome and timeline data of a completed simulation run.

    Attributes:
        turns (list[list[str]]): A list of text tokens representing moves
        executed per turn.
        total_turns (int): The total number of turns the simulation took to
        complete.
        frames (list[list[tuple[Drone, ScheduledMove]]]): Detailed
        frame-by-frame movement data for each turn.
    """
    turns: list[list[str]]
    total_turns: int
    frames: list[list[tuple[Drone, ScheduledMove]]]


class SimulationEngine:
    """Executes and validates the simulation timeline using scheduled
    drone movement plans.
    """

    def __init__(
        self, graph: Graph, drones: list[Drone], plans: list[DronePlan]
    ) -> None:
        """Initializes the SimulationEngine with the graph map, drones, and
        their plans.

        Args:
            graph (Graph): The graph structure containing zones and
            connections.
            drones (list[Drone]): The list of drones participating
            in the simulation.
            plans (list[DronePlan]): The scheduled movement plans for
            each drone.
        """
        self.graph = graph
        self.drones = drones
        self.plans = plans

        self._moves_by_turn: dict[int, dict[int, ScheduledMove]] = {
            plan.drone.drone_id: {move.turn: move for move in plan.moves}
            for plan in plans
        }

    def run(self) -> SimulationResult:
        """Runs the full simulation from start to finish, tracking turns and
        frame states.

        Returns:
            SimulationResult: The collected results and timelines of the
            simulation run.

        Raises:
            SimulationError: If the graph lacks a start hub or if simulation
            constraints are violated.
        """
        start = self.graph.start_hub
        if start is None:
            raise SimulationError("Graph has no start_hub.")

        self._reset_drones(start)

        total_turns = max((p.arrival_turn for p in self.plans), default=0)
        output_lines: list[list[str]] = []
        frames: list[list[tuple[Drone, ScheduledMove]]] = []

        for turn in range(1, total_turns + 1):
            tokens, frame = self._simulate_turn(turn)
            output_lines.append(tokens)
            frames.append(frame)

        return SimulationResult(
            turns=output_lines, total_turns=total_turns, frames=frames)

    def _reset_drones(self, start: Zone) -> None:
        """Resets all drone states and places them at the start hub zone.

        Args:
            start (Zone): The start hub zone where all drones begin.
        """
        start.occupants.clear()
        for drone in self.drones:
            drone.current_zone = start
            drone.current_connection = None
            drone.target_zone = None
            drone.remaining_turns = 0
            drone.is_delivered = False
            start.occupants.append(drone)

    def _simulate_turn(
        self, turn: int
    ) -> tuple[list[str], list[tuple[Drone, ScheduledMove]]]:
        """Simulates a single turn by processing scheduled movements and
        updating occupancy.

        Args:
            turn (int): The current simulation turn number.

        Returns:
            tuple[list[str], list[tuple[Drone, ScheduledMove]]]: A tuple
            containing the text tokens for the turn and the list of active
            moves.

        Raises:
            SimulationError: If a drone lacks an origin zone or capacity
            limits are breached.
        """
        pending: list[tuple[Drone, ScheduledMove]] = []
        origin_of_this_turn: dict[Drone, Zone] = {}
        for plan in self.plans:
            drone = plan.drone
            if drone.is_delivered:
                continue
            move = self._moves_by_turn.get(drone.drone_id, {}).get(turn)
            if move is not None:
                pending.append((drone, move))

        for drone, move in pending:
            if isinstance(move.target, Connection):
                if drone.current_zone is None:
                    raise SimulationError(
                        f"{drone.name} has no current zone before entering "
                        f"connection '{move.label}' on turn {turn}."
                    )
                origin_of_this_turn[drone] = drone.current_zone
            self._release_current_position(drone)

        tokens: list[str] = []
        for drone, move in pending:
            self._occupy(drone, move, origin_of_this_turn)
            tokens.append(f"{drone.name}-{move.label}")

        return tokens, pending

    def _release_current_position(self, drone: Drone) -> None:
        """Releases a drone from its current zone or connection occupancy.

        Args:
            drone (Drone): The drone whose position is being released.
        """
        if drone.current_connection is not None:
            drone.current_connection.traffic.remove(drone)
            drone.current_connection = None
        elif drone.current_zone is not None:
            drone.current_zone.occupants.remove(drone)
            drone.current_zone = None

    def _occupy(
        self,
        drone: Drone,
        move: ScheduledMove,
        origin: dict[Drone, Zone],
    ) -> None:
        """Moves a drone into its target zone or connection, enforcing
        capacity checks.

        Args:
            drone (Drone): The drone being moved.
            move (ScheduledMove): The scheduled move containing the target.
            origin (dict[Drone, Zone]): A mapping of drones to their origin
            zones for this turn.

        Raises:
            SimulationError: If connection traffic or zone occupant capacities
            are exceeded.
        """
        target = move.target

        if isinstance(target, Connection):
            if len(target.traffic) >= target.max_link_capacity:
                raise SimulationError(
                    f"Link capacity exceeded on turn {move.turn} "
                    f"for connection '{move.label}'."
                )
            target.traffic.append(drone)
            drone.current_connection = target
            drone.target_zone = target.get_other_end(origin[drone])
            drone.remaining_turns = 1

        elif isinstance(target, Zone):
            if len(target.occupants) >= target.max_drones:
                raise SimulationError(
                    f"Zone capacity exceeded on turn {move.turn} "
                    f"for zone '{move.label}'."
                )
            target.occupants.append(drone)
            drone.current_zone = target
            drone.target_zone = None
            drone.remaining_turns = 0

            if target.is_end:
                drone.is_delivered = True
