from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aircraft_design.app import get_input_schemas
from aircraft_design.core.models import ProjectResult


@dataclass(slots=True)
class InputFieldView:
    """
    UI-friendly representation of one editable input field.
    """

    section_name: str
    name: str
    display_name: str
    value_type: str
    description: str
    unit: str | None = None
    required: bool = True
    default: Any = None
    value: Any = None
    min_value: float | None = None
    max_value: float | None = None
    choices: list[Any] | None = None
    choice_display_names: dict[Any, str] | None = None
    group: str | None = None


@dataclass(slots=True)
class InputSectionView:
    """
    UI-friendly representation of one input section.
    """

    section_name: str
    display_name: str
    description: str
    fields: list[InputFieldView] = field(default_factory=list)


@dataclass(slots=True)
class OutputRowView:
    """
    One row for non-editable output table.
    """

    section: str
    name: str
    display_name: str
    value: Any
    unit: str | None = None


@dataclass(slots=True)
class ChartSeriesView:
    """
    One chart series for the existence/design-space chart.
    """

    name: str
    points: list[tuple[float, float]]


@dataclass(slots=True)
class ExistenceChartView:
    """
    UI-friendly chart data for preliminary sizing constraints.
    """

    series: list[ChartSeriesView] = field(default_factory=list)
    optimal_point: tuple[float, float] | None = None
    p0_by_v_s: float | None = None


_UNIT_DISPLAY_NAMES = {
    "kg": "кг",
    "km": "км",
    "m": "м",
    "m/s": "м/с",
    "m²": "м²",
    "deg": "град",
    "kg/m³": "кг/м³",
    "N": "Н",
    "N/m²": "Н/м²",
    "Wh/kg": "Вт·ч/кг",
    "kW/kg": "кВт/кг",
    "kg/(hp*h)": "кг/(л.с.·ч)",
    "hp": "л.с.",
}

_CHOICE_DISPLAY_NAMES = {
    ("geometry", "wing_scheme", "low"): "Низкоплан",
    ("geometry", "wing_scheme", "mid"): "Среднеплан",
    ("geometry", "wing_scheme", "high"): "Высокоплан",
    ("mass_estimation", "powerplant_type", "electric"): "Электрическая",
    ("mass_estimation", "powerplant_type", "ice"): "ДВС",
    ("mass_estimation", "engine_type", "piston"): "Поршневой",
    ("mass_estimation", "engine_type", "turboprop"): "Турбовинтовой",
    ("mass_estimation", "wing_position", "high"): "Высокоплан",
    ("mass_estimation", "wing_position", "low"): "Низкоплан",
    ("mass_estimation", "landing_gear_material", "medium_steel"): "Сталь средней удельной прочности",
    ("mass_estimation", "landing_gear_material", "high_strength_metal"): "Металл высокой удельной прочности",
    ("mass_estimation", "landing_gear_fairing", "none"): "Нет",
    ("mass_estimation", "landing_gear_fairing", "wheel_fairings"): "На колёса",
    ("mass_estimation", "landing_gear_fairing", "retractable"): "Шасси убирается",
    ("mass_estimation", "landing_gear_type", "ski"): "Лыжное",
    ("mass_estimation", "landing_gear_type", "wheeled"): "Колёсное",
}


def _display_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    return _UNIT_DISPLAY_NAMES.get(unit, unit)


def _display_choice(section_name: str, field_name: str, value: Any) -> Any:
    if value is None:
        return None

    return _CHOICE_DISPLAY_NAMES.get((section_name, field_name, value), value)


def _append_output_row(
    rows: list[OutputRowView],
    *,
    section: str,
    name: str,
    display_name: str,
    value: Any,
    unit: str | None = None,
) -> None:
    if value is None:
        return

    rows.append(
        OutputRowView(
            section=section,
            name=name,
            display_name=display_name,
            value=value,
            unit=unit,
        )
    )


def _choice_display_names(
    section_name: str,
    field_name: str,
    choices: tuple[Any, ...] | None,
) -> dict[Any, str] | None:
    if not choices:
        return None

    labels: dict[Any, str] = {}
    for choice in choices:
        label = _CHOICE_DISPLAY_NAMES.get((section_name, field_name, choice))
        if label is not None:
            labels[choice] = label

    return labels or None


