from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aircraft_design.core.models import ProjectResult


def write_json_result(
    result: ProjectResult,
    path: str | Path,
    *,
    indent: int = 2,
) -> None:
    """
    Write machine-readable calculation result to JSON file.

    Unlike TXT report, JSON output intentionally contains full technical data,
    including chart_data and nested block outputs.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        format_json_result(result, indent=indent),
        encoding="utf-8",
    )


def format_json_result(
    result: ProjectResult,
    *,
    indent: int = 2,
) -> str:
    return json.dumps(
        project_result_to_dict(result),
        ensure_ascii=False,
        indent=indent,
    ) + "\n"


def project_result_to_dict(result: ProjectResult) -> dict[str, Any]:
    """
    Convert ProjectResult to JSON-serializable dictionary.

    The 'outputs' field is duplicated as a convenience aggregate:
    - block_results keeps full block-by-block information;
    - outputs gives quick access to successful block outputs by block name.
    """
    data = asdict(result)

    return {
        "result_format": "aircraft_preliminary_design.result.v1",
        "schema_version": data["schema_version"],
        "success": data["success"],
        "warnings": data["warnings"],
        "errors": data["errors"],
        "block_results": data["block_results"],
        "outputs": result.outputs,
    }