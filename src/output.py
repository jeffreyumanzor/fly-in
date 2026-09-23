from __future__ import annotations

from pathlib import Path

from src.simulation import SimulationResult


class OutputError(Exception):
    """Exception raised when an error occurs while writing simulation
    output files.
    """
    pass


class OutputWriter:
    """Handles writing simulation results to disk and printing execution
    summaries.
    """

    def __init__(self, output_path: str | Path) -> None:
        """Initializes the OutputWriter with the destination file path.

        Args:
            output_path (str | Path): The target file path where output
            will be written.
        """
        self.output_path = Path(output_path)

    def write(self, result: SimulationResult) -> None:
        """Writes the simulation result turn tokens into the output file.

        Args:
            result (SimulationResult): The completed simulation results
            containing turn tokens.

        Raises:
            OutputError: If file writing or directory creation fails due to
            an OS error.
        """
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("w", encoding="utf-8") as f:
                for turns_tokens in result.turns:
                    f.write(" ".join(turns_tokens) + "\n")
        except OSError as error:
            raise OutputError(
                f"Could not write output to '{self.output_path}': {error}"
            )

    def print_summary(self, result: SimulationResult) -> None:
        """Prints a human-readable summary of the simulation results
        to standard output.

        Args:
            result (SimulationResult): The completed simulation results
            to summarize.
        """
        print(f"Simulation complete in {result.total_turns} turns.")
        print(f"Output written to: {self.output_path}")