def build_input_table_sections(
    values: dict[str, dict[str, Any]] | None = None,
) -> list[InputSectionView]:
    """
    Build UI input table sections from input schemas.

    Parameters
    ----------
    values:
        Optional current values by section name and parameter name.
        Useful when UI loads a JSON file and needs to populate controls.
    """
    values = values or {}

    sections: list[InputSectionView] = []

    for schema in get_input_schemas():
        section_values = values.get(schema.section_name, {})

        fields: list[InputFieldView] = []

        for parameter in schema.parameters:
            value = section_values.get(parameter.name, parameter.template_value())

            fields.append(
                InputFieldView(
                    section_name=schema.section_name,
                    name=parameter.name,
                    display_name=parameter.display_name,
                    value_type=parameter.value_type,
                    description=parameter.description,
                    unit=_display_unit(parameter.unit),
                    required=parameter.required,
                    default=parameter.default,
                    value=value,
                    min_value=parameter.min_value,
                    max_value=parameter.max_value,
                    choices=list(parameter.choices) if parameter.choices else None,
                    choice_display_names=_choice_display_names(
                        schema.section_name,
                        parameter.name,
                        parameter.choices,
                    ),
                    group=parameter.group,
                )
            )

        sections.append(
            InputSectionView(
                section_name=schema.section_name,
                display_name=schema.display_name,
                description=schema.description,
                fields=fields,
            )
        )

    return sections


def collect_input_sections_from_field_views(
    sections: list[InputSectionView],
) -> dict[str, dict[str, Any]]:
    """
    Convert UI field views back to section dictionaries.

    This function does not validate values. Validation is done later by
    create_project_input_from_sections / run_calculation_from_sections.
    """
    data: dict[str, dict[str, Any]] = {}

    for section in sections:
        data[section.section_name] = {
            field.name: field.value
            for field in section.fields
        }

    return data


def build_output_table_rows(result: ProjectResult) -> list[OutputRowView]:
    """
    Build non-editable output table rows from ProjectResult.
    """
    rows: list[OutputRowView] = []

    outputs = result.outputs

    preliminary = outputs.get("preliminary_sizing", {})
    mass = outputs.get("mass_estimation", {})
    geometry = outputs.get("geometry", {})

    rows.extend(_build_preliminary_rows(preliminary))
    rows.extend(_build_mass_rows(mass))
    rows.extend(_build_geometry_rows(geometry))

    return rows


def build_existence_chart_view(result: ProjectResult) -> ExistenceChartView:
    """
    Build chart data for the preliminary sizing/design-space chart.
    """
    preliminary = result.outputs.get("preliminary_sizing", {})
    chart_data = preliminary.get("chart_data", {})

    series: list[ChartSeriesView] = []

    mapping = {
        "P0_by_theta_points": "Градиент набора высоты",
        "P0_by_n_max_points": "Эксплуатационная перегрузка",
        "P0_by_L_TODA_points": "Взлётная дистанция",
        "P0_by_V_y_points": "Скороподъёмность",
        "P0_by_V_cruise_points": "Крейсерский полёт",
    }

    for key, display_name in mapping.items():
        raw_points = chart_data.get(key, [])
        points = _normalize_points(raw_points)

        if points:
            series.append(
                ChartSeriesView(
                    name=display_name,
                    points=points,
                )
            )

    optimal_point = preliminary.get("optimal_point")
    normalized_optimal_point = None

    if isinstance(optimal_point, list | tuple) and len(optimal_point) == 2:
        normalized_optimal_point = (
            float(optimal_point[0]),
            float(optimal_point[1]),
        )

    p0_by_v_s = preliminary.get("p0_by_V_s")
    normalized_p0_by_v_s = float(p0_by_v_s) if isinstance(p0_by_v_s, int | float) else None

    return ExistenceChartView(
        series=series,
        optimal_point=normalized_optimal_point,
        p0_by_v_s=normalized_p0_by_v_s,
    )


def _build_preliminary_rows(preliminary: dict[str, Any]) -> list[OutputRowView]:
    if not preliminary:
        return []

    return [
        OutputRowView(
            section="Предварительные характеристики",
            name="p0_optimal",
            display_name="Оптимальная нагрузка на крыло",
            value=preliminary.get("p0_optimal"),
            unit="Н/м²",
        ),
        OutputRowView(
            section="Предварительные характеристики",
            name="P0_optimal",
            display_name="Оптимальная тяговооружённость",
            value=preliminary.get("P0_optimal"),
        ),
        OutputRowView(
            section="Предварительные характеристики",
            name="p0_by_V_s",
            display_name="Ограничение по скорости сваливания",
            value=preliminary.get("p0_by_V_s"),
            unit="Н/м²",
        ),
        OutputRowView(
            section="Предварительные характеристики",
            name="P0_by_theta",
            display_name="Ограничение по градиенту набора высоты",
            value=preliminary.get("P0_by_theta"),
        ),
    ]


