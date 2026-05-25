from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from aircraft_design.core.errors import InputValidationError

ParameterValueType = Literal["number", "integer", "string", "boolean"]

JsonDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """
    Description of one input parameter.
    """

    name: str
    value_type: ParameterValueType
    display_name: str
    description: str
    unit: str | None = None
    required: bool = True
    default: Any = None
    min_value: float | None = None
    max_value: float | None = None
    choices: tuple[Any, ...] | None = None
    group: str | None = None

    def to_dict(self) -> JsonDict:
        return {
            "name": self.name,
            "type": self.value_type,
            "display_name": self.display_name,
            "description": self.description,
            "unit": self.unit,
            "required": self.required,
            "default": self.default,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "choices": list(self.choices) if self.choices is not None else None,
            "group": self.group,
        }

    def normalize(self, raw_value: Any) -> Any:
        if self.choices is not None and raw_value not in self.choices:
            raise InputValidationError(
                f"{self.name} must be one of {self.choices}. Got: {raw_value!r}"
            )

        if self.value_type == "number":
            value = self._normalize_number(raw_value)
        elif self.value_type == "integer":
            value = self._normalize_integer(raw_value)
        elif self.value_type == "string":
            value = self._normalize_string(raw_value)
        elif self.value_type == "boolean":
            value = self._normalize_boolean(raw_value)
        else:
            raise InputValidationError(
                f"Unsupported parameter type for {self.name}: {self.value_type}"
            )

        self._validate_range(value)
        return value

    def template_value(self) -> Any:
        if self.default is not None:
            return self.default

        if self.value_type == "number":
            return 0.0

        if self.value_type == "integer":
            return 0

        if self.value_type == "string":
            if self.choices:
                return self.choices[0]
            return ""

        if self.value_type == "boolean":
            return False

        return None

    def _normalize_number(self, raw_value: Any) -> float:
        if isinstance(raw_value, bool):
            raise InputValidationError(f"{self.name} must be a number, not boolean.")

        try:
            return float(raw_value)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(
                f"{self.name} must be a number. Got: {raw_value!r}"
            ) from exc

    def _normalize_integer(self, raw_value: Any) -> int:
        if isinstance(raw_value, bool):
            raise InputValidationError(f"{self.name} must be an integer, not boolean.")

        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(
                f"{self.name} must be an integer. Got: {raw_value!r}"
            ) from exc

        if not value.is_integer():
            raise InputValidationError(
                f"{self.name} must be an integer. Got: {raw_value!r}"
            )

        return int(value)

    def _normalize_string(self, raw_value: Any) -> str:
        if not isinstance(raw_value, str):
            raise InputValidationError(
                f"{self.name} must be a string. Got: {raw_value!r}"
            )

        return raw_value

    def _normalize_boolean(self, raw_value: Any) -> bool:
        if not isinstance(raw_value, bool):
            raise InputValidationError(
                f"{self.name} must be a boolean. Got: {raw_value!r}"
            )

        return raw_value

    def _validate_range(self, value: Any) -> None:
        if self.value_type not in ("number", "integer"):
            return

        if self.min_value is not None and value < self.min_value:
            raise InputValidationError(
                f"{self.name} must be >= {self.min_value}. Got: {value}"
            )

        if self.max_value is not None and value > self.max_value:
            raise InputValidationError(
                f"{self.name} must be <= {self.max_value}. Got: {value}"
            )


@dataclass(frozen=True, slots=True)
class BlockInputSchema:
    """
    Description of input section for one calculation block.
    """

    section_name: str
    block_name: str
    display_name: str
    description: str
    parameters: tuple[ParameterSpec, ...] = field(default_factory=tuple)

    def to_dict(self) -> JsonDict:
        return {
            "section_name": self.section_name,
            "block_name": self.block_name,
            "display_name": self.display_name,
            "description": self.description,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
        }

    def normalize_section(self, section: JsonDict) -> JsonDict:
        if not isinstance(section, dict):
            raise InputValidationError(
                f"Section '{self.section_name}' must be an object."
            )

        normalized = dict(section)

        for parameter in self.parameters:
            if parameter.name not in normalized or normalized[parameter.name] is None:
                if parameter.required and parameter.default is None:
                    raise InputValidationError(
                        f"Missing required field: {self.section_name}.{parameter.name}"
                    )

                if parameter.default is not None:
                    normalized[parameter.name] = parameter.default

                continue

            normalized[parameter.name] = parameter.normalize(normalized[parameter.name])

        return normalized

    def create_template_section(self) -> JsonDict:
        return {
            parameter.name: parameter.template_value()
            for parameter in self.parameters
        }


def normalize_project_input_data(
    data: JsonDict,
    schemas: list[BlockInputSchema],
) -> JsonDict:
    """
    Normalize project input data using block input schemas.
    """
    if not isinstance(data, dict):
        raise InputValidationError("Input JSON root must be an object.")

    normalized = dict(data)

    for schema in schemas:
        section = normalized.get(schema.section_name)

        if section is None:
            section = {}

        if not isinstance(section, dict):
            raise InputValidationError(
                f"Section '{schema.section_name}' must be an object."
            )

        normalized[schema.section_name] = schema.normalize_section(section)

    return normalized


def input_schemas_to_dict(schemas: list[BlockInputSchema]) -> JsonDict:
    return {
        "schema_format": "aircraft_preliminary_design.input_schema.v1",
        "schema_version": "1.0",
        "sections": [schema.to_dict() for schema in schemas],
    }


def create_input_template(schemas: list[BlockInputSchema]) -> JsonDict:
    template: JsonDict = {
        "schema_version": "1.0",
        "metadata": {
            "case_name": "example_case",
            "description": "Generated input template",
        },
        "aircraft": {
            "aircraft_type": "business_jet",
        },
    }

    for schema in schemas:
        template[schema.section_name] = schema.create_template_section()

    return template