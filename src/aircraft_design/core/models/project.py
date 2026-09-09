from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError

from aircraft_design.core.errors import InputValidationError

from aircraft_design.core.models.technology import TechnologyDatabase

JsonDict = Dict[str, Any]


# --- Заготовки для строгих моделей секций ---
# ConfigDict(extra="allow") позволяет обращаться к ним как к словарям на этапе перехода.
# В будущем сюда нужно будет добавить конкретные поля, например: wing_area: float

class AircraftData(BaseModel):
    """Данные о типе и назначении самолета."""
    model_config = ConfigDict(extra="allow")

class FeasibilityData(BaseModel):
    """Данные для блока оценки реализуемости."""
    model_config = ConfigDict(extra="allow")
    

class PreliminarySizingData(BaseModel):
    """Данные для блока предварительного расчета."""
    model_config = ConfigDict(extra="allow")


class MassEstimationData(BaseModel):
    """Данные для блока расчета масс."""
    model_config = ConfigDict(extra="allow")


class GeometryData(BaseModel):
    """Данные для блока расчета геометрии."""
    model_config = ConfigDict(extra="allow")


class Metadata(BaseModel):
    """Метаданные проекта (название, описание и т.д.)."""
    NLA: float = Field(default=100.0, description="Количество ЛА в партии")
    T: float = Field(default=50.0, description="Срок выполнения заказа в неделях")
    model_config = ConfigDict(extra="allow")


class ProjectInput(BaseModel):
    """
    Полные входные данные для одного расчета предварительного проектирования самолета.
    """
    schema_version: str
    aircraft: AircraftData = Field(default_factory=AircraftData)
    feasibility: FeasibilityData = Field(default_factory=FeasibilityData)
    preliminary_sizing: PreliminarySizingData = Field(default_factory=PreliminarySizingData)
    mass_estimation: MassEstimationData = Field(default_factory=MassEstimationData)
    geometry: GeometryData = Field(default_factory=GeometryData)
    metadata: Metadata = Field(default_factory=Metadata)
    technology_db: TechnologyDatabase | None = Field(default=None, exclude=True)

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"Неподдерживаемая версия схемы: {v}. Ожидается: 1.0.")
        return v

    @classmethod
    def from_dict(cls, data: JsonDict) -> "ProjectInput":
        """
        Создает объект ProjectInput из словаря.
        Сохранено для обратной совместимости с существующим кодом загрузчиков.
        """
        if not isinstance(data, dict):
            raise InputValidationError("Корневой элемент JSON должен быть объектом.")

        try:
            return cls.model_validate(data)
        except ValidationError as e:
            # Перехватываем ошибки Pydantic и отдаем вашу кастомную ошибку
            raise InputValidationError(f"Ошибка валидации входных данных: {e}")


class CalculationTraceRecord(BaseModel):
    """
    Одна запись трассировки, объясняющая, как было получено важное расчетное значение.
    """
    block_name: str
    value_name: str
    formula: str
    values: JsonDict = Field(default_factory=dict)
    result: Any = None
    unit: Optional[str] = None
    description: Optional[str] = None


class CalculationTrace(BaseModel):
    """
    Накопитель трассировки расчетов.
    Блоки должны добавлять записи сюда вместо прямого логирования формул.
    """
    enabled: bool = True
    records: List[CalculationTraceRecord] = Field(default_factory=list)

    def add(
            self,
            *,
            block_name: str,
            value_name: str,
            formula: str,
            values: Optional[JsonDict] = None,
            result: Any = None,
            unit: Optional[str] = None,
            description: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return

        self.records.append(
            CalculationTraceRecord(
                block_name=block_name,
                value_name=value_name,
                formula=formula,
                values=values or {},
                result=result,
                unit=unit,
                description=description,
            )
        )


class CalculationState(BaseModel):
    """
    Изменяемое состояние расчета, общее для всех блоков в течение одного запуска.
    """
    project_input: ProjectInput
    data: JsonDict = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    trace: CalculationTrace = Field(default_factory=CalculationTrace)

    def add_trace(
            self,
            *,
            block_name: str,
            value_name: str,
            formula: str,
            values: Optional[JsonDict] = None,
            result: Any = None,
            unit: Optional[str] = None,
            description: Optional[str] = None,
    ) -> None:
        self.trace.add(
            block_name=block_name,
            value_name=value_name,
            formula=formula,
            values=values,
            result=result,
            unit=unit,
            description=description,
        )


class BlockResult(BaseModel):
    """
    Результат выполнения одного расчетного блока.
    """
    block_name: str
    success: bool
    outputs: JsonDict = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ProjectResult(BaseModel):
    """
    Итоговый результат выполнения всего проекта.
    """
    schema_version: str
    success: bool = True
    block_results: List[BlockResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    trace: List[CalculationTraceRecord] = Field(default_factory=list)

    @property
    def outputs(self) -> JsonDict:
        return {
            block_result.block_name: block_result.outputs
            for block_result in self.block_results
            if block_result.success
        }