from __future__ import annotations

import json
from pathlib import Path

from aircraft_design.core.errors import FileFormatError
from aircraft_design.core.models import ProjectInput
from aircraft_design.input_builder import create_project_input


def load_project_input(path: str | Path) -> ProjectInput:
    input_path = Path(path)

    if not input_path.exists():
        raise FileFormatError(f"Input file does not exist: {input_path}")

    if input_path.suffix.lower() != ".json":
        raise FileFormatError(f"Input file must have .json extension: {input_path}")

    try:
        with input_path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

    except json.JSONDecodeError as exc:
        raise FileFormatError(f"Invalid JSON file '{input_path}': {exc}") from exc

    return create_project_input(raw_data)