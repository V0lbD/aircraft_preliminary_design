from pathlib import Path
from typing import Any
from aircraft_design.core.models.project import ProjectState


def _format_value(val: Any) -> str:
    """Умное форматирование чисел для отчета."""
    if isinstance(val, float):
        if val == 0.0:
            return "0"
        # Если число больше 0.001, округляем до 3 знаков после запятой
        if abs(val) >= 0.001:
            s = f"{val:.3f}"
            return s.rstrip("0").rstrip(".") if "." in s else s
        return f"{val:.3e}"
    return str(val)


def _build_unit_map(project: ProjectState) -> dict[str, str]:
    """Динамически собирает единицы измерения из всех параметров проекта."""
    unit_map = {}
    # Проходим по всем группам параметров
    for group_name in ["feasibility", "preliminary", "mass", "technology", "geometry"]:
        group = getattr(project, group_name, None)
        if group:
            # Извлекаем параметры прямо из класса
            for attr_name, attr in group.__class__.__dict__.items():
                if hasattr(attr, "unit") and attr.unit:
                    unit_map[attr_name] = attr.unit

    # Добавляем алиасы для переменных, которые мы переименовывали внутри add_trace
    unit_map.update({
        "range": unit_map.get("design_range", ""),
        "duration": unit_map.get("flight_duration_h", ""),
        "speed": unit_map.get("max_speed", ""),
        "ceiling": unit_map.get("practical_ceiling_m", ""),
        "payload": unit_map.get("payload_mass", ""),
        "S_wing": unit_map.get("S_W", ""),
        "lambda_wing": unit_map.get("Lambda", ""),
    })
    return unit_map


def write_trace_markdown(project: ProjectState, file_path: str | Path) -> None:
    """Экспорт трассировки расчетов (формул и значений) в Markdown."""
    if not project.trace_records:
        raise ValueError("Нет данных для трассировки. Сначала выполните расчет.")

    unit_map = _build_unit_map(project)

    lines = [
        "# Отчет о ходе расчета (Trace)",
        "Ниже приведены основные формулы, подставленные значения и результаты вычислений.\n"
    ]

    current_block = None
    for record in project.trace_records:
        block = record.get("block") or "Общее"
        if block != current_block:
            lines.append(f"## Блок: {block}")
            current_block = block

        val_name = record.get("value_name", "Параметр")
        desc = record.get("description", "")
        formula = record.get("formula", "")
        res = record.get("result", "")
        res_unit = record.get("unit", "")

        lines.append(f"### {val_name}")
        if desc:
            lines.append(f"**Описание:** {desc}")

        if formula:
            lines.append("**Формула:**")
            # Если формула склеена через \\ и это не система уравнений (cases)
            if r"\\" in formula and r"\begin" not in formula:
                parts = formula.split(r"\\")
                for part in parts:
                    if part.strip():
                        lines.append(f"$$\n{part.strip()}\n$$")
            else:
                lines.append(f"$$\n{formula}\n$$")

        vals = record.get("values", {})
        if vals:
            formatted_vals = []
            for k, v in vals.items():
                val_str = _format_value(v)
                unit_str = unit_map.get(k, "")

                # Собираем строку вида "V_s = 20 км/ч"
                if unit_str:
                    formatted_vals.append(f"{k} = {val_str} {unit_str}")
                else:
                    formatted_vals.append(f"{k} = {val_str}")

            vals_str = ", ".join(formatted_vals)
            lines.append(f"**Значения:** `{vals_str}`")

        res_str = f"{_format_value(res)} {res_unit}".strip()
        lines.append(f"**Результат:** `{res_str}`\n")
        lines.append("---\n")

    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")