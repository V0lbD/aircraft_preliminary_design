from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aircraft_design.core.models import CalculationTraceRecord, ProjectResult


def write_trace_markdown(result: ProjectResult, path: str | Path) -> None:
    """
    Write calculation trace as human-readable Markdown file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        format_trace_markdown(result),
        encoding="utf-8",
    )


def write_trace_json(
    result: ProjectResult,
    path: str | Path,
    *,
    indent: int = 2,
) -> None:
    """
    Write calculation trace as machine-readable JSON file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        format_trace_json(result, indent=indent),
        encoding="utf-8",
    )


def format_trace_json(
    result: ProjectResult,
    *,
    indent: int = 2,
) -> str:
    data = {
        "trace_format": "aircraft_preliminary_design.trace.v1",
        "schema_version": result.schema_version,
        "success": result.success,
        "records_count": len(result.trace),
        "records": [
            trace_record_to_dict(record)
            for record in result.trace
        ],
    }

    return json.dumps(
        data,
        ensure_ascii=False,
        indent=indent,
    ) + "\n"


def format_trace_markdown(result: ProjectResult) -> str:
    lines: list[str] = []

    lines.extend(
        [
            "# Aircraft preliminary design calculation trace",
            "",
            f"- Schema version: `{result.schema_version}`",
            f"- Calculation success: `{result.success}`",
            f"- Trace records: `{len(result.trace)}`",
            "",
        ]
    )

    if not result.trace:
        lines.extend(
            [
                "No trace records were collected.",
                "",
            ]
        )
        return "\n".join(lines)

    grouped_records = _group_records_by_block(result.trace)

    for block_name, records in grouped_records.items():
        lines.extend(
            [
                f"## {block_name}",
                "",
            ]
        )

        for index, record in enumerate(records, start=1):
            lines.extend(_format_trace_record_markdown(index, record))

    return "\n".join(lines).rstrip() + "\n"


def trace_record_to_dict(record: CalculationTraceRecord) -> dict[str, Any]:
    return asdict(record)


def _group_records_by_block(
    records: list[CalculationTraceRecord],
) -> dict[str, list[CalculationTraceRecord]]:
    grouped: dict[str, list[CalculationTraceRecord]] = {}

    for record in records:
        grouped.setdefault(record.block_name, []).append(record)

    return grouped


def _format_trace_record_markdown(
    index: int,
    record: CalculationTraceRecord,
) -> list[str]:
    lines = [
        f"### {index}. {record.value_name}",
        "",
    ]

    if record.description:
        lines.extend(
            [
                record.description,
                "",
            ]
        )

    lines.extend(
        [
            "**Formula:**",
            "",
            "$$",
            record.formula,
            "$$",
            "",
        ]
    )

    if record.values:
        lines.extend(
            [
                "**Values:**",
                "",
            ]
        )

        for key, value in record.values.items():
            lines.append(f"- `{key}` = `{_format_value(value)}`")

        lines.append("")

    lines.extend(
        [
            "**Result:**",
            "",
            f"`{record.value_name}` = `{_format_value(record.result)}`"
            + (f" `{record.unit}`" if record.unit else ""),
            "",
            "---",
            "",
        ]
    )

    return lines


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        abs_value = abs(value)

        if value != 0 and (abs_value >= 1e6 or abs_value < 1e-4):
            return f"{value:.6e}"

        return f"{value:.6f}".rstrip("0").rstrip(".")

    if isinstance(value, dict | list | tuple):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    return str(value)