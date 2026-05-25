from __future__ import annotations

import logging

from aircraft_design.core.blocks import BaseBlock
from aircraft_design.core.errors import AircraftDesignError, BlockCalculationError
from aircraft_design.core.models import BlockResult, CalculationState, ProjectInput, ProjectResult

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Runs calculation blocks in a fixed order.
    """

    def __init__(
        self,
        blocks: list[BaseBlock] | None = None,
        stop_on_error: bool = True,
    ) -> None:
        self.blocks = blocks or []
        self.stop_on_error = stop_on_error

    def run(self, project_input: ProjectInput) -> ProjectResult:
        logger.info("Calculation started")

        state = CalculationState(project_input=project_input)
        result = ProjectResult(schema_version=project_input.schema_version)

        if not self.blocks:
            warning = "No calculation blocks configured yet."
            logger.warning(warning)
            result.warnings.append(warning)

        for block in self.blocks:
            try:
                block_result = block.run(state)

            except AircraftDesignError as exc:
                block_result = self._make_failed_block_result(block.name, exc)
                result.success = False
                result.errors.append(str(exc))

                if self.stop_on_error:
                    result.block_results.append(block_result)
                    logger.error("Stopping calculation after block failure: %s", block.name)
                    break

            except Exception as exc:
                wrapped_error = BlockCalculationError(
                    f"Unexpected error in block '{block.name}': {exc}"
                )
                block_result = self._make_failed_block_result(block.name, wrapped_error)
                result.success = False
                result.errors.append(str(wrapped_error))

                if self.stop_on_error:
                    result.block_results.append(block_result)
                    logger.exception("Stopping calculation after unexpected block failure")
                    break

            result.block_results.append(block_result)

        logger.info("Calculation finished. Success: %s", result.success)
        return result

    @staticmethod
    def _make_failed_block_result(block_name: str, error: Exception) -> BlockResult:
        return BlockResult(
            block_name=block_name,
            success=False,
            errors=[str(error)],
        )