from __future__ import annotations

from dataclasses import dataclass

from src.models import Connection, Drone, Graph, Zone
from src.router import DronePlan, ScheduledMove


class SimulationError(Exception):
    """Base class for simulation errors."""
    pass


@dataclass
class SimulationResult:
    turns: list[list[str]]
    total_turns: int
    frames: list[list[tuple[Drone, ScheduledMove]]]


class SimulationEngine:
    def __init__(
        self, graph: Graph, drones: list[Drone], plans: list[DronePlan]
    ) -> None:
        self.graph = graph
        self.drones = drones
        self.plans = plans

        self._moves_by_turn: dict[int, dict[int, ScheduledMove]] = {
            plan.drone.drone_id: {move.turn: move for move in plan.moves}
            for plan in plans
        }

    def run(self) -> SimulationResult:
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
