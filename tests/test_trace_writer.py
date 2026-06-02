from __future__ import annotations

import json

from aircraft_design.core.models import CalculationTraceRecord, ProjectResult
from aircraft_design.io.trace_writer import (
    format_trace_json,
    format_trace_markdown,
    write_trace_json,
    write_trace_markdown,
)


def make_result_with_trace() -> ProjectResult:
    return ProjectResult(
        schema_version="1.0",
        success=True,
        trace=[
            CalculationTraceRecord(
                block_name="mass_estimation",
                value_name="S_W",
                formula="S_W = m_MTO / p0_optimal",
                values={
                    "m_MTO": 10000.0,
                    "p0_optimal": 500.0,
                },
                result=20.0,
                unit="m²",
                description="Wing area from takeoff mass and wing loading.",
            ),
            CalculationTraceRecord(
                block_name="mass_estimation",
                value_name="m_F",
                formula="m_F = m_MTO * m_F_ratio",
                values={
                    "m_MTO": 10000.0,
                    "m_F_ratio": 0.2,
                },
                result=2000.0,
                unit="kg",
            ),
        ],
    )


def test_format_trace_markdown_contains_formula_and_values() -> None:
    result = make_result_with_trace()

    text = format_trace_markdown(result)

    assert "# Aircraft preliminary design calculation trace" in text
    assert "## mass_estimation" in text
    assert "S_W = m_MTO / p0_optimal" in text
    assert "`m_MTO` = `10000`" in text
    assert "`S_W` = `20` `m²`" in text


def test_format_trace_json_returns_valid_json() -> None:
    result = make_result_with_trace()

    text = format_trace_json(result)
    data = json.loads(text)

    assert data["trace_format"] == "aircraft_preliminary_design.trace.v1"
    assert data["schema_version"] == "1.0"
    assert data["records_count"] == 2
    assert data["records"][0]["value_name"] == "S_W"


def test_write_trace_markdown_creates_file(tmp_path) -> None:
    result = make_result_with_trace()
    output_path = tmp_path / "trace.md"

    write_trace_markdown(result, output_path)

    assert output_path.exists()
    assert "S_W = m_MTO / p0_optimal" in output_path.read_text(encoding="utf-8")


def test_write_trace_json_creates_file(tmp_path) -> None:
    result = make_result_with_trace()
    output_path = tmp_path / "trace.json"

    write_trace_json(result, output_path)

    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["records_count"] == 2
    assert data["records"][1]["value_name"] == "m_F"