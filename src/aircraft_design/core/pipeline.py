from __future__ import annotations

from aircraft_design.core.blocks import (
    BaseBlock,
    GeometryBlock,
    MassEstimationBlock,
    PreliminarySizingBlock,
)
from aircraft_design.core.models import BlockInputSchema


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


def get_default_input_schemas() -> list[BlockInputSchema]:
    schemas: list[BlockInputSchema] = []

    for block in create_default_blocks():
        schema = block.get_input_schema()
        if schema is not None:
            schemas.append(schema)

    return schemas