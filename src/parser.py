from __future__ import annotations

from src.models import Connection, Zone, ZoneTypes, Graph


class ParsingError(Exception):
    pass


class Parser:
    ALLOWED_ZONE_KEYS = {"zone", "color", "max_drones"}
    ALLOWED_CONN_KEYS = {"max_link_capacity"}

    def __init__(self, filepath: str) -> None:
        self.filepath: str = filepath

    def _parse_metadata(
        self, line: str, line_num: int, allowed_keys: set[str]
    ) -> dict[str, str]:
        metadata: dict[str, str] = {}
        count_open = line.count("[")
        count_close = line.count("]")

        if count_open == 0 and count_close == 0:
            return metadata

        if count_open != 1 or count_close != 1:
            raise ParsingError(
                f"Line {line_num}: Mismatched or multiple metadata brackets."
            )

        start_idx = line.find("[")
        end_idx = line.find("]")

        if start_idx > end_idx:
            raise ParsingError(
                f"Line {line_num}: Invalid metadata bracket order."
            )

        after_bracket = line[end_idx + 1:].strip()
        if after_bracket:
            raise ParsingError(
                f"Line {line_num}: Unexpected tokens after metadata block."
            )

        meta_content = line[start_idx + 1: end_idx].strip()
        if not meta_content:
            return metadata

        for token in meta_content.split():
            if "=" not in token:
                raise ParsingError(
                    f"Line {line_num}: Invalid metadata format '{token}'"
                )

            key, value = token.split("=", 1)
            key, value = key.strip(), value.strip()

            if key not in allowed_keys:
                raise ParsingError(
                    f"Line {line_num}: Unknown metadata key '{key}'."
                )

            if not value:
                raise ParsingError(
                    f"Line {line_num}: Empty value for metadata key '{key}'."
                )

            metadata[key] = value

        return metadata

    def _parse_zone(
        self,
        line: str,
        line_num: int,
        graph: Graph,
        defined_zones: set[str],
    ) -> None:
        parts = line.split(":", 1)
        prefix = parts[0].strip()
        remainder = parts[1].strip()

        base_info = remainder.split("[")[0].strip()
        tokens = base_info.split()

        if len(tokens) != 3:
            raise ParsingError(
                f"Line {line_num}: Zone requires name, X, and Y coordinates."
            )

        name, x_str, y_str = tokens

        if "-" in name:
            raise ParsingError(
                f"Line {line_num}: Zone '{name}' cannot contain dashes."
            )

        if name in defined_zones:
            raise ParsingError(
                f"Line {line_num}: Zone '{name}' is already defined."
            )

        try:
            x_coord, y_coord = int(x_str), int(y_str)
        except ValueError:
            raise ParsingError(
                f"Line {line_num}: Zone coordinates must be valid integers."
            )

        metadata = self._parse_metadata(
            remainder, line_num, self.ALLOWED_ZONE_KEYS
        )

        is_start = prefix == "start_hub"
        is_end = prefix == "end_hub"

        zone_type_str = metadata.get("zone", "normal")
        try:
            zone_type = ZoneTypes(zone_type_str)
        except ValueError:
            raise ParsingError(
                f"Line {line_num}: Invalid zone type '{zone_type_str}'."
            )

        if (is_start or is_end) and zone_type == ZoneTypes.BLOCKED:
            raise ParsingError(
                f"Line {line_num}: Start and end hubs cannot be blocked"
            )

        color: str | None = metadata.get("color")

        max_drones = 1
        if "max_drones" in metadata:
            try:
                parsed_capacity = int(metadata["max_drones"])
                if parsed_capacity <= 0:
                    raise ValueError
                if not (is_start or is_end):
                    max_drones = parsed_capacity
            except ValueError:
                raise ParsingError(
                    f"Line {line_num}: max_drones must be > 0"
                )

        new_zone = Zone(
            name=name,
            x_location=x_coord,
            y_location=y_coord,
            color=color,
            zone_type=zone_type,
            max_drones=max_drones,
            is_start=is_start,
            is_end=is_end,
        )
        graph.add_zone(new_zone)
        defined_zones.add(name)

    def _parse_connection(
        self,
        line: str,
        line_num: int,
        graph: Graph,
        defined_zones: set[str],
        defined_connections: set[tuple[str, str]],
    ) -> None:
        remainder = line.split(":", 1)[1].strip()
        base_info = remainder.split("[")[0].strip()

        base_tokens = base_info.split()
        if len(base_tokens) != 1 or "-" not in base_tokens[0]:
            raise ParsingError(
                f"Line {line_num}: Invalid connection format. "
                "Must be zone1-zone2."
            )

        nodes = base_tokens[0].split("-")
        if len(nodes) != 2:
            raise ParsingError(
                f"Line {line_num}: Connection must link exactly two zones."
            )

        name1, name2 = nodes[0].strip(), nodes[1].strip()

        if not name1 or not name2:
            raise ParsingError(
                f"Line {line_num}: Invalid zone names in connection."
            )

        if name1 == name2:
            raise ParsingError(
                f"Line {line_num}: Self-connections are not permitted."
            )

        if name1 not in defined_zones or name2 not in defined_zones:
            raise ParsingError(
                f"Line {line_num}: Connection references an undefined zone."
            )

        conn_key = (min(name1, name2), max(name1, name2))
        if conn_key in defined_connections:
            raise ParsingError(
                f"Line {line_num}: Duplicate connection '{name1}-{name2}'"
            )

        metadata = self._parse_metadata(
            remainder, line_num, self.ALLOWED_CONN_KEYS
        )

        max_cap = 1
        if "max_link_capacity" in metadata:
            try:
                max_cap = int(metadata['max_link_capacity'])
                if max_cap <= 0:
                    raise ValueError
            except ValueError:
                raise ParsingError(
                    f"Line {line_num}: "
                    "max_link_capacity must be a positive integer."
                )

        zone1 = graph.zones[name1]
        zone2 = graph.zones[name2]

        new_conn = Connection(zone1, zone2, max_cap)
        graph.add_connection(new_conn)
        defined_connections.add(conn_key)

    def parse(self) -> tuple[Graph, int]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as file:
                lines = file.readlines()
        except OSError as error:
            raise ParsingError(
                f"Unable to read file '{self.filepath}': {error.strerror}"
            )

        graph = Graph()
        nb_drones = 0
        nb_drones_found = False

        has_start = False
        has_end = False

        defined_zones: set[str] = set()
        defined_connections: set[tuple[str, str]] = set()

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.split("#")[0].strip()

            if not line:
                continue

            if not nb_drones_found:
                if not line.startswith("nb_drones:"):
                    raise ParsingError(
                        f"Line {line_num}: First non-comment line must be "
                        "'nb_drones: <number>'."
                    )

                try:
                    nb_drones = int(line.split(":", 1)[1].strip())
                    if nb_drones <= 0:
                        raise ValueError
                except (ValueError, IndexError):
                    raise ParsingError(
                        f"Line {line_num}: nb_drones must be a positive int."
                    )
                nb_drones_found = True
                continue

            if line.startswith(("start_hub:", "end_hub:", "hub:")):
                if line.startswith("start_hub:"):
                    if has_start:
                        raise ParsingError(
                            f"Line {line_num}: Multiple start_hubs defined."
                        )
                    has_start = True
                elif line.startswith("end_hub:"):
                    if has_end:
                        raise ParsingError(
                            f"Line {line_num}: Multiple end_hubs defined."
                        )
                    has_end = True

                self._parse_zone(line, line_num, graph, defined_zones)
            elif line.startswith("connection:"):
                self._parse_connection(
                    line,
                    line_num,
                    graph,
                    defined_zones,
                    defined_connections,
                )
            else:
                raise ParsingError(
                    f"Line {line_num}: Unrecognized syntax '{line}'."
                )

        if not nb_drones_found:
            raise ParsingError(
                f"Line {line_num}: Map file is empty or missing 'nb_drones:'."
            )

        if not has_start or not has_end:
            raise ParsingError(
                "Map must define exactly one start_hub and one end_hub."
            )

        return graph, nb_drones
