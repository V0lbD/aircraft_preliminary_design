from __future__ import annotations

from aircraft_design.app import run_calculation_from_sections
from aircraft_design.ui.adapter import (
    build_existence_chart_view,
    build_input_table_sections,
    build_output_table_rows,
    collect_input_sections_from_field_views,
)


def make_preliminary_sizing_data() -> dict:
    return {
        "N": 2,
        "theta": 0.15,
        "C_x0": 0.028,
        "Lambda": 9.2,
        "e": 0.82,
        "n_max": 3.2,
        "sigma": 1.0,
        "V_s": 52.0,
        "V_cruise": 185.0,
        "V_y": 10.0,
        "C_y_max": 1.5,
        "C_y_max_TO": 1.9,
        "L_TODA": 850.0,
        "pho_V_s": 1.225,
        "pho_V_cruise": 0.45,
        "pho_V_y": 1.1,
    }


def make_mass_estimation_data() -> dict:
    return {
        "payload_mass": 1100.0,
        "design_range": 2000.0,
        "fuel_reserve_factor": 1.15,
        "cruise_sfc": 1.8e-5,
        "cruise_L_D_ratio": 13.5,
    }


def test_build_input_table_sections_from_schema() -> None:
    sections = build_input_table_sections()

    assert [section.section_name for section in sections] == [
        "preliminary_sizing",
        "mass_estimation",
        "geometry",
    ]

    preliminary = sections[0]

    assert preliminary.display_name == "Предварительные характеристики"

    field_names = [field.name for field in preliminary.fields]

    assert "V_s" in field_names
    assert "Lambda" in field_names


def test_build_input_table_sections_with_values() -> None:
    sections = build_input_table_sections(
        values={
            "preliminary_sizing": {
                "V_s": 60.0,
            },
            "geometry": {
                "wing_scheme": "high",
            },
        }
    )

    preliminary = sections[0]
    geometry = sections[2]

    v_s_field = next(field for field in preliminary.fields if field.name == "V_s")
    wing_scheme_field = next(field for field in geometry.fields if field.name == "wing_scheme")

    assert v_s_field.value == 60.0
    assert wing_scheme_field.value == "high"


def test_collect_input_sections_from_field_views() -> None:
    sections = build_input_table_sections(
        values={
            "preliminary_sizing": make_preliminary_sizing_data(),
            "mass_estimation": make_mass_estimation_data(),
            "geometry": {},
        }
    )

    collected = collect_input_sections_from_field_views(sections)

    assert collected["preliminary_sizing"]["N"] == 2
    assert collected["preliminary_sizing"]["V_s"] == 52.0
    assert collected["mass_estimation"]["payload_mass"] == 1100.0
    assert collected["geometry"]["wing_scheme"] == "mid"


def test_build_output_rows_and_chart_view_from_result() -> None:
    result = run_calculation_from_sections(
        preliminary_sizing=make_preliminary_sizing_data(),
        mass_estimation=make_mass_estimation_data(),
        geometry={},
        trace_enabled=False,
    )

    rows = build_output_table_rows(result)
    chart = build_existence_chart_view(result)

    row_names = [row.name for row in rows]

    assert "p0_optimal" in row_names
    assert "m_MTO" in row_names
    assert "S_W" in row_names
    assert "l_wing" in row_names

    assert len(chart.series) > 0
    assert chart.optimal_point is not None
    assert chart.p0_by_v_s is not None