from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from aircraft_design.core.models import ProjectResult


def write_txt_result(result: ProjectResult, path: str | Path) -> None:
    """
    Write human-readable calculation report to TXT file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        format_txt_report(result),
        encoding="utf-8",
    )


def format_txt_report(result: ProjectResult) -> str:
    """
    Format calculation result as a human-readable text report.

    This report is intentionally not a full technical dump.
    Large UI-specific fields such as chart_data are omitted.
    """
    lines: list[str] = []

    lines.extend(_format_header(result))
    lines.extend(_format_preliminary_sizing(result))
    lines.extend(_format_mass_estimation(result))
    lines.extend(_format_technology(result))
    lines.extend(_format_geometry(result))
    lines.extend(_format_block_status(result))
    lines.extend(_format_warnings_and_errors(result))

    return "\n".join(lines).rstrip() + "\n"


def _format_header(result: ProjectResult) -> list[str]:
    status = "SUCCESS" if result.success else "FAILED"

    return [
        "Aircraft preliminary design report",
        "=" * 60,
        f"Created at: {_now()}",
        f"Schema version: {result.schema_version}",
        f"Calculation status: {status}",
        "",
    ]


def _format_preliminary_sizing(result: ProjectResult) -> list[str]:
    outputs = _get_block_outputs(result, "preliminary_sizing")

    lines = [
        "1. Предварительные характеристики",
        "-" * 60,
    ]

    if not outputs:
        lines.append("Нет данных.")
        lines.append("")
        return lines

    lines.extend(
        [
            f"Оптимальная нагрузка на крыло p0: {_fmt(outputs.get('p0_optimal'), 'Н/м²')}",
            f"Оптимальная тяговооружённость P0: {_fmt(outputs.get('P0_optimal'))}",
            f"Ограничение по скорости сваливания p0: {_fmt(outputs.get('p0_by_V_s'), 'Н/м²')}",
            f"Ограничение по градиенту набора высоты P0: {_fmt(outputs.get('P0_by_theta'))}",
        ]
    )

    aerodynamics = _as_dict(outputs.get("aerodynamics"))

    if aerodynamics:
        lines.extend(
            [
                "",
                "Аэродинамика:",
                f"  Cx для максимального K: {_fmt(aerodynamics.get('C_x_for_max_K'))}",
                f"  Cy для максимального K: {_fmt(aerodynamics.get('C_y_for_max_K'))}",
                f"  K max: {_fmt(aerodynamics.get('K_max'))}",
            ]
        )

    active_constraints = outputs.get("active_constraints", [])

    if isinstance(active_constraints, list) and active_constraints:
        lines.append("")
        lines.append("Активные ограничения:")

        for item in active_constraints:
            if isinstance(item, dict):
                constraint_id = item.get("id", "-")
                constraint_name = item.get("name", "Без названия")
                lines.append(f"  - [{constraint_id}] {constraint_name}")
            else:
                lines.append(f"  - {item}")

    lines.append("")
    return lines


def _format_mass_estimation(result: ProjectResult) -> list[str]:
    outputs = _get_block_outputs(result, "mass_estimation")

    lines = [
        "2. Оценка масс",
        "-" * 60,
    ]

    if not outputs:
        lines.append("Нет данных.")
        lines.append("")
        return lines

    # Основные данные
    lines.extend(
        [
            f"Тип силовой установки: {_fmt(outputs.get('powerplant_type'))}",
            f"Максимальная взлётная масса m_MTO: {_fmt(outputs.get('m_MTO'), 'кг')}",
            f"Масса пустого самолёта m_OE: {_fmt(outputs.get('m_OE'), 'кг')}",
            f"Масса топлива m_F: {_fmt(outputs.get('m_F'), 'кг')}",
            f"Взлётная тяга T_TO: {_fmt(outputs.get('T_TO'), 'Н')}",
            f"Площадь крыла S_W: {_fmt(outputs.get('S_W'), 'м²')}",
            "",
        ]
    )

    # Информация об итерациях сходимости
    lines.extend(
        [
            "Итерационный расчёт масс:",
            f"  Итерация сошлась: {_fmt(outputs.get('converged'))}",
            f"  Количество затраченных итераций: {_fmt(outputs.get('iterations'))}",
            f"  Отн. невязка нагрузки на крыло: {_fmt(outputs.get('wing_loading_relative_delta'))}",
            "",
        ]
    )

    # Относительные массы (доли)
    mass_ratios = _as_dict(outputs.get("mass_ratios"))
    if mass_ratios or "m_OE_ratio" in outputs:
        lines.append("Относительные массы (доли от m_MTO):")
        lines.append(f"  Пустой самолёт (m_OE_ratio): {_fmt(outputs.get('m_OE_ratio'))}")
        lines.append(f"  Топливо (m_F_ratio): {_fmt(outputs.get('m_F_ratio'))}")

        if mass_ratios.get("battery_mass_ratio"):
            lines.append(f"  АКБ на полёт: {_fmt(mass_ratios.get('battery_mass_ratio'))}")

        lines.append(f"  Полезная/служебная нагрузка: {_fmt(outputs.get('useful_load_ratio'))}")
        lines.append(f"  Конструкция суммарно: {_fmt(outputs.get('structure_mass_ratio'))}")

        if mass_ratios.get("powerplant_mass_ratio"):
            lines.append(f"  Силовая установка: {_fmt(mass_ratios.get('powerplant_mass_ratio'))}")
        if mass_ratios.get("special_equipment_mass_ratio"):
            lines.append(f"  Оборудование СН: {_fmt(mass_ratios.get('special_equipment_mass_ratio'))}")
        lines.append("")

    # Абсолютные массы компонентов
    component_masses = _as_dict(outputs.get("component_masses"))
    if component_masses:
        lines.extend(
            [
                "Массы компонентов:",
                f"  Целевая нагрузка: {_fmt(component_masses.get('payload'), 'кг')}",
                f"  Служебная нагрузка: {_fmt(component_masses.get('service_load'), 'кг')}",
                f"  Топливо: {_fmt(component_masses.get('fuel'), 'кг')}",
            ]
        )
        if component_masses.get('battery_energy'):
            lines.append(f"  АКБ на полёт: {_fmt(component_masses.get('battery_energy'), 'кг')}")
        if component_masses.get('battery_equipment'):
            lines.append(f"  АКБ бортового оборудования: {_fmt(component_masses.get('battery_equipment'), 'кг')}")
        if component_masses.get('control_equipment'):
            lines.append(f"  Оборудование управления: {_fmt(component_masses.get('control_equipment'), 'кг')}")

        lines.extend(
            [
                f"  Крыло: {_fmt(component_masses.get('wing'), 'кг')}",
                f"  Фюзеляж: {_fmt(component_masses.get('fuselage'), 'кг')}",
                f"  Оперение: {_fmt(component_masses.get('tail'), 'кг')}",
                f"  Шасси: {_fmt(component_masses.get('landing_gear'), 'кг')}",
                f"  Силовая установка: {_fmt(component_masses.get('powerplant'), 'кг')}",
                f"  Оборудование СН: {_fmt(component_masses.get('special_equipment'), 'кг')}",
            ]
        )

    lines.append("")
    return lines


def _format_technology(result: ProjectResult) -> list[str]:
    outputs = _get_block_outputs(result, "technology")

    lines = [
        "3. Технологии и экономика",
        "-" * 60,
    ]

    if not outputs:
        lines.append("Нет данных.")
        lines.append("")
        return lines

    combo = _as_dict(outputs.get("best_combination"))
    details = _as_dict(outputs.get("details"))

    def format_combo(c: tuple | list | None) -> str:
        if not c or len(c) != 3:
            return "Нет данных"
        names = {"alum_1": "Алюминий 1", "alum_2": "Алюминий 2", "comp_1": "Композит 1", "comp_2": "Композит 2"}
        return f"Обшивка: {names.get(c[0], c[0])}, Прод. набор: {names.get(c[1], c[1])}, Попер. набор: {names.get(c[2], c[2])}"

    # Помощник для вывода денег в миллионах рублей
    def _fmt_money(val: Any) -> str:
        if val is None:
            return "-"
        try:
            return f"{float(val) / 1_000_000:.2f} млн руб."
        except (ValueError, TypeError):
            return "-"

    lines.extend(
        [
            "Оптимальная комбинация технологий:",
            f"  Крыло: {format_combo(combo.get('wing'))}",
            f"  Фюзеляж: {format_combo(combo.get('fuselage'))}",
            f"  Оперение: {format_combo(combo.get('tail'))}",
            "",
            "Уточнённые параметры (с учётом технологий):",
            f"  Новая взлётная масса m0: {_fmt(details.get('m0_new'), 'кг')}",
            f"  Новая отн. масса крыла: {_fmt(details.get('m_kr_relative'))}",
            f"  Новая отн. масса фюзеляжа: {_fmt(details.get('m_fuse_relative'))}",
            f"  Новая отн. масса оперения: {_fmt(details.get('m_tail_relative'))}",
            "",
            "Экономика всей партии:",
            f"  Стоимость материалов (CLA_I): {_fmt_money(details.get('CLA_I_materials'))}",
            f"  Стоимость станков/оснастки (COSN): {_fmt_money(details.get('COSN_machines'))}",
            f"  Фонд оплаты труда (CTRUD): {_fmt_money(details.get('CTRUD_labor'))}",
            f"  Стоимость площадей (CSPL): {_fmt_money(details.get('CSPL_space'))}",
            f"  СУММАРНАЯ СТОИМОСТЬ ПАРТИИ: {_fmt_money(details.get('CSUM_total'))}",
            "",
            f"СЕБЕСТОИМОСТЬ 1 ЭКЗЕМПЛЯРА (SEB_1): {_fmt_money(outputs.get('best_cost_seb1'))}",
            "",
        ]
    )

    return lines


def _format_geometry(result: ProjectResult) -> list[str]:
    outputs = _get_block_outputs(result, "geometry")

    lines = [
        "4. Геометрия",
        "-" * 60,
    ]

    if not outputs:
        lines.append("Нет данных.")
        lines.append("")
        return lines

    wing = _as_dict(outputs.get("wing"))
    fuselage = _as_dict(outputs.get("fuselage"))
    horizontal_tail = _as_dict(outputs.get("horizontal_tail"))
    vertical_tail = _as_dict(outputs.get("vertical_tail"))

    if wing:
        lines.extend(
            [
                "Крыло:",
                f"  Площадь S: {_fmt(wing.get('S_wing'), 'м²')}",
                f"  Размах l: {_fmt(wing.get('l_wing'), 'м')}",
                f"  Удлинение λ: {_fmt(wing.get('lambda_wing'))}",
                f"  Сужение η: {_fmt(wing.get('eta_wing'))}",
                f"  Корневая хорда b0: {_fmt(wing.get('b0_wing'), 'м')}",
                f"  Концевая хорда bk: {_fmt(wing.get('bk_wing'), 'м')}",
                f"  Стреловидность по 1/4 хорды: {_fmt(wing.get('sweep_wing_quarter'), 'град')}",
                f"  Стреловидность по передней кромке: {_fmt(wing.get('sweep_wing_LE'), 'град')}",
                f"  Схема крыла: {wing.get('wing_scheme_ru', wing.get('wing_scheme', '-'))}",
                "",
            ]
        )

    if fuselage:
        lines.extend(
            [
                "Фюзеляж:",
                f"  Длина L: {_fmt(fuselage.get('L_fuselage'), 'м')}",
                f"  Диаметр d: {_fmt(fuselage.get('d_fuselage'), 'м')}",
                f"  Радиус r: {_fmt(fuselage.get('r_fuselage'), 'м')}",
                f"  Удлинение λ: {_fmt(fuselage.get('lambda_fuselage'))}",
                "",
            ]
        )

    if horizontal_tail:
        lines.extend(
            [
                "Горизонтальное оперение:",
                f"  Площадь S_ht: {_fmt(horizontal_tail.get('S_ht'), 'м²')}",
                f"  Размах l_ht: {_fmt(horizontal_tail.get('l_ht'), 'м')}",
                f"  Корневая хорда b0_ht: {_fmt(horizontal_tail.get('b0_ht'), 'м')}",
                f"  Концевая хорда bk_ht: {_fmt(horizontal_tail.get('bk_ht'), 'м')}",
                f"  Стреловидность по 1/4 хорды: {_fmt(horizontal_tail.get('sweep_horizontal_tail_quarter'), 'град')}",
                f"  Стреловидность по передней кромке: {_fmt(horizontal_tail.get('sweep_ht_LE'), 'град')}",
                "",
            ]
        )

    if vertical_tail:
        lines.extend(
            [
                "Вертикальное оперение:",
                f"  Площадь S_vt: {_fmt(vertical_tail.get('S_vt'), 'м²')}",
                f"  Размах/высота l_vt: {_fmt(vertical_tail.get('l_vt'), 'м')}",
                f"  Корневая хорда b0_vt: {_fmt(vertical_tail.get('b0_vt'), 'м')}",
                f"  Концевая хорда bk_vt: {_fmt(vertical_tail.get('bk_vt'), 'м')}",
                f"  Стреловидность по 1/4 хорды: {_fmt(vertical_tail.get('sweep_vertical_tail_quarter'), 'град')}",
                f"  Стреловидность по передней кромке: {_fmt(vertical_tail.get('sweep_vt_LE'), 'град')}",
                "",
            ]
        )

    return lines


def _format_block_status(result: ProjectResult) -> list[str]:
    lines = [
        "5. Статус расчётных блоков",
        "-" * 60,
    ]

    if not result.block_results:
        lines.append("Расчётные блоки не запускались.")
        lines.append("")
        return lines

    for block_result in result.block_results:
        status = "OK" if block_result.success else "FAILED"
        lines.append(f"{block_result.block_name}: {status}")

        if block_result.warnings:
            for warning in block_result.warnings:
                lines.append(f"  warning: {warning}")

        if block_result.errors:
            for error in block_result.errors:
                lines.append(f"  error: {error}")

    lines.append("")
    return lines


def _format_warnings_and_errors(result: ProjectResult) -> list[str]:
    lines = [
        "6. Предупреждения и ошибки",
        "-" * 60,
    ]

    if not result.warnings and not result.errors:
        lines.append("Нет предупреждений и ошибок.")
        lines.append("")
        return lines

    if result.warnings:
        lines.append("Предупреждения:")
        for warning in result.warnings:
            lines.append(f"  - {warning}")

    if result.errors:
        if result.warnings:
            lines.append("")

        lines.append("Ошибки:")
        for error in result.errors:
            lines.append(f"  - {error}")

    lines.append("")
    return lines


def _get_block_outputs(result: ProjectResult, block_name: str) -> dict[str, Any]:
    for block_result in result.block_results:
        if block_result.block_name == block_name and block_result.success:
            return block_result.outputs

    return {}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _fmt(value: Any, unit: str = "", *, precision: int = 4) -> str:
    if value is None:
        text = "-"

    elif isinstance(value, bool):
        text = "Да" if value else "Нет"

    elif isinstance(value, int):
        text = str(value)

    elif isinstance(value, float):
        abs_value = abs(value)

        if value != 0 and (abs_value >= 1e6 or abs_value < 1e-3):
            text = f"{value:.{precision}e}"
        else:
            text = f"{value:.{precision}f}".rstrip("0").rstrip(".")

    else:
        text = str(value)

    if unit and text != "-":
        return f"{text} {unit}"

    return text


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")