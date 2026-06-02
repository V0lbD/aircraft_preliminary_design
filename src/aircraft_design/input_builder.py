from __future__ import annotations

from typing import Any

from aircraft_design.core.models import (
    BlockInputSchema,
    ProjectInput,
    normalize_project_input_data,
)
from aircraft_design.core.pipeline import get_default_input_schemas

JsonDict = dict[str, Any]


def create_project_input(
    raw_data: JsonDict,
    *,
    schemas: list[BlockInputSchema] | None = None,
) -> ProjectInput:
    """
    Create ProjectInput from raw nested dictionary.

    This function is the common entry point for:
    - JSON input;
    - UI input;
    - tests;
    - future API usage.

    It applies:
    - defaults;
    - required field validation;
    - type validation;
    - min/max validation;
    - choices validation.
    """
    selected_schemas = schemas if schemas is not None else get_default_input_schemas()

    normalized_data = normalize_project_input_data(
        raw_data,
        schemas=selected_schemas,
    )

    return ProjectInput.from_dict(normalized_data)


def create_project_input_from_sections(
    *,
    preliminary_sizing: JsonDict,
    mass_estimation: JsonDict,
    geometry: JsonDict,
    aircraft: JsonDict | None = None,
    metadata: JsonDict | None = None,
    schema_version: str = "1.0",
    schemas: list[BlockInputSchema] | None = None,
) -> ProjectInput:
    """
    Create ProjectInput from already separated input sections.

    This is the most convenient function for UI:
    each UI tab/table can produce its own dictionary.
    """
    raw_data: JsonDict = {
        "schema_version": schema_version,
        "metadata": metadata or {},
        "aircraft": aircraft or {},
        "preliminary_sizing": preliminary_sizing,
        "mass_estimation": mass_estimation,
        "geometry": geometry,
    }

    return create_project_input(
        raw_data,
        schemas=schemas,
    )


def project_input_to_dict(project_input: ProjectInput) -> JsonDict:
    """
    Convert ProjectInput back to JSON-compatible dictionary.

    Useful for saving edited UI input data to input JSON file.
    """
    return {
        "schema_version": project_input.schema_version,
        "metadata": dict(project_input.metadata),
        "aircraft": dict(project_input.aircraft),
        "preliminary_sizing": dict(project_input.preliminary_sizing),
        "mass_estimation": dict(project_input.mass_estimation),
        "geometry": dict(project_input.geometry),
    }