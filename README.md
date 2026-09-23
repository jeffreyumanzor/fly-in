*This project has been created as part of the 42 curriculum by juasanta.*

# Fly-in — Drone Fleet Routing Simulation

## Description

Fly-in is a simulation system that routes a fleet of autonomous drones from a
central `start_hub` to a target `end_hub` across a network of connected zones,
while respecting movement constraints, zone/connection capacity limits, and
different zone types (`normal`, `priority`, `restricted`, `blocked`).

The goal is to move every drone from start to end in the fewest possible
simulation turns, producing a turn-by-turn movement log and a real-time
graphical visualization of the simulation built with `pygame`.

The project is fully object-oriented, statically typed (`mypy`), linted with
`flake8`, and implements its own pathfinding and scheduling logic from
scratch — no graph libraries (`networkx`, `graphlib`, etc.) are used.

## Features

- Custom map file parser with strict syntax validation and clear error
  messages (line number + cause).
- Dijkstra-based pathfinding implemented from scratch, weighted by zone entry
  cost, with a soft preference for `priority` zones.
- Multi-drone scheduling using a prioritized planning strategy with a
  space-time reservation table, respecting zone capacity (`max_drones`) and
  connection capacity (`max_link_capacity`).
- Correct handling of `restricted` zones (2-turn atomic transit — no waiting
  mid-flight).
- Discrete-turn simulation engine that validates capacity in real time and
  produces the exact output format required by the subject.
- Real-time graphical visualization with `pygame`: animated drone movement,
  colored zones by type, connection capacity indicators, and a live HUD
  (pause/play, speed control, delivery count).
- Plain text turn-by-turn output log.

## Project Structure

.
├── Makefile
├── README.md
├── pyproject.toml / uv.lock
├── main.py
└── src/
├── parser.py
├── output.py
├── models/ # Zone, Connection, Drone, Graph
├── router/ # PathFinder (Dijkstra) + Scheduler (space-time reservations)
├── simulation/ # SimulationEngine (turn-by-turn execution)
└── visualizer/ # Renderer + SimulationGUI (pygame)


## Instructions

### Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) for dependency and virtual environment
  management

### Installation

```bash
make install
```

### Running the simulation

```bash
make run ARGS="maps/easy1.txt"
```

or directly:

```bash
uv run main.py maps/easy1.txt
```

### Available options

| Flag | Description |
|---|---|
| `map_path` | Path to the map file (positional, required) |
| `-o, --output` | Path to the output log (default: `output/simulation.log`) |
| `--no-gui` | Skip the pygame visualization, only produce the log file |

Example:

```bash
uv run main.py maps/challenger.txt --no-gui -o output/challenger.log
```

### Debugging

```bash
make debug ARGS="maps/easy1.txt"
```

### Linting

```bash
make lint
```

### Cleaning

```bash
make clean
```

## Algorithm & Implementation Strategy

The routing problem is split into two independent stages, each with a single
responsibility:

**1. Pathfinding (`PathFinder`)** — A hand-written Dijkstra's algorithm
computes the lowest-cost route from `start_hub` to `end_hub`, using each
zone's entry cost (`1` for `normal`/`priority`, `2` for `restricted`,
`blocked` zones are excluded from traversal entirely). To honor the
requirement that `priority` zones "should be prioritized" without altering
their real cost, each path is scored with a composite key
`(real_cost, penalty)`, where `penalty` only breaks ties between equally
short paths — it never overrides the real cost.

**2. Scheduling (`Scheduler`)** — Since all drones share the same
start/end, a single ideal path is computed and reused for every drone. Drones
are then scheduled one at a time (prioritized planning) against a
**space-time reservation table** that tracks, per turn, how many drones
occupy each zone and traverse each connection. A drone advances along the
ideal path only when both the connection and — critically, for `restricted`
zones, the *exact future turn of arrival* — have available capacity;
otherwise it waits one turn and retries. This guarantees a conflict-free
plan without requiring an optimal (NP-hard) multi-agent solution, and
comfortably meets the benchmark turn targets given in the subject.

