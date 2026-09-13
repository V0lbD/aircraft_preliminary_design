from datetime import datetime
from pathlib import Path

from aircraft_design.core.models.project import ProjectState
from aircraft_design.io.json_io import _get_parameters_from_group

# Маппинг групп данных на названия секций
SECTION_NAMES = {
    "feasibility": "Оценка реализуемости",
    "preliminary": "Предварительные характеристики",
    "mass": "Оценка масс",
    "geometry": "Геометрия",
    "technology": "Технологии и экономика"
}


def write_txt_result(project: ProjectState, path: str | Path) -> None:
    """Write human-readable calculation report to TXT file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    status = "SUCCESS" if len(project.errors) == 0 else "FAILED"
    lines = [
        "Aircraft preliminary design report",
        "=" * 60,
        f"Created at: {datetime.now().isoformat(timespec='seconds')}",
        f"Calculation status: {status}\n",
    ]

    # Динамический вывод результатов блоков
    for i, (section_key, section_display) in enumerate(SECTION_NAMES.items(), 1):
        lines.append(f"{i}. {section_display}")
        lines.append("-" * 60)

        group_obj = getattr(project, section_key, None)
        if not group_obj:
            lines.append("Нет данных.\n")
            continue

        has_data = False
        for attr_name, param in _get_parameters_from_group(group_obj):
            if param.is_input: continue  # Выводим только результаты

            val = getattr(group_obj, attr_name)
            if val is None: continue

            has_data = True

            # Форматирование
            unit_str = f" {param.unit}" if param.unit else ""
            if isinstance(val, bool):
                val_str = "Да" if val else "Нет"
            elif isinstance(val, float):
                val_str = f"{val:.4f}".rstrip("0").rstrip(".")
            else:
                val_str = str(val)

            lines.append(f"{param.display_name}: {val_str}{unit_str}")

        if not has_data:
            lines.append("Нет данных.")
        lines.append("")

    # Вывод ошибок и предупреждений
    lines.append("Статус и ошибки")
    lines.append("-" * 60)

    if not project.warnings and not project.errors:
        lines.append("Нет предупреждений и ошибок.\n")
    else:
        if project.warnings:
            lines.append("Предупреждения:")
            for w in project.warnings: lines.append(f"  - {w}")
        if project.errors:
            lines.append("\nОшибки:")
            for e in project.errors: lines.append(f"  - {e}")

    output_path.write_text("\n".join(lines), encoding="utf-8")