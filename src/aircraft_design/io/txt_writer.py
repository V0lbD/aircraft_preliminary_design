from __future__ import annotations

from pathlib import Path

from aircraft_design.core.models import ProjectResult


def write_txt_result(result: ProjectResult, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("Aircraft preliminary design calculation result")
    lines.append("=" * 52)
    lines.append(f"Schema version: {result.schema_version}")
    lines.append(f"Success: {result.success}")
    lines.append("")

    if result.warnings:
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    if result.errors:
        lines.append("Errors:")
        for error in result.errors:
            lines.append(f"  - {error}")
        lines.append("")

    lines.append("Blocks:")
    if not result.block_results:
        lines.append("  No blocks were executed.")
    else:
        for block_result in result.block_results:
            lines.append(f"  [{block_result.block_name}]")
            lines.append(f"    success: {block_result.success}")

            if block_result.outputs:
                lines.append("    outputs:")
                for key, value in block_result.outputs.items():
                    lines.append(f"      {key}: {value}")

            if block_result.warnings:
                lines.append("    warnings:")
                for warning in block_result.warnings:
                    lines.append(f"      - {warning}")

            if block_result.errors:
                lines.append("    errors:")
                for error in block_result.errors:
                    lines.append(f"      - {error}")

    output_path.write_text("\n".join(lines), encoding="utf-8")