from __future__ import annotations

from typing import Any

from aircraft_design.core.models.project import ProjectInput

JsonDict = dict[str, Any]


def create_project_input(
    raw_data: JsonDict,
    **kwargs: Any,
) -> ProjectInput:
    """
    Создает ProjectInput из сырого словаря с помощью Pydantic.
    """
    return ProjectInput.model_validate(raw_data)


def create_project_input_from_sections(
    *,
    feasibility: JsonDict,
    preliminary_sizing: JsonDict,
    mass_estimation: JsonDict,
    geometry: JsonDict,
    aircraft: JsonDict | None = None,
    metadata: JsonDict | None = None,
    schema_version: str = "1.0",
    **kwargs: Any,
) -> ProjectInput:
    """
    Склеивает секции в единый словарь и валидирует через Pydantic.
    """
    raw_data: JsonDict = {
        "schema_version": schema_version,
        "metadata": metadata or {},
        "aircraft": aircraft or {},
        "feasibility": feasibility,
        "preliminary_sizing": preliminary_sizing,
        "mass_estimation": mass_estimation,
        "geometry": geometry,
    }

    return ProjectInput.model_validate(raw_data)


def project_input_to_dict(project_input: ProjectInput) -> JsonDict:
    """
    Конвертирует строгую модель обратно в словарь для UI или сохранения.
    """
    return project_input.model_dump()