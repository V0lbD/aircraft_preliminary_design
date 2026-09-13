from __future__ import annotations

import logging
from typing import Sequence

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.models.project import ProjectState
from aircraft_design.core.orchestrator import Orchestrator
from aircraft_design.core.pipeline import create_default_blocks

logger = logging.getLogger(__name__)

def create_orchestrator(
    blocks: Sequence[BaseBlock] | None = None,
    *,
    stop_on_error: bool = True,
) -> Orchestrator:
    selected_blocks = list(blocks) if blocks is not None else create_default_blocks()
    return Orchestrator(blocks=selected_blocks, stop_on_error=stop_on_error)

def run_calculation(
    project: ProjectState,
    *,
    blocks: Sequence[BaseBlock] | None = None,
    stop_on_error: bool = True,
) -> bool:
    """
    Запускает конвейер расчетов. Возвращает True, если расчет успешен.
    """
    logger.info("Running aircraft preliminary design calculation")
    orchestrator = create_orchestrator(blocks=blocks, stop_on_error=stop_on_error)
    return orchestrator.run(project)