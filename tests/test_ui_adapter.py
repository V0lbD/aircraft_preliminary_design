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
        "powerplant_type": "ice",
        "payload_mass": 520.0,
        "service_load_mass": 1500.0,
        "battery_equipment_mass": 0.0,
        "control_equipment_mass": 0.0,
        "design_range": 400.0,
        "cruise_speed": 48.0,
        "cruise_L_D_ratio": 12.0,
        "is_maneuverable": False,
        "is_under_2_5kg": False,
        "battery_specific_energy_wh_kg": 250.0,
        "electric_powertrain_efficiency": 0.8,
        "cruise_altitude_m": 0.0,
        "power_loading_N0_kw_kg": 0.05,
        "cruise_sfc_power": 0.26,
        "propeller_efficiency": 0.8,
        "engine_count": 2,
        "engine_type": "piston",
        "takeoff_power_hp": 300.0,
        "wing_area_m2": 25.0,
        "horizontal_tail_area_m2": 6.25,
        "vertical_tail_area_m2": 3.75,
        "wing_aspect_ratio": 12.19,
        "wing_taper_ratio": 1.5,
        "wing_relative_thickness": 0.12,
        "ultimate_load_factor": 2.5,
        "f_factor": 2.0,
        "wing_material_factor": 0.8,
        "wing_position": "high",
        "has_landing_gear": True,
        "landing_gear_material": "medium_steel",
        "landing_gear_fairing": "none",
        "landing_gear_type": "wheeled",
        "has_brakes": True,
        "landing_gear_strut_length_m": 0.6,
        "wing_loading_tolerance": 0.1,
        "max_iterations": 30,
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
    assert collected["mass_estimation"]["payload_mass"] == 520.0
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
    assert "powerplant_type" in row_names
    assert "m_MTO" in row_names
    assert "S_W" in row_names
    assert "structure_mass_ratio" in row_names
    assert "relative_delta_wing_loading" in row_names
    assert "service_load" in row_names
    assert "battery_energy" in row_names
    assert "l_wing" in row_names

    powerplant_row = next(row for row in rows if row.name == "powerplant_type")
    assert powerplant_row.value == "ДВС"

    assert len(chart.series) > 0
    assert chart.optimal_point is not None
    assert chart.p0_by_v_s is not None