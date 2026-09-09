from __future__ import annotations

from typing import Any, Literal, Dict, Optional, Tuple, List
from pydantic import BaseModel, Field, model_validator, ConfigDict
from aircraft_design.core.errors import InputValidationError

ParameterValueType = Literal["number", "integer", "string", "boolean"]
JsonDict = Dict[str, Any]

class ParameterSpec(BaseModel):
    """
    Описание одного входного параметра.
    """
    # Разрешаем использовать произвольные типы, если потребуется
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    value_type: ParameterValueType
    display_name: str
    description: str
    unit: Optional[str] = None
    required: bool = True
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[Tuple[Any, ...]] = None
    group: Optional[str] = None

    def to_dict(self) -> JsonDict:
        # Pydantic имеет встроенный метод model_dump()
        dump = self.model_dump(exclude_none=False)
        dump["type"] = dump.pop("value_type") # Переименовываем обратно для JSON
        if self.choices is not None:
             dump["choices"] = list(self.choices)
        return dump

    # Вся ручная логика _normalize_number, _normalize_integer и т.д.
    # нам больше не нужна для самой схемы! Pydantic будет валидировать ДАННЫЕ
    # в ProjectInput.
    # Но если нужен этот метод для совместимости со старым кодом:
    def normalize(self, raw_value: Any) -> Any:
        if self.choices is not None and raw_value not in self.choices:
            raise InputValidationError(
                f"{self.name} must be one of {self.choices}. Got: {raw_value!r}"
            )

        if self.value_type == "number":
             if isinstance(raw_value, bool): raise InputValidationError(f"{self.name} must be a number, not boolean.")
             try: value = float(raw_value)
             except (TypeError, ValueError): raise InputValidationError(f"{self.name} must be a number. Got: {raw_value!r}")
        elif self.value_type == "integer":
             if isinstance(raw_value, bool): raise InputValidationError(f"{self.name} must be an integer, not boolean.")
             try:
                 value = float(raw_value)
                 if not value.is_integer(): raise ValueError
                 value = int(value)
             except (TypeError, ValueError): raise InputValidationError(f"{self.name} must be an integer. Got: {raw_value!r}")
        elif self.value_type == "string":
             if not isinstance(raw_value, str): raise InputValidationError(f"{self.name} must be a string. Got: {raw_value!r}")
             value = raw_value
        elif self.value_type == "boolean":
             if not isinstance(raw_value, bool): raise InputValidationError(f"{self.name} must be a boolean. Got: {raw_value!r}")
             value = raw_value
        else:
            raise InputValidationError(f"Unsupported parameter type for {self.name}: {self.value_type}")

        if self.value_type in ("number", "integer"):
            if self.min_value is not None and value < self.min_value:
                raise InputValidationError(f"{self.name} must be >= {self.min_value}. Got: {value}")
            if self.max_value is not None and value > self.max_value:
                raise InputValidationError(f"{self.name} must be <= {self.max_value}. Got: {value}")
        return value

    def template_value(self) -> Any:
        if self.default is not None: return self.default
        if self.value_type == "number": return 0.0
        if self.value_type == "integer": return 0
        if self.value_type == "string": return self.choices[0] if self.choices else ""
        if self.value_type == "boolean": return False
        return None

class BlockInputSchema(BaseModel):
    """
    Description of input section for one calculation block.
    """
    section_name: str
    block_name: str
    display_name: str
    description: str
    parameters: Tuple[ParameterSpec, ...] = Field(default_factory=tuple)

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
            raise InputValidationError(f"Section '{self.section_name}' must be an object.")
        normalized = dict(section)
        for parameter in self.parameters:
            if parameter.name not in normalized or normalized[parameter.name] is None:
                if parameter.required and parameter.default is None:
                    raise InputValidationError(f"Missing required field: {self.section_name}.{parameter.name}")
                if parameter.default is not None:
                    normalized[parameter.name] = parameter.default
                continue
            normalized[parameter.name] = parameter.normalize(normalized[parameter.name])
        return normalized

    def create_template_section(self) -> JsonDict:
        return {parameter.name: parameter.template_value() for parameter in self.parameters}

# Функции normalize_project_input_data, input_schemas_to_dict и create_input_template
# остаются без изменений, так как они работают с API этих классов.
def normalize_project_input_data(data: JsonDict, schemas: List[BlockInputSchema]) -> JsonDict:
    if not isinstance(data, dict): raise InputValidationError("Input JSON root must be an object.")
    normalized = dict(data)
    for schema in schemas:
        section = normalized.get(schema.section_name, {})
        if not isinstance(section, dict): raise InputValidationError(f"Section '{schema.section_name}' must be an object.")
        normalized[schema.section_name] = schema.normalize_section(section)
    return normalized

def input_schemas_to_dict(schemas: List[BlockInputSchema]) -> JsonDict:
    return {
        "schema_format": "aircraft_preliminary_design.input_schema.v1",
        "schema_version": "1.0",
        "sections": [schema.to_dict() for schema in schemas],
    }

def create_input_template(schemas: List[BlockInputSchema]) -> JsonDict:
    template: JsonDict = {
        "schema_version": "1.0",
        "metadata": {"case_name": "example_case", "description": "Generated input template"},
        "aircraft": {"aircraft_type": "business_jet"},
    }
    for schema in schemas: template[schema.section_name] = schema.create_template_section()
    return template