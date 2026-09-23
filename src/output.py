from __future__ import annotations

from pathlib import Path

from src.simulation import SimulationResult


class OutputError(Exception):
    """Error"""


class OutputWriter:
    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)

    def write(self, result: SimulationResult) -> None:
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
        print(f"Simulation complete in {result.total_turns} turns.")
        print(f"Output written to: {self.output_path}")
