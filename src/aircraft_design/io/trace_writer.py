import json
from pathlib import Path

from aircraft_design.core.models.project import ProjectState


def write_trace_json(project: ProjectState, path: str | Path, *, indent: int = 2) -> None:
    """Записывает ход вычислений в виде машиночитаемого JSON-файла."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "schema_version": project.schema_version,
        "success": len(project.errors) == 0,
        "records_count": len(project.trace_records),
        "records": project.trace_records,
    }

    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")


def write_trace_markdown(project: ProjectState, path: str | Path) -> None:
    """Записывает ход вычислений в виде удобного для чтения файла Markdown."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success_text = "True" if len(project.errors) == 0 else "False"
    lines = [
        "# Aircraft preliminary design calculation trace\n",
        f"- Schema version: `{project.schema_version}`",
        f"- Calculation success: `{success_text}`",
        f"- Trace records: `{len(project.trace_records)}`\n",
    ]

    if not project.trace_records:
        lines.append("No trace records were collected.\n")
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return

    # Группируем логи по имени блока
    grouped = {}
    for record in project.trace_records:
        block = record.get("block", "unknown")
        grouped.setdefault(block, []).append(record)

    for block_name, records in grouped.items():
        lines.append(f"## {block_name}\n")

        for i, r in enumerate(records, 1):
            val_name = r.get('value_name', '')
            lines.append(f"### {i}. {val_name}\n")

            if desc := r.get('description'):
                lines.append(f"{desc}\n")

            lines.append("**Formula:**\n")
            lines.append(f"$$\n{r.get('formula', '')}\n$$\n")

            if values := r.get('values'):
                lines.append("**Values:**\n")
                for k, v in values.items():
                    v_str = f"{v:.6e}" if isinstance(v, float) and (abs(v) >= 1e6 or (0 < abs(v) < 1e-4)) else str(v)
                    lines.append(f"- `{k}` = `{v_str}`")
                lines.append("\n")

            result = r.get('result')
            unit = r.get('unit', '')
            res_str = f"{result:.6e}" if isinstance(result, float) and (
                        abs(result) >= 1e6 or (0 < abs(result) < 1e-4)) else str(result)
            lines.append(f"**Result:**\n\n`{val_name}` = `{res_str}` {unit}\n\n---\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")