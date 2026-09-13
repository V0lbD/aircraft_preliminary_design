from __future__ import annotations

from aircraft_design.core.blocks import (
    BaseBlock,
    GeometryBlock,
    MassEstimationBlock,
    PreliminarySizingBlock,
    TechnologyBlock,
    FeasibilityBlock,
)

# Очередь выполнения. Порядок критически важен!
DEFAULT_BLOCK_CLASSES: tuple[type[BaseBlock], ...] = (
    FeasibilityBlock,
    PreliminarySizingBlock,
    MassEstimationBlock,
    TechnologyBlock,
    GeometryBlock,
)


def create_default_blocks() -> list[BaseBlock]:
    """
    Создает инстансы расчетных блоков для стандартного конвейера.
    """
    return [block_class() for block_class in DEFAULT_BLOCK_CLASSES]