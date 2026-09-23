from __future__ import annotations

import pygame

from src.models import Connection, Graph, Zone, ZoneTypes


DEFAULT_ZONE_COLORS: dict[ZoneTypes, tuple[int, int, int]] = {
    ZoneTypes.NORMAL: (200, 200, 200),
    ZoneTypes.BLOCKED: (60, 60, 60),
    ZoneTypes.RESTRICTED: (200, 60, 60),
    ZoneTypes.PRIORITY: (60, 180, 90),
}


NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "red": (220, 60, 60),
    "green": (60, 180, 90),
    "blue": (60, 120, 220),
    "yellow": (230, 200, 60),
    "orange": (230, 140, 40),
    "gray": (120, 120, 120),
    "grey": (120, 120, 120),
    "cyan": (60, 200, 200),
    "purple": (150, 80, 200),
}


ZONE_RADIUS = 22
DRONE_RADIUS = 7
MARGIN = 100


class Renderer:
    """Handles Pygame-based visualization and rendering of the graph map,
    zones, connections, and drones."""

    def __init__(self, graph: Graph, screen_size: tuple[int, int]) -> None:
        """Initializes the Renderer with the graph structure and
        display dimensions.

        Args:
            graph (Graph): The graph map containing zones and connections
            to render.
            screen_size (tuple[int, int]): The width and height of the target
            screen surface.
        """
        self.graph = graph
        self.screen_size = screen_size
        self.font = pygame.font.SysFont("consolas", 14)
        self._compute_scale()

    def _compute_scale(self) -> None:
        """Computes the scaling factor and offset boundaries to fit graph
        coordinates to the screen size."""
        xs = [z.x_location for z in self.graph.zones.values()]
        ys = [z.y_location for z in self.graph.zones.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)

        width, height = self.screen_size
        usable_w = width - 2 * MARGIN
        usable_h = height - 2 * MARGIN

        self._scale = min(usable_w / span_x, usable_h / span_y)
        self._min_x, self._min_y = min_x, min_y

    def to_screen(self, x: int, y: int) -> tuple[int, int]:
        """Converts graph spatial coordinates to pixel screen coordinates.

        Args:
            x (int): The graph X coordinate.
            y (int): The graph Y coordinate.

        Returns:
            tuple[int, int]: The corresponding (pixel_x, pixel_y) screen
            position.
        """
        px = MARGIN + (x - self._min_x) * self._scale
        py = MARGIN + (y - self._min_y) * self._scale
        return int(px), int(py)

    def zone_position(self, zone: Zone) -> tuple[int, int]:
        """Calculates the screen pixel position for a given zone.

        Args:
            zone (Zone): The zone whose position is being resolved.

        Returns:
            tuple[int, int]: The pixel coordinates on the screen.
        """
        return self.to_screen(zone.x_location, zone.y_location)

    def _resolve_zone_color(self, zone: Zone) -> tuple[int, int, int]:
        """Resolves the RGB color for a zone based on custom overrides or
        zone types.

        Args:
            zone (Zone): The zone to evaluate.

        Returns:
            tuple[int, int, int]: The resolved RGB color tuple.
        """
        if zone.color is not None:
            return NAMED_COLORS.get(zone.color, DEFAULT_ZONE_COLORS[zone.type])
        return DEFAULT_ZONE_COLORS[zone.type]

    def draw_connections(self, surface: pygame.Surface) -> None:
        """Draws all network connections/links between zones onto the surface.

        Args:
            surface (pygame.Surface): The Pygame surface to draw onto.
        """
        drawn: set[Connection] = set()
        for neighbors in self.graph.adjacent.values():
            for connection in neighbors.values():
                if connection in drawn:
                    continue
                drawn.add(connection)
                a = self.zone_position(connection.point_a)
                b = self.zone_position(connection.point_b)
                width = 4 if connection.max_link_capacity > 1 else 2
                pygame.draw.line(surface, (140, 140, 140), a, b, width)

    def draw_zones(self, surface: pygame.Surface) -> None:
        """Draws all graph zones, labels, and capacity markers onto
        the surface.

        Args:
            surface (pygame.Surface): The Pygame surface to draw onto.
        """
        for zone in self.graph.zones.values():
            pos = self.zone_position(zone)
            color = self._resolve_zone_color(zone)
            pygame.draw.circle(surface, color, pos, ZONE_RADIUS)
            pygame.draw.circle(surface, (20, 20, 20), pos, ZONE_RADIUS, 2)

            label = self.font.render(zone.name, True, (20, 20, 20))
            surface.blit(
                label, (
                    pos[0] - label.get_width() // 2, pos[1] + ZONE_RADIUS + 4)
            )

            if zone.max_drones != float("inf") and zone.max_drones > 1:
                cap = self.font.render(f"x{int(zone.max_drones)}", True, (
                    255, 255, 255))
                surface.blit(cap, (pos[0] - 8, pos[1] - 8))

    def draw_drone(
        self,
        surface: pygame.Surface,
        position: tuple[float, float],
        label: str,
        color: tuple[int, int, int],
    ) -> None:
        """Draws an individual drone node and its identifier label on
        the surface.

        Args:
            surface (pygame.Surface): The Pygame surface to draw onto.
            position (tuple[float, float]): The pixel coordinates of the drone.
            label (str): The text label or name of the drone.
            color (tuple[int, int, int]): The RGB color assigned to the drone.
        """
        pos = (int(position[0]), int(position[1]))
        pygame.draw.circle(surface, color, pos, DRONE_RADIUS)
        pygame.draw.circle(surface, (0, 0, 0), pos, DRONE_RADIUS, 1)
        text = self.font.render(label, True, (0, 0, 0))
        surface.blit(text, (pos[0] + DRONE_RADIUS, pos[1] - DRONE_RADIUS))
