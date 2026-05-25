from __future__ import annotations

import logging
from collections.abc import Sequence

from aircraft_design.core.blocks import (
    BaseBlock,
    GeometryBlock,
    MassEstimationBlock,
    PreliminarySizingBlock,
)
from aircraft_design.core.models import ProjectInput, ProjectResult
from aircraft_design.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


DEFAULT_BLOCK_CLASSES: tuple[type[BaseBlock], ...] = (
    PreliminarySizingBlock,
    MassEstimationBlock,
    GeometryBlock,
)


def create_default_blocks() -> list[BaseBlock]:
    """
    Create calculation blocks for the default full calculation pipeline.

    The order is important:

    1. preliminary_sizing
    2. mass_estimation
    3. geometry
    """
    return [block_class() for block_class in DEFAULT_BLOCK_CLASSES]


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

    This is the main application-level entry point.
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