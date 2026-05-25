from __future__ import annotations

import logging
from collections.abc import Sequence

from aircraft_design.core.blocks import BaseBlock
from aircraft_design.core.models import BlockInputSchema, ProjectInput, ProjectResult
from aircraft_design.core.orchestrator import Orchestrator
from aircraft_design.core.pipeline import create_default_blocks, get_default_input_schemas

logger = logging.getLogger(__name__)


def create_orchestrator(
    blocks: Sequence[BaseBlock] | None = None,
    *,
    stop_on_error: bool = True,
) -> Orchestrator:
    """
    Create an orchestrator.

    If no blocks are provided, the default full calculation pipeline is used.
    """
    selected_blocks = list(blocks) if blocks is not None else create_default_blocks()

    logger.debug(
        "Creating orchestrator with blocks: %s",
        [block.name for block in selected_blocks],
    )

    return Orchestrator(
        blocks=selected_blocks,
        stop_on_error=stop_on_error,
    )


def run_calculation(
    project_input: ProjectInput,
    *,
    blocks: Sequence[BaseBlock] | None = None,
    stop_on_error: bool = True,
    trace_enabled: bool = True,
) -> ProjectResult:
    """
    Run aircraft preliminary design calculation.

    CLI, UI and tests should use this function instead of creating
    Orchestrator directly.
    """
    logger.info("Running aircraft preliminary design calculation")

    orchestrator = create_orchestrator(
        blocks=blocks,
        stop_on_error=stop_on_error,
    )

    result = orchestrator.run(
        project_input,
        trace_enabled=trace_enabled,
    )

    logger.info("Application calculation finished. Success: %s", result.success)

    return result


def get_input_schemas() -> list[BlockInputSchema]:
    """
    Return input schemas for the default calculation pipeline.
    """
    return get_default_input_schemas()