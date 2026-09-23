from __future__ import annotations

import argparse
import sys

from src.models import Drone, Graph
from src.output import OutputError, OutputWriter
from src.parser import Parser, ParsingError
from src.router import PathfindingError, Scheduler, SchedulingError, DronePlan
from src.simulation import SimulationEngine, SimulationError, SimulationResult
from src.visualizer import SimulationGUI


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fly-in",
        description="Simulate and route a fleet "
        "of drones across a zone graph.",
    )
    parser.add_argument(
        "map_path",
        help="Path to the map file describing zones and connections.",
    )
    parser.add_argument(
        "-o", "--output",
        default="output/simulation.log",
        help="Path to write the turn-by-turn movement "
        "log (default: %(default)s).",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Skip the pygame visualization and only produce the log file.",
    )
    return parser


class App:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

    def run(self) -> int:
        graph, nb_drones = self._parse_map()
        if graph is None:
            return 1

        if graph.start_hub is None:
            print(
                "Internal error: parsed graph has no start_hub.",
                file=sys.stderr
            )
            return 1

        drones = [Drone(i, graph.start_hub) for i in range(1, nb_drones + 1)]

        plans = self._build_plans(graph, drones)
        if plans is None:
            return 1

        result = self._run_simulation(graph, drones, plans)
        if result is None:
            return 1

        if not self._write_output(result):
            return 1

        if not self.args.no_gui:
            SimulationGUI(graph, drones, result).run()

        return 0

    def _parse_map(self) -> tuple[Graph | None, int]:
        try:
            return Parser(self.args.map_path).parse()
        except ParsingError as error:
            print(f"Error parsing map: {error}", file=sys.stderr)
            return None, 0

    def _build_plans(
        self, graph: Graph, drones: list[Drone]
    ) -> list[DronePlan] | None:
        try:
            return Scheduler(graph, drones).build_plans()
        except (PathfindingError, SchedulingError) as error:
            print(f"Error computing routes: {error}", file=sys.stderr)
            return None

    def _run_simulation(
        self,
        graph: Graph,
        drones: list[Drone],
        plans: list[DronePlan]
    ) -> SimulationResult | None:
        try:
            return SimulationEngine(graph, drones, plans).run()
        except SimulationError as error:
            print(f"Simulation error: {error}", file=sys.stderr)
            return None

    def _write_output(self, result: SimulationResult) -> bool:
        writer = OutputWriter(self.args.output)
        try:
            writer.write(result)
        except OutputError as error:
            print(str(error), file=sys.stderr)
            return False
        writer.print_summary(result)
        return True


def main() -> None:
    args = build_arg_parser().parse_args()
    exit_code = App(args).run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