def _build_mass_rows(mass: dict[str, Any]) -> list[OutputRowView]:
    if not mass:
        return []

    rows: list[OutputRowView] = []

    _append_output_row(
        rows,
        section="Оценка масс",
        name="powerplant_type",
        display_name="Тип силовой установки",
        value=_display_choice("mass_estimation", "powerplant_type", mass.get("powerplant_type")),
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="m_MTO",
        display_name="Максимальная взлётная масса",
        value=mass.get("m_MTO"),
        unit="кг",
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="m_OE",
        display_name="Масса пустого самолёта",
        value=mass.get("m_OE"),
        unit="кг",
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="m_F",
        display_name="Масса топлива",
        value=mass.get("m_F"),
        unit="кг",
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="T_TO",
        display_name="Взлётная тяга",
        value=mass.get("T_TO"),
        unit="Н",
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="S_W",
        display_name="Площадь крыла",
        value=mass.get("S_W"),
        unit="м²",
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="m_OE_ratio",
        display_name="Относительная масса пустого самолёта",
        value=mass.get("m_OE_ratio"),
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="m_F_ratio",
        display_name="Относительная масса топлива",
        value=mass.get("m_F_ratio"),
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="useful_load_ratio",
        display_name="Относительная полезная/служебная нагрузка",
        value=mass.get("useful_load_ratio"),
    )
    _append_output_row(
        rows,
        section="Оценка масс",
        name="structure_mass_ratio",
        display_name="Относительная масса конструкции",
        value=mass.get("structure_mass_ratio"),
    )

    component_iteration = _as_dict(mass.get("component_mass_iteration"))

    if component_iteration:
        rows.extend(
            [
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="converged",
                    display_name="Итерация сошлась",
                    value=component_iteration.get("converged"),
                ),
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="iterations",
                    display_name="Количество итераций",
                    value=component_iteration.get("iterations"),
                ),
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="tolerance",
                    display_name="Допуск по изменению нагрузки на крыло",
                    value=component_iteration.get("tolerance"),
                ),
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="relative_delta_wing_loading",
                    display_name="Последнее изменение нагрузки на крыло",
                    value=component_iteration.get("relative_delta_wing_loading"),
                ),
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="initial_m0",
                    display_name="Масса в первом приближении",
                    value=component_iteration.get("initial_m0"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="final_m0",
                    display_name="Финальная расчётная масса",
                    value=component_iteration.get("final_m0"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="initial_wing_area",
                    display_name="Исходная площадь крыла",
                    value=component_iteration.get("initial_wing_area"),
                    unit="м²",
                ),
                OutputRowView(
                    section="Итерация расчёта масс",
                    name="final_wing_area",
                    display_name="Финальная площадь крыла",
                    value=component_iteration.get("final_wing_area"),
                    unit="м²",
                ),
            ]
        )

        structure_ratios = _as_dict(component_iteration.get("structure_ratios"))
        if structure_ratios:
            rows.extend(
                [
                    OutputRowView(
                        section="Относительные массы конструкции",
                        name="structure_wing_ratio",
                        display_name="Крыло",
                        value=structure_ratios.get("wing"),
                    ),
                    OutputRowView(
                        section="Относительные массы конструкции",
                        name="structure_fuselage_ratio",
                        display_name="Фюзеляж",
                        value=structure_ratios.get("fuselage"),
                    ),
                    OutputRowView(
                        section="Относительные массы конструкции",
                        name="structure_tail_ratio",
                        display_name="Оперение",
                        value=structure_ratios.get("tail"),
                    ),
                    OutputRowView(
                        section="Относительные массы конструкции",
                        name="structure_landing_gear_ratio",
                        display_name="Шасси",
                        value=structure_ratios.get("landing_gear"),
                    ),
                    OutputRowView(
                        section="Относительные массы конструкции",
                        name="structure_total_ratio",
                        display_name="Итого конструкция",
                        value=structure_ratios.get("total"),
                    ),
                ]
            )

    mass_ratios = _as_dict(mass.get("mass_ratios"))

    if mass_ratios:
        ratio_rows = [
            ("battery_mass_ratio", "АКБ на полёт"),
            ("fuel_mass_ratio", "Топливо"),
            ("powerplant_mass_ratio", "Силовая установка"),
            ("special_equipment_mass_ratio", "Оборудование СН"),
            ("operating_empty_mass_ratio", "Пустой самолёт"),
        ]

        for name, display_name in ratio_rows:
            _append_output_row(
                rows,
                section="Относительные массы",
                name=name,
                display_name=display_name,
                value=mass_ratios.get(name),
            )

    component_masses = _as_dict(mass.get("component_masses"))

    if component_masses:
        component_rows = [
            ("payload", "Целевая нагрузка"),
            ("service_load", "Служебная нагрузка"),
            ("fuel", "Топливо"),
            ("battery_energy", "АКБ на полёт"),
            ("battery_equipment", "АКБ бортового оборудования"),
            ("control_equipment", "Оборудование управления"),
            ("wing", "Крыло"),
            ("fuselage", "Фюзеляж"),
            ("tail", "Оперение"),
            ("landing_gear", "Шасси"),
            ("structure", "Конструкция"),
            ("powerplant", "Силовая установка"),
            ("special_equipment", "Оборудование СН"),
            ("operating_empty_mass", "Пустой самолёт по компонентам"),
            ("useful_load_mass", "Целевая + служебная нагрузка"),
            ("total_mass", "Суммарная масса по компонентам"),
        ]

        for name, display_name in component_rows:
            _append_output_row(
                rows,
                section="Массы компонентов",
                name=name,
                display_name=display_name,
                value=component_masses.get(name),
                unit="кг",
            )

    return rows


def _build_geometry_rows(geometry: dict[str, Any]) -> list[OutputRowView]:
    if not geometry:
        return []

    rows: list[OutputRowView] = []

    wing = _as_dict(geometry.get("wing"))
    fuselage = _as_dict(geometry.get("fuselage"))
    horizontal_tail = _as_dict(geometry.get("horizontal_tail"))
    vertical_tail = _as_dict(geometry.get("vertical_tail"))

    if wing:
        rows.extend(
            [
                OutputRowView("Геометрия крыла", "l_wing", "Размах крыла", wing.get("l_wing"), "м"),
                OutputRowView("Геометрия крыла", "b0_wing", "Корневая хорда", wing.get("b0_wing"), "м"),
                OutputRowView("Геометрия крыла", "bk_wing", "Концевая хорда", wing.get("bk_wing"), "м"),
                OutputRowView("Геометрия крыла", "sweep_wing_LE", "Стреловидность по передней кромке", wing.get("sweep_wing_LE"), "град"),
            ]
        )

    if fuselage:
        rows.extend(
            [
                OutputRowView("Геометрия фюзеляжа", "L_fuselage", "Длина фюзеляжа", fuselage.get("L_fuselage"), "м"),
                OutputRowView("Геометрия фюзеляжа", "d_fuselage", "Диаметр фюзеляжа", fuselage.get("d_fuselage"), "м"),
            ]
        )

    if horizontal_tail:
        rows.extend(
            [
                OutputRowView("Геометрия ГО", "S_ht", "Площадь ГО", horizontal_tail.get("S_ht"), "м²"),
                OutputRowView("Геометрия ГО", "l_ht", "Размах ГО", horizontal_tail.get("l_ht"), "м"),
            ]
        )

    if vertical_tail:
        rows.extend(
            [
                OutputRowView("Геометрия ВО", "S_vt", "Площадь ВО", vertical_tail.get("S_vt"), "м²"),
                OutputRowView("Геометрия ВО", "l_vt", "Высота/размах ВО", vertical_tail.get("l_vt"), "м"),
            ]
        )

    return rows


def _normalize_points(raw_points: Any) -> list[tuple[float, float]]:
    if not isinstance(raw_points, list | tuple):
        return []

    points: list[tuple[float, float]] = []

    for point in raw_points:
        if not isinstance(point, list | tuple) or len(point) != 2:
            continue

        x, y = point

        if not isinstance(x, int | float) or not isinstance(y, int | float):
            continue

        points.append((float(x), float(y)))

    return points


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}