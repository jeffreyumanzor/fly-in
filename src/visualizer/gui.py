from __future__ import annotations

import colorsys

import pygame

from src.models import Connection, Drone, Graph, Zone
from src.router import ScheduledMove
from src.simulation import SimulationResult
from src.visualizer.renderer import Renderer

SCREEN_SIZE = (900, 900)
BACKGROUND_COLOR = (245, 245, 245)
TURN_DURATION_MS = 1000


def _generate_drone_colors(count: int) -> list[tuple[int, int, int]]:
    """
    Reparte `count` colores en el círculo de tono (hue), para que cada
    dron sea distinguible sin tener que elegir colores a mano.
    """
    colors = []
    for i in range(count):
        hue = i / max(count, 1)
        r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 0.85)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


class SimulationGUI:
    """
    Reproduce con pygame el SimulationResult ya calculado por el engine.

    El engine decidió TODO (qué dron se mueve, cuándo, hacia dónde);
    esta clase solo decide CÓMO SE VE ESO EN EL TIEMPO: interpola la
    posición de cada dron entre donde terminó el turno anterior y su
    destino del turno actual. Separar "qué pasó" de "cómo se muestra"
    es lo que permite pausar, cambiar velocidad, etc. sin tocar nada
    de router/simulation.
    """

    def __init__(
        self,
        graph: Graph,
        drones: list[Drone],
        result: SimulationResult
    ) -> None:
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

        # --- Estado de reproducción ---
        self._turn_index = 0    # índice (0-based) del turno que se está animando
        self._elapsed_ms = 0.0  # tiempo transcurrido dentro de ese turno
        self._paused = False
        self._speed = 1.0

        start = graph.start_hub
        assert start is not None  # ya validado por el engine antes de llegar aquí
        start_pos = self.renderer.zone_position(start)

        # Posición renderizada de cada dron en este instante (se recalcula cada frame)
        self._current_pos: dict[int, tuple[float, float]] = {
            d.drone_id: start_pos for d in drones
        }
        # Dónde arrancó y dónde debe terminar cada dron en el turno actual
        self._start_of_turn_pos: dict[int, tuple[float, float]] = dict(
            self._current_pos)
        self._target_pos: dict[int, tuple[float, float]] = dict(
            self._current_pos)

        self._delivered: set[int] = set()
        self._pending_delivery: set[int] = set()

        if self.result.frames:
            self._prepare_turn(self.result.frames[0])

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(60)  # ms desde el frame anterior, tope 60 FPS
            running = self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()

    def _handle_events(self) -> bool:
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
        """
        Fija, para el turno que va a reproducirse, dónde arranca cada
        dron (su posición renderizada actual) y a dónde debe llegar.
        """
        self._start_of_turn_pos = dict(self._current_pos)

        for drone, move in frame:
            target = move.target
            if isinstance(target, Zone):
                end_pos = self.renderer.zone_position(target)
                if target.is_end:
                    self._pending_delivery.add(drone.drone_id)
            elif isinstance(target, Connection):
                # Punto medio de la conexión: representa "en tránsito".
                a = self.renderer.zone_position(target.point_a)
                b = self.renderer.zone_position(target.point_b)
                end_pos = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            else:
                end_pos = self._current_pos[drone.drone_id]

            self._target_pos[drone.drone_id] = end_pos

    def _update(self, dt: float) -> None:
        if self._paused or self._turn_index >= len(self.result.frames):
            return

        self._elapsed_ms += dt * self._speed
        t = min(self._elapsed_ms / TURN_DURATION_MS, 1.0)

        # Interpolación lineal simple entre inicio y destino del turno.
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
        self.screen.fill(BACKGROUND_COLOR)
        self.renderer.draw_connections(self.screen)
        self.renderer.draw_zones(self.screen)

        for drone in self.drones:
            if drone.drone_id in self._delivered:
                continue
            pos = self._current_pos[drone.drone_id]
            self.renderer.draw_drone(
                self.screen, pos, drone.name, self._colors[drone.drone_id]
            )

        self._draw_hud()

    def _draw_hud(self) -> None:
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
            "SPACE: pause/play   +/-: speed   ESC: quit", True, (90, 90, 90)
        )
        self.screen.blit(hint, (10, SCREEN_SIZE[1] - 24))
