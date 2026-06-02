from __future__ import annotations

import json

from aircraft_design.core.models import BlockResult, CalculationTraceRecord, ProjectResult
from aircraft_design.io.json_writer import (
    format_json_result,
    project_result_to_dict,
    write_json_result,
)


def test_project_result_to_dict_contains_full_machine_readable_result() -> None:
    result = ProjectResult(
        schema_version="1.0",
        success=True,
        block_results=[
            BlockResult(
                block_name="preliminary_sizing",
                success=True,
                outputs={
                    "p0_optimal": 1234.5,
                    "chart_data": {
                        "points": [[1, 2], [3, 4]],
                    },
                },
            )
        ],
    )

    data = project_result_to_dict(result)

    assert data["result_format"] == "aircraft_preliminary_design.result.v1"
    assert data["schema_version"] == "1.0"
    assert data["success"] is True

    assert data["block_results"][0]["block_name"] == "preliminary_sizing"
    assert data["block_results"][0]["outputs"]["chart_data"]["points"] == [
        [1, 2],
        [3, 4],
    ]

    assert data["outputs"]["preliminary_sizing"]["p0_optimal"] == 1234.5


def test_format_json_result_returns_valid_json() -> None:
    result = ProjectResult(
        schema_version="1.0",
        success=True,
        block_results=[],
    )

    text = format_json_result(result)
    data = json.loads(text)

    assert data["result_format"] == "aircraft_preliminary_design.result.v1"
    assert data["success"] is True


def test_write_json_result_creates_file(tmp_path) -> None:
    result = ProjectResult(
        schema_version="1.0",
        success=True,
        block_results=[
            BlockResult(
                block_name="geometry",
                success=True,
                outputs={
                    "wing": {
                        "S_wing": 32.5,
                    }
                },
            )
        ],
    )

    output_path = tmp_path / "result.json"

    write_json_result(result, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["outputs"]["geometry"]["wing"]["S_wing"] == 32.5


def test_json_result_contains_trace() -> None:
    result = ProjectResult(
        schema_version="1.0",
        success=True,
        block_results=[],
        trace=[
            CalculationTraceRecord(
                block_name="mass_estimation",
                value_name="S_W",
                formula="S_W = (m_MTO * g) / p0_optimal",
                values={
                    "m_MTO": 8000.0,
                    "g": 9.80665,
                    "p0_optimal": 2450.0,
                },
                result=32.02,
                unit="m²",
            )
        ],
    )

    text = format_json_result(result)
    data = json.loads(text)

    assert data["trace"][0]["block_name"] == "mass_estimation"
    assert data["trace"][0]["value_name"] == "S_W"
    assert data["trace"][0]["unit"] == "m²"