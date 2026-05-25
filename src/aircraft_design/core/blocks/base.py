from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from aircraft_design.core.models import BlockResult, CalculationState

logger = logging.getLogger(__name__)


class BaseBlock(ABC):
    """
    Base class for all calculation blocks.

    A block must not know anything about UI, CLI, files or Qt.
    It receives CalculationState and returns calculated outputs.
    """

    name: str = "base_block"
    required_input_sections: tuple[str, ...] = ()

    def validate(self, state: CalculationState) -> None:
        for section_name in self.required_input_sections:
            if not hasattr(state.project_input, section_name):
                raise ValueError(f"Unknown input section: {section_name}")

            section = getattr(state.project_input, section_name)
            if not isinstance(section, dict):
                raise ValueError(f"Input section '{section_name}' must be a dictionary.")

    def run(self, state: CalculationState) -> BlockResult:
        logger.info("Starting block: %s", self.name)

        self.validate(state)
        outputs = self.calculate(state)

        state.data[self.name] = outputs

        logger.info("Finished block: %s", self.name)

        return BlockResult(
            block_name=self.name,
            success=True,
            outputs=outputs,
        )

    @abstractmethod
    def calculate(self, state: CalculationState) -> dict:
        """Run block calculation and return output dictionary."""