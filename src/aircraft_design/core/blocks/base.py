from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel

from aircraft_design.core.models import (
    BlockInputSchema,
    BlockResult,
    CalculationState,
)

logger = logging.getLogger(__name__)


class BaseBlock(ABC):
    """
    Базовый класс для всех расчётных блоков.

    Блок ничего не знает о UI, CLI, файлах или Qt.
    Он получает CalculationState и возвращает рассчитанные выходные данные.
    """

    name: str = "base_block"
    required_input_sections: tuple[str, ...] = ()
    input_schema: BlockInputSchema | None = None

    def get_input_schema(self) -> BlockInputSchema | None:
        return self.input_schema

    def validate(self, state: CalculationState) -> None:
        for section_name in self.required_input_sections:
            if not hasattr(state.project_input, section_name):
                raise ValueError(f"Неизвестная входная секция: {section_name}")

            section = getattr(state.project_input, section_name)

            # Секция может быть как словарем (legacy), так и Pydantic-моделью
            if not isinstance(section, (dict, BaseModel)):
                raise ValueError(f"Входная секция '{section_name}' должна быть словарем или BaseModel.")


    def run(self, state: CalculationState) -> BlockResult:
        logger.info("Запуск блока: %s", self.name)

        self.validate(state)
        outputs = self.calculate(state)

        state.data[self.name] = outputs

        logger.info("Блок завершен: %s", self.name)

        return BlockResult(
            block_name=self.name,
            success=True,
            outputs=outputs,
        )

    @abstractmethod
    def calculate(self, state: CalculationState) -> dict:
        """Запуск расчёта блока и возврат словаря с результатами."""