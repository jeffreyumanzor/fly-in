from __future__ import annotations

import colorsys

import math
import pygame

from src.models import Connection, Drone, Graph, Zone
from src.router import ScheduledMove
from src.simulation import SimulationResult
from src.visualizer.renderer import Renderer

SCREEN_SIZE = (900, 900)
BACKGROUND_COLOR = (245, 245, 245)
TURN_DURATION_MS = 1000
OVERLAP_OFFSET_RADIUS = 12


def _generate_drone_colors(count: int) -> list[tuple[int, int, int]]:
    """Generates a list of visually distinct RGB colors evenly distributed
    across the HSV hue circle.

    Args:
        count (int): The number of drone colors required.

    Returns:
        list[tuple[int, int, int]]: A list of RGB color tuples.
    """
    colors = []
    for i in range(count):
        hue = i / max(count, 1)
        r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 0.85)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


class SimulationGUI:
    """Handles Pygame-based playback and time interpolation of pre-computed
    simulation results.
    """

    def __init__(
        self,
        graph: Graph,
        drones: list[Drone],
        result: SimulationResult
    ) -> None:
        """Initializes the SimulationGUI with the graph map, drones,
        and simulation result frames.

        Args:
            graph (Graph): The graph structure containing zones
            and connections.
            drones (list[Drone]): The list of drones taking part in
            the simulation.
            result (SimulationResult): The calculated simulation outcome
            and timeline frames.
        """
        self.graph = graph
        self.drones = drones
        self.result = result

        pygame.init()
        pygame.display.set_caption("Fly-in — Drone Routing Simulation")
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(graph, SCREEN_SIZE)

        self._colors = dict(
            zip((d.drone_id for d in drones), _generate_drone_colors(
                len(drones)))
        )

        self._turn_index = 0
        self._elapsed_ms = 0.0
        self._paused = False
        self._speed = 1.0

        start = graph.start_hub
        assert start is not None
        start_pos = self.renderer.zone_position(start)

        self._current_pos: dict[int, tuple[float, float]] = {
            d.drone_id: start_pos for d in drones
        }
        self._start_of_turn_pos: dict[int, tuple[float, float]] = dict(
            self._current_pos)
        self._target_pos: dict[int, tuple[float, float]] = dict(
            self._current_pos)

        self._delivered: set[int] = set()
        self._pending_delivery: set[int] = set()

        if self.result.frames:
            self._prepare_turn(self.result.frames[0])

    def run(self) -> None:
        """Runs the main visualization and interaction event loop until closed.
        """
        running = True
        while running:
            dt = self.clock.tick(60)
            running = self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()

    def _handle_events(self) -> bool:
        """Processes user input events such as pausing, changing speed,
        or quitting.

        Returns:
            bool: True if the simulation loop should continue running,
            False otherwise.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_SPACE:
                    self._paused = not self._paused
                if event.key == pygame.K_EQUALS:
                    self._speed = min(self._speed * 1.5, 8.0)
                if event.key == pygame.K_MINUS:
                    self._speed = max(self._speed / 1.5, 0.25)
        return True

    def _prepare_turn(self, frame: list[tuple[Drone, ScheduledMove]]) -> None:
        """Prepares coordinate positions for the upcoming turn based on
        scheduled moves.

        Args:
            frame (list[tuple[Drone, ScheduledMove]]): The list of active
            drone moves for the current turn.
        """
        self._start_of_turn_pos = dict(self._current_pos)

        for drone, move in frame:
            end_pos: tuple[float, float]
            target = move.target
            if isinstance(target, Zone):
                end_pos = self.renderer.zone_position(target)
                if target.is_end:
                    self._pending_delivery.add(drone.drone_id)
            elif isinstance(target, Connection):
                a = self.renderer.zone_position(target.point_a)
                b = self.renderer.zone_position(target.point_b)
                end_pos = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            else:
                end_pos = self._current_pos[drone.drone_id]

            self._target_pos[drone.drone_id] = end_pos

    def _update(self, dt: float) -> None:
        """Updates interpolated drone positions and manages turn progression
        over time.

        Args:
            dt (float): The delta time in milliseconds elapsed since the
            last frame.
        """
        if self._paused or self._turn_index >= len(self.result.frames):
            return

        self._elapsed_ms += dt * self._speed
        t = min(self._elapsed_ms / TURN_DURATION_MS, 1.0)

        for drone in self.drones:
            start = self._start_of_turn_pos[drone.drone_id]
            end = self._target_pos[drone.drone_id]
            self._current_pos[drone.drone_id] = (
                start[0] + (end[0] - start[0]) * t,
                start[1] + (end[1] - start[1]) * t,
            )

        if t >= 1.0:
            self._delivered |= self._pending_delivery
            self._pending_delivery.clear()

            self._turn_index += 1
            self._elapsed_ms = 0.0
            if self._turn_index < len(self.result.frames):
                self._prepare_turn(self.result.frames[self._turn_index])

    def _draw(self) -> None:
        """Renders the complete simulation scene, including the graph,
        active drones, and HUD.
        """
        self.screen.fill(BACKGROUND_COLOR)
        self.renderer.draw_connections(self.screen)
        self.renderer.draw_zones(self.screen)

        active_ids = [
            d.drone_id for d in self.drones
            if d.drone_id not in self._delivered
        ]
        spread_positions = self._spread_overlapping_drones(active_ids)

        for drone in self.drones:
            if drone.drone_id in self._delivered:
                continue
            pos = spread_positions[drone.drone_id]
            self.renderer.draw_drone(
                self.screen, pos, drone.name, self._colors[drone.drone_id]
            )

        self._draw_hud()

    def _draw_hud(self) -> None:
        """Renders the heads-up display (HUD) showing current turn
        progress, state, and controls.
        """
        font = self.renderer.font
        total = len(self.result.frames)
        shown_turn = min(self._turn_index + 1, total)
        status = "PAUSED" if self._paused else "PLAYING"
        text = (
            f"Turn {shown_turn}/{total}  |  {status}  |  "
            f"speed x{self._speed:.2f}  |  "
            f"delivered {len(self._delivered)}/{len(self.drones)}"
        )
        self.screen.blit(font.render(text, True, (20, 20, 20)), (10, 10))
        hint = font.render(
            "SPACE: pause/play   +/-: speed   ESC: quit",
            True,
            (90, 90, 90)
        )
        self.screen.blit(hint, (10, SCREEN_SIZE[1] - 24))

    def _spread_overlapping_drones(
        self, active_ids: list[int]
    ) -> dict[int, tuple[float, float]]:
        """ A visual help to avoid drones flying the same connection
        overlapping.

        Args:
            active_ids (list[int]): IDs of the drones currently on screen
            (i.e. not yet delivered) that need a draw position resolved
            for this frame.

        Returns:
            dict[int, tuple[float, float]]: For each drone id in
            `active_ids`, the screen coordinates it should be drawn at
            this frame. Drones alone at their position keep their exact
            coordinates; drones sharing a position are offset around it.
        """
        groups: dict[tuple[int, int], list[int]] = {}
        for drone_id in active_ids:
            pos = self._current_pos[drone_id]
            key = (round(pos[0]), round(pos[1]))
            groups.setdefault(key, []).append(drone_id)

        resolved: dict[int, tuple[float, float]] = {}
        for key, ids_in_group in groups.items():
            base_x, base_y = self._current_pos[ids_in_group[0]]

            if len(ids_in_group) == 1:
                resolved[ids_in_group[0]] = (base_x, base_y)
                continue

            count = len(ids_in_group)
            for i, drone_id in enumerate(sorted(ids_in_group)):
                angle = (2 * math.pi * i) / count
                offset_x = OVERLAP_OFFSET_RADIUS * math.cos(angle)
                offset_y = OVERLAP_OFFSET_RADIUS * math.sin(angle)
                resolved[drone_id] = (base_x + offset_x, base_y + offset_y)

        return resolved
