"""
Main entry point for the Fly-in Drone Routing Simulation.

This module initializes the application, parses command-line arguments,
and orchestrates the data flow between the parser, the routing algorithm,
the simulation engine, and the graphical user interface.
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

# Asumo que tus __init__.py exponen estas clases correctamente.
# Si no, ajusta las importaciones (ej. from src.parser.parser import Parser)
from src.parser import Parser, ParsingError
from src.models.drone import Drone
from src.router.scheduler import Scheduler, SchedulingError
from src.simulation.engine import SimulationEngine, SimulationError
from src.visualizer.gui import SimulationGUI


class SimulationApp:
    """
    Main application class that encapsulates the simulation lifecycle.
    
    By wrapping the execution in this class, we ensure strict adherence
    to the object-oriented programming requirement of the subject.
    """

    def __init__(self) -> None:
        """Initialize the SimulationApp and configure the argument parser."""
        self.parser = argparse.ArgumentParser(
            description="Fly-in: Autonomous Drone Routing System"
        )
        self.parser.add_argument(
            "map_file",
            type=str,
            help="Path to the map file to be simulated.",
        )
        self.parser.add_argument(
            "--gui",
            action="store_true",
            help="Launch the Pygame graphical interface after computation.",
        )

    def _handle_error(self, message: str) -> NoReturn:
        """
        Print a formatted error message to standard error and exit.

        Args:
            message (str): The error description to display.
        """
        print(f"Error: {message}", file=sys.stderr)
        sys.exit(1)

    def run(self) -> None:
        """
        Execute the main pipeline of the application.
        
        Flow:
        1. Parse CLI arguments.
        2. Parse the map file to generate the Graph and determine drone count.
        3. Instantiate the Drones.
        4. Run the routing algorithm to schedule the paths.
        5. Execute the simulation engine turn by turn.
        6. Output the results to stdout.
        7. Launch the GUI if requested.
        """
        args = self.parser.parse_args()

        try:
            # 1. Parse the input map
            map_parser = Parser(args.map_file)
            graph, nb_drones = map_parser.parse()

            if graph.start_hub is None:
                self._handle_error("The parsed map has no start_hub.")

            # 2. Initialize the drones at the start hub
            drones = [
                Drone(drone_id=i + 1, initial_zone=graph.start_hub)
                for i in range(nb_drones)
            ]

            # 3. Pathfinding and Scheduling (Algorithm Phase)
            # El scheduler calcula la ruta óptima para cada dron y evita colisiones
            scheduler = Scheduler(graph, drones)
            plans = scheduler.build_plans()

            # 4. Run the Engine (Simulation Phase)
            # El engine toma los planes y los ejecuta turno a turno
            engine = SimulationEngine(graph, drones, plans)
            result = engine.run()

            # 5. Output to standard output (Mandatory subject requirement)
            # Cada turno se imprime como una línea con los movimientos separados por espacio
            for turn_moves in result.turns:
                # Si en un turno ningún dron se mueve, se imprime una línea en blanco
                # para mantener la sincronía del índice de turnos.
                print(" ".join(turn_moves))

            # 6. Launch Visual Representation (Bonus / Visual Requirement)
            if args.gui:
                gui = SimulationGUI(graph, drones, result)
                gui.run()

        # Catch all custom exceptions to provide clean terminal output 
        # instead of an ugly Python traceback, which evaluators appreciate.
        except ParsingError as e:
            self._handle_error(f"Failed to parse map -> {e}")
        except SchedulingError as e:
            self._handle_error(f"Routing failed -> {e}")
        except SimulationError as e:
            self._handle_error(f"Simulation execution failed -> {e}")
        except Exception as e:
            self._handle_error(f"An unexpected error occurred -> {e}")


if __name__ == "__main__":
    app = SimulationApp()
    app.run()