**3. Simulation (`SimulationEngine`)** — Executes the validated plans
turn by turn, releasing each drone's current position before occupying its
destination (so a drone can enter a zone the same turn another one leaves
it), and re-validates capacity in real time as a safety net against
scheduling bugs. It produces the exact `D<ID>-<zone|connection>` output
format required by the subject.

## Visual Representation

The `pygame`-based GUI plays back the simulation result computed by the
engine — it does not make any routing decisions, it only visualizes them.

- **Zones** are drawn as colored circles (using the map's `color=` metadata
  when present, otherwise a default color per zone type), labeled with their
  name, with a capacity badge (`x2`, `x3`...) for zones allowing more than
  one drone.
- **Connections** are drawn as lines between zones, thicker when
  `max_link_capacity > 1`.
- **Drones** are drawn as small colored circles (one distinct color per
  drone, evenly spread across the hue spectrum) and animated by
  interpolating their position between the start and end of each simulation
  turn — including a mid-connection pause while transiting toward a
  `restricted` zone, reflecting the two-turn atomic transit rule.
- **HUD** displays the current turn, play/pause state, animation speed, and
  the number of drones delivered so far.
- Controls: `SPACE` to pause/play, `+`/`-` to change speed, `ESC` to quit.

This gives an intuitive, real-time view of how drones distribute across
paths, wait for capacity, and converge at the goal — much easier to audit
than reading the raw text log alone.

## Example

**Input** (`maps/example.txt`):

nb_drones: 2

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]

connection: hub-roof1
connection: roof1-roof2
connection: roof2-goal


**Command:**

```bash
uv run main.py maps/example.txt --no-gui
```

**Output** (`output/simulation.log`):

D1-hub-roof1
D1-roof1
D1-roof2
D1-goal

Simulation complete in 4 turns.
Output written to: output/simulation.log


## Resources

- [Dijkstra's algorithm — overview](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html)
- [Prioritized Planning for Multi-Agent Path Finding — general concept](https://en.wikipedia.org/wiki/Multi-agent_pathfinding)
- [pygame documentation](https://www.pygame.org/docs/)
- [uv documentation](https://docs.astral.sh/uv/)
- [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [mypy documentation](https://mypy.readthedocs.io/)

### AI Usage

AI assistance (Claude) was used throughout this project in the following ways:

- **Architecture discussion**: talked through the design of the `router`
  (Dijkstra-based `PathFinder` + prioritized-planning `Scheduler` with a
  space-time reservation table), the `simulation` engine, and the `pygame`
  visualizer before writing any code, to validate the approach against the
  subject's constraints (capacity rules, restricted-zone transit, OOP-only,
  no graph libraries).
- **Code generation with explanation**: AI-generated implementations of
  `PathFinder`, `Scheduler`, `SimulationEngine`, `Renderer`, and
  `SimulationGUI` were provided together with inline comments explaining the
  reasoning behind each design decision, then reviewed, tested against
  multiple maps (including edge cases), and debugged manually.
- **Debugging**: two concrete bugs were found and fixed through AI-assisted
  reasoning rather than AI-provided fixes alone — an engine crash on
  `restricted`-zone arrival caused by an overly broad precondition check, and
  a visualization bug where drones vanished instead of animating their
  arrival at `end_hub`, both diagnosed by tracing the actual state flow
  turn by turn.
- All AI-suggested code was tested against the provided example maps plus
  custom maps created specifically to validate capacity limits, restricted
  zones, and deadlock scenarios, before being accepted into the project.

<!--
TODO before submission:
- [ ] Replace <login1>/<login2> with actual 42 logins
- [ ] Add docstrings across all modules (PEP 257)
- [ ] Fill in real benchmark numbers per map difficulty
- [ ] Double-check "Instructions" matches the final Makefile targets
-->