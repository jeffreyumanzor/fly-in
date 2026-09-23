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
    """Builds and configures the command-line argument parser for
    the application.

    Returns:
        argparse.ArgumentParser: The configured argument parser instance.
    """
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
    """Manages the overall execution lifecycle of the drone routing and
    simulation application."""

    def __init__(self, args: argparse.Namespace) -> None:
        """Initializes the App with parsed command-line arguments.

        Args:
            args (argparse.Namespace): The parsed command-line arguments.
        """
        self.args = args

    def run(self) -> int:
        """Executes the full application workflow including parsing, routing,
        simulation, output, and optional GUI.

        Returns:
            int: The exit status code (0 for success, 1 for failure).
        """
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
        """Parses the map file into a graph model and retrieves the drone
        count.

        Returns:
            tuple[Graph | None, int]: A tuple containing the parsed Graph
            (or None on error) and the number of drones.
        """
        try:
            return Parser(self.args.map_path).parse()
        except ParsingError as error:
            print(f"Error parsing map: {error}", file=sys.stderr)
            return None, 0

    def _build_plans(
        self, graph: Graph, drones: list[Drone]
    ) -> list[DronePlan] | None:
        """Computes and builds movement plans for the drone fleet.

        Args:
            graph (Graph): The parsed graph structure.
            drones (list[Drone]): The list of drones to plan for.

        Returns:
            list[DronePlan] | None: A list of drone movement plans, or None
            if routing fails.
        """
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
        """Executes the simulation engine using the graph, drones, and plans.

        Args:
            graph (Graph): The graph structure.
            drones (list[Drone]): The list of drones.
            plans (list[DronePlan]): The scheduled movement plans.

        Returns:
            SimulationResult | None: The simulation outcome results, or None
            if an error occurs.
        """
        try:
            return SimulationEngine(graph, drones, plans).run()
        except SimulationError as error:
            print(f"Simulation error: {error}", file=sys.stderr)
            return None

    def _write_output(self, result: SimulationResult) -> bool:
        """Writes the simulation results to disk using the output writer.

        Args:
            result (SimulationResult): The completed simulation results.

        Returns:
            bool: True if writing succeeded, False otherwise.
        """
        writer = OutputWriter(self.args.output)
        try:
            writer.write(result)
        except OutputError as error:
            print(str(error), file=sys.stderr)
            return False
        writer.print_summary(result)
        return True


def main() -> None:
    """Parses command-line arguments, runs the application, and exits with the
    resulting code.
    """
    args = build_arg_parser().parse_args()
    exit_code = App(args).run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
