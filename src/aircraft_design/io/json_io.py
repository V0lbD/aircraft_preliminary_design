import json
import numpy as np

from pathlib import Path
from typing import Any

from aircraft_design.core.models.project import ProjectState
from aircraft_design.core.models.parameter import Parameter


def _get_parameters_from_group(group_obj: Any) -> list[tuple[str, Parameter]]:
    """Извлекает все объекты Parameter из класса в порядке их объявления."""
    params = []
    cls = group_obj.__class__

    # Используем __dict__ вместо dir(), чтобы сохранить порядок из project.py!
    for attr_name, attr in cls.__dict__.items():
        if isinstance(attr, Parameter):
            params.append((attr_name, attr))

    return params


def _normalize_value(val: Any) -> Any:
    """Очищает типы numpy для корректной записи в JSON."""
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        return float(val)
    return val


def save_project_to_json(project: ProjectState, file_path: str | Path) -> None:
    """Сериализует текущее состояние проекта в JSON."""
    data = {"schema_version": project.schema_version}

    groups = ["feasibility", "preliminary", "mass", "geometry", "technology"]

    for group_name in groups:
        group_obj = getattr(project, group_name, None)
        if not group_obj: continue

        group_data = {}
        for attr_name, _ in _get_parameters_from_group(group_obj):
            val = getattr(group_obj, attr_name)
            if not isinstance(val, (list, tuple, dict)):
                group_data[attr_name] = _normalize_value(val)

        data[group_name] = group_data

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")


def load_project_from_json(project: ProjectState, file_path: str | Path) -> None:
    """Загружает данные из JSON в существующий объект проекта (строгий режим)."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Ошибка чтения JSON файла {path.name}:\n{e}")

    groups = ["feasibility", "preliminary", "mass", "geometry", "technology"]

    for group_name in groups:
        if group_name not in data: continue
        group_obj = getattr(project, group_name, None)
        if not group_obj: continue

        for attr_name, value in data[group_name].items():
            try:
                setattr(group_obj, attr_name, value)
            except Exception as e:
                project.add_error(f"Ошибка загрузки параметра {group_name}.{attr_name}: {e}")


def create_input_template(project: ProjectState) -> dict[str, Any]:
    """Генерирует JSON-шаблон со всеми входными параметрами и их значениями по умолчанию."""
    data = {
        "schema_version": project.schema_version,
        "aircraft": {"aircraft_type": "business_jet"},
        "metadata": {"source": "template"}
    }

    groups = ["feasibility", "preliminary", "mass", "geometry", "technology"]

    for group_name in groups:
        group_obj = getattr(project, group_name, None)
        if not group_obj: continue

        group_data = {}
        for attr_name, param in _get_parameters_from_group(group_obj):
            if param.is_input:
                group_data[attr_name] = param.default

        if group_data:
            data[group_name] = group_data

    return data