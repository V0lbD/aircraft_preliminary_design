from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aircraft_design.core.models.parameter import Parameter
from aircraft_design.core.models.project import ProjectState


# Маппинг внутренних значений на красивые названия для UI
_CHOICE_DISPLAY_NAMES = {
    ("geometry", "wing_scheme", "low"): "Низкоплан",
    ("geometry", "wing_scheme", "mid"): "Среднеплан",
    ("geometry", "wing_scheme", "high"): "Высокоплан",
    ("feasibility", "powerplant_type", "electric"): "Электрическая",
    ("feasibility", "powerplant_type", "ice"): "ДВС",
    ("feasibility", "powerplant_type", "hybrid"): "Гибридная",
    ("mass", "engine_type", "piston"): "Поршневой",
    ("mass", "engine_type", "turboprop"): "Турбовинтовой",
    ("mass", "wing_position", "high"): "Высокоплан",
    ("mass", "wing_position", "low"): "Низкоплан",
    ("mass", "landing_gear_material", "medium_steel"): "Сталь средней уд. прочности",
    ("mass", "landing_gear_material", "high_strength_metal"): "Металл высокой уд. прочности",
    ("mass", "landing_gear_fairing", "none"): "Нет",
    ("mass", "landing_gear_fairing", "wheel_fairings"): "На колёса",
    ("mass", "landing_gear_fairing", "retractable"): "Убирающееся",
    ("mass", "landing_gear_type", "ski"): "Лыжное",
    ("mass", "landing_gear_type", "wheeled"): "Колёсное",
}


@dataclass(slots=True)
class InputFieldView:
    section_name: str
    name: str
    display_name: str
    value_type: str
    description: str = ""
    unit: str | None = None
    default: Any = None
    value: Any = None
    choices: list[Any] | None = None
    choice_display_names: dict[Any, str] | None = None
    group: str | None = None


@dataclass(slots=True)
class InputSectionView:
    section_name: str
    display_name: str
    description: str = ""
    fields: list[InputFieldView] = field(default_factory=list)


@dataclass(slots=True)
class OutputRowView:
    section: str
    name: str
    display_name: str
    value: Any
    unit: str | None = None
    description: str = ""


@dataclass(slots=True)
class ChartSeriesView:
    name: str
    points: list[tuple[float, float]]


@dataclass(slots=True)
class ExistenceChartView:
    series: list[ChartSeriesView] = field(default_factory=list)
    optimal_point: tuple[float, float] | None = None
    p0_by_v_s: float | None = None


# Маппинг групп данных на человекочитаемые названия
SECTION_NAMES = {
    "feasibility": "Оценка реализуемости",
    "preliminary": "Предварительные характеристики",
    "mass": "Оценка масс",
    "geometry": "Геометрия",
    "technology": "Параметры производства"
}


def _get_parameters_from_group(group_obj: Any) -> list[tuple[str, Parameter]]:
    """Извлекает все объекты Parameter из класса в порядке их объявления."""
    params = []
    cls = group_obj.__class__

    # Используем __dict__ вместо dir(), чтобы сохранить порядок из project.py!
    for attr_name, attr in cls.__dict__.items():
        if isinstance(attr, Parameter):
            params.append((attr_name, attr))

    return params


def build_input_table_sections(project: ProjectState) -> list[InputSectionView]:
    """Генерирует данные для верхней (редактируемой) таблицы UI."""
    sections = []

    for section_key, section_display in SECTION_NAMES.items():
        group_obj = getattr(project, section_key, None)
        if not group_obj: continue

        # Достаем описание из тройных кавычек класса (docstring)
        desc = group_obj.__doc__.strip() if group_obj.__doc__ else ""

        fields = []
        for attr_name, param in _get_parameters_from_group(group_obj):
            if not param.is_input:
                continue  # Берем только входные

            val = getattr(group_obj, attr_name)

            # Определяем тип для UI
            v_type = "number"
            if isinstance(val, bool):
                v_type = "boolean"
            elif isinstance(val, str):
                v_type = "string"

            # Собираем переводы для выпадающего списка
            display_names = None
            if param.choices:
                display_names = {}
                for choice in param.choices:
                    display_names[choice] = _CHOICE_DISPLAY_NAMES.get((section_key, attr_name, choice), str(choice))

            fields.append(InputFieldView(
                section_name=section_key,
                name=attr_name,
                display_name=param.display_name,
                value_type=v_type,
                description=param.description,
                unit=param.unit if param.unit else None,
                default=param.default,
                value=val,
                choices=list(param.choices) if param.choices else None,
                choice_display_names=display_names,
                group=param.category
            ))

        if fields:
            sections.append(InputSectionView(
                section_name=section_key,
                display_name=section_display,
                description=desc,
                fields=fields
            ))

    return sections


def update_project_from_ui(project: ProjectState, ui_sections_data: dict[str, dict[str, Any]]) -> None:
    """Записывает данные из UI-таблицы обратно в ProjectState перед расчетом."""
    for section_key, fields_dict in ui_sections_data.items():
        group_obj = getattr(project, section_key, None)
        if not group_obj: continue

        for field_name, value in fields_dict.items():
            try:
                setattr(group_obj, field_name, value)
            except Exception as e:
                project.add_error(f"Ошибка присвоения UI-параметра [{section_key}.{field_name}]: {e}")


def build_output_table_rows(project: ProjectState) -> list[OutputRowView]:
    """Генерирует данные для нижней (read-only) таблицы UI."""
    rows = []

    for section_key, section_display in SECTION_NAMES.items():
        group_obj = getattr(project, section_key, None)
        if not group_obj: continue

        for attr_name, param in _get_parameters_from_group(group_obj):
            if param.is_input:
                continue  # Берем только выходные

            val = getattr(group_obj, attr_name)
            if val is None: continue

            # Красивый вывод списков в результатах
            if param.choices:
                val = _CHOICE_DISPLAY_NAMES.get((section_key, attr_name, val), val)

            # Округление длинных дробей для красоты
            if isinstance(val, float):
                val = round(val, 4)
            elif not isinstance(val, (int, bool, float)):
                val = str(val)

            rows.append(OutputRowView(
                section=section_display,
                name=attr_name,
                display_name=param.display_name,
                value=val,
                unit=param.unit if param.unit else None,
                description=param.description,
            ))

    return rows


def build_existence_chart_view(project: ProjectState) -> ExistenceChartView:
    """Генерирует данные для графиков ограничений."""
    chart_data = project.databases.get("preliminary_chart_data", {})
    if not chart_data:
        return ExistenceChartView()

    series = []
    mapping = {
        "P0_by_theta_points": "Градиент набора высоты",
        "P0_by_n_max_points": "Эксплуатационная перегрузка",
        "P0_by_L_TODA_points": "Взлётная дистанция",
        "P0_by_V_y_points": "Скороподъёмность",
        "P0_by_V_cruise_points": "Крейсерский полёт",
    }

    for key, display_name in mapping.items():
        points = chart_data.get(key, [])
        if points:
            series.append(ChartSeriesView(name=display_name, points=points))

    return ExistenceChartView(
        series=series,
        optimal_point=chart_data.get("optimal_point"),
        p0_by_v_s=chart_data.get("p0_by_V_s"),
    )