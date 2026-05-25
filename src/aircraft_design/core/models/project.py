from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aircraft_design.core.errors import InputValidationError

JsonDict = dict[str, Any]


@dataclass(slots=True)
class ProjectInput:
    """
    Full input data for one aircraft preliminary design calculation.

    For now, sections are intentionally stored as dictionaries.
    Later we will replace them with stricter typed models.
    """

    schema_version: str
    aircraft: JsonDict = field(default_factory=dict)
    preliminary_sizing: JsonDict = field(default_factory=dict)
    mass_estimation: JsonDict = field(default_factory=dict)
    geometry: JsonDict = field(default_factory=dict)
    metadata: JsonDict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ProjectInput":
        if not isinstance(data, dict):
            raise InputValidationError("Input JSON root must be an object.")

        schema_version = data.get("schema_version")
        if not isinstance(schema_version, str):
            raise InputValidationError("Missing or invalid field: schema_version.")

        if schema_version != "1.0":
            raise InputValidationError(
                f"Unsupported schema_version: {schema_version}. Expected: 1.0."
            )

        required_sections = [
            "aircraft",
            "preliminary_sizing",
            "mass_estimation",
            "geometry",
        ]

        for section in required_sections:
            if section not in data:
                raise InputValidationError(f"Missing required section: {section}.")
            if not isinstance(data[section], dict):
                raise InputValidationError(f"Section '{section}' must be an object.")

        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            raise InputValidationError("Section 'metadata' must be an object.")

        return cls(
            schema_version=schema_version,
            aircraft=data["aircraft"],
            preliminary_sizing=data["preliminary_sizing"],
            mass_estimation=data["mass_estimation"],
            geometry=data["geometry"],
            metadata=metadata,
        )


@dataclass(slots=True)
class CalculationState:
    """
    Mutable calculation state shared between blocks during one run.
    """

    project_input: ProjectInput
    data: JsonDict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BlockResult:
    block_name: str
    success: bool
    outputs: JsonDict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectResult:
    schema_version: str
    success: bool = True
    block_results: list[BlockResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def outputs(self) -> JsonDict:
        return {
            block_result.block_name: block_result.outputs
            for block_result in self.block_results
            if block_result.success
        }