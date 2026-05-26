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
                    unit=parameter.unit,
                    required=parameter.required,
                    default=parameter.default,
                    value=value,
                    min_value=parameter.min_value,
                    max_value=parameter.max_value,
                    choices=list(parameter.choices) if parameter.choices else None,
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

    rows = [
        OutputRowView(
            section="Оценка масс",
            name="m_MTO",
            display_name="Максимальная взлётная масса",
            value=mass.get("m_MTO"),
            unit="кг",
        ),
        OutputRowView(
            section="Оценка масс",
            name="m_OE",
            display_name="Масса пустого самолёта",
            value=mass.get("m_OE"),
            unit="кг",
        ),
        OutputRowView(
            section="Оценка масс",
            name="m_F",
            display_name="Масса топлива",
            value=mass.get("m_F"),
            unit="кг",
        ),
        OutputRowView(
            section="Оценка масс",
            name="m_ML",
            display_name="Максимальная посадочная масса",
            value=mass.get("m_ML"),
            unit="кг",
        ),
        OutputRowView(
            section="Оценка масс",
            name="T_TO",
            display_name="Взлётная тяга",
            value=mass.get("T_TO"),
            unit="Н",
        ),
        OutputRowView(
            section="Оценка масс",
            name="S_W",
            display_name="Площадь крыла",
            value=mass.get("S_W"),
            unit="м²",
        ),
    ]

    component_iteration = _as_dict(mass.get("component_mass_iteration"))

    if component_iteration:
        rows.extend(
            [
                OutputRowView(
                    section="Итерация масс компонентов",
                    name="enabled",
                    display_name="Итерационный расчёт включён",
                    value=component_iteration.get("enabled"),
                ),
                OutputRowView(
                    section="Итерация масс компонентов",
                    name="converged",
                    display_name="Итерация сошлась",
                    value=component_iteration.get("converged"),
                ),
                OutputRowView(
                    section="Итерация масс компонентов",
                    name="iterations",
                    display_name="Количество итераций",
                    value=component_iteration.get("iterations"),
                ),
                OutputRowView(
                    section="Итерация масс компонентов",
                    name="relative_delta",
                    display_name="Последняя относительная разница",
                    value=component_iteration.get("relative_delta"),
                ),
                OutputRowView(
                    section="Итерация масс компонентов",
                    name="final_m0",
                    display_name="Финальная масса по компонентам",
                    value=component_iteration.get("final_m0"),
                    unit="кг",
                ),
            ]
        )

        failure_reason = component_iteration.get("failure_reason")

        if failure_reason:
            rows.append(
                OutputRowView(
                    section="Итерация масс компонентов",
                    name="failure_reason",
                    display_name="Причина остановки",
                    value=failure_reason,
                )
            )

    component_masses = _as_dict(mass.get("component_masses"))

    if component_masses:
        rows.extend(
            [
                OutputRowView(
                    section="Массы компонентов",
                    name="payload",
                    display_name="Полезная нагрузка",
                    value=component_masses.get("payload"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="fuel",
                    display_name="Топливо",
                    value=component_masses.get("fuel"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="wing",
                    display_name="Крыло",
                    value=component_masses.get("wing"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="fuselage",
                    display_name="Фюзеляж",
                    value=component_masses.get("fuselage"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="tail",
                    display_name="Оперение",
                    value=component_masses.get("tail"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="powerplant",
                    display_name="Силовая установка",
                    value=component_masses.get("powerplant"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="landing_gear",
                    display_name="Шасси",
                    value=component_masses.get("landing_gear"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="battery",
                    display_name="АКБ",
                    value=component_masses.get("battery"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="equipment_and_control",
                    display_name="Оборудование и управление",
                    value=component_masses.get("equipment_and_control"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="additional",
                    display_name="Дополнительная масса",
                    value=component_masses.get("additional"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="operating_empty_mass",
                    display_name="Масса пустого самолёта по компонентам",
                    value=component_masses.get("operating_empty_mass"),
                    unit="кг",
                ),
                OutputRowView(
                    section="Массы компонентов",
                    name="total_mass",
                    display_name="Суммарная масса по компонентам",
                    value=component_masses.get("total_mass"),
                    unit="кг",
                ),
            ]
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