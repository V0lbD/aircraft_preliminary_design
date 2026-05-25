from __future__ import annotations

from aircraft_design.app import run_calculation
from aircraft_design.core.blocks import BaseBlock
from aircraft_design.core.models import CalculationState, ProjectInput


class TraceTestBlock(BaseBlock):
    name = "trace_test"

    def calculate(self, state: CalculationState) -> dict:
        x = 2
        y = 3
        z = x + y

        state.add_trace(
            block_name=self.name,
            value_name="z",
            formula="z = x + y",
            values={
                "x": x,
                "y": y,
            },
            result=z,
            unit="-",
            description="Simple trace test.",
        )

        return {"z": z}


def make_project_input() -> ProjectInput:
    return ProjectInput.from_dict(
        {
            "schema_version": "1.0",
            "aircraft": {},
            "preliminary_sizing": {},
            "mass_estimation": {},
            "geometry": {},
        }
    )


def test_trace_records_are_collected() -> None:
    result = run_calculation(
        make_project_input(),
        blocks=[
            TraceTestBlock(),
        ],
        trace_enabled=True,
    )

    assert result.success is True
    assert len(result.trace) == 1

    record = result.trace[0]

    assert record.block_name == "trace_test"
    assert record.value_name == "z"
    assert record.formula == "z = x + y"
    assert record.values == {"x": 2, "y": 3}
    assert record.result == 5
    assert record.unit == "-"


def test_trace_can_be_disabled() -> None:
    result = run_calculation(
        make_project_input(),
        blocks=[
            TraceTestBlock(),
        ],
        trace_enabled=False,
    )

    assert result.success is True
    assert result.trace == []