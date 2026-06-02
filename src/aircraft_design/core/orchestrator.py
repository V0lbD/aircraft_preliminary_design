from __future__ import annotations

import logging

from aircraft_design.core.blocks import BaseBlock
from aircraft_design.core.errors import AircraftDesignError, BlockCalculationError
from aircraft_design.core.models import (
    BlockResult,
    CalculationState,
    CalculationTrace,
    CalculationTraceRecord,
    ProjectInput,
    ProjectResult,
)

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

    def run(
        self,
        project_input: ProjectInput,
        *,
        trace_enabled: bool = True,
    ) -> ProjectResult:
        logger.info("Calculation started")

        state = CalculationState(
            project_input=project_input,
            trace=CalculationTrace(enabled=trace_enabled),
        )
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

                result.block_results.append(block_result)

                if self.stop_on_error:
                    logger.error("Stopping calculation after block failure: %s", block.name)
                    break

                continue

            except Exception as exc:
                wrapped_error = BlockCalculationError(
                    f"Unexpected error in block '{block.name}': {exc}"
                )
                block_result = self._make_failed_block_result(block.name, wrapped_error)
                result.success = False
                result.errors.append(str(wrapped_error))

                result.block_results.append(block_result)

                if self.stop_on_error:
                    logger.exception("Stopping calculation after unexpected block failure")
                    break

                continue

            result.block_results.append(block_result)

        result.warnings.extend(state.warnings)
        result.trace = list(state.trace.records)

        if trace_enabled and logger.isEnabledFor(logging.DEBUG):
            self._log_trace_records(result.trace)

        logger.info("Calculation finished. Success: %s", result.success)
        return result

    @staticmethod
    def _make_failed_block_result(block_name: str, error: Exception) -> BlockResult:
        return BlockResult(
            block_name=block_name,
            success=False,
            errors=[str(error)],
        )

    @staticmethod
    def _log_trace_records(records: list[CalculationTraceRecord]) -> None:
        if not records:
            logger.debug("Calculation trace is empty")
            return

        logger.debug("Calculation trace records: %s", len(records))

        for record in records:
            unit = f" {record.unit}" if record.unit else ""

            logger.debug(
                "TRACE | %s | %s = %s%s | formula: %s | values: %s",
                record.block_name,
                record.value_name,
                record.result,
                unit,
                record.formula,
                record.values,
            )