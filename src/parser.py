from __future__ import annotations

from src.models import Connection, Zone, ZoneTypes, Graph


class ParsingError(Exception):
    pass


class Parser:
    ALLOWED_ZONE_KEYS = {"zone", "color", "max_drones"}
    ALLOWED_CONN_KEYS = {"max_link_capacity"}

    def __init__(self, filepath: str) -> None:
        self.filepath: str = self.filepath

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
                f"{line_num}: Invalid metadata bracket order."
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
                f"Line {line_num}: Zone '{name}' is already defined."
            )

        if name in defined_zones:
            raise ParsingError(
                f"Line {line_num}: Zone 'name' is already defined."
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
                f"Line {line_num}: Invalid connection format. \
                    Must be zone1-zone2."
            )