from __future__ import annotations

import pytest

from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import (
    create_input_template,
    input_schemas_to_dict,
    normalize_project_input_data,
)
from aircraft_design.core.pipeline import get_default_input_schemas


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



def test_default_input_schemas_are_available() -> None:
    schemas = get_default_input_schemas()

    section_names = [schema.section_name for schema in schemas]

    assert section_names == [
        "preliminary_sizing",
        "mass_estimation",
        "geometry",
    ]


def test_input_schema_can_be_serialized() -> None:
    schemas = get_default_input_schemas()

    data = input_schemas_to_dict(schemas)

    assert data["schema_format"] == "aircraft_preliminary_design.input_schema.v1"
    assert data["schema_version"] == "1.0"
    assert len(data["sections"]) == 3

    preliminary_section = data["sections"][0]

    assert preliminary_section["section_name"] == "preliminary_sizing"
    assert preliminary_section["parameters"][0]["name"] == "N"


def test_create_input_template_contains_all_sections() -> None:
    schemas = get_default_input_schemas()

    template = create_input_template(schemas)

    assert template["schema_version"] == "1.0"
    assert "aircraft" in template
    assert "preliminary_sizing" in template
    assert "mass_estimation" in template
    assert "geometry" in template

    assert "V_s" in template["preliminary_sizing"]
    assert "payload_mass" in template["mass_estimation"]
    assert template["geometry"]["wing_scheme"] == "mid"


def test_normalize_project_input_data_fills_geometry_defaults() -> None:
    schemas = get_default_input_schemas()

    data = {
        "schema_version": "1.0",
        "aircraft": {},
        "preliminary_sizing": {
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
        },
        "mass_estimation": make_mass_estimation_data(),
        "geometry": {},
    }

    normalized = normalize_project_input_data(data, schemas)

    assert normalized["geometry"]["eta_wing"] == 2.5
    assert normalized["geometry"]["wing_scheme"] == "mid"
    assert normalized["geometry"]["lambda_fuselage"] == 9.0


def test_normalize_project_input_data_rejects_missing_required_field() -> None:
    schemas = get_default_input_schemas()

    data = {
        "schema_version": "1.0",
        "aircraft": {},
        "preliminary_sizing": {},
        "mass_estimation": {},
        "geometry": {},
    }

    with pytest.raises(InputValidationError, match="Missing required field"):
        normalize_project_input_data(data, schemas)


def test_normalize_project_input_data_rejects_invalid_choice() -> None:
    schemas = get_default_input_schemas()

    data = {
        "schema_version": "1.0",
        "aircraft": {},
        "preliminary_sizing": {
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
        },
        "mass_estimation": make_mass_estimation_data(),
        "geometry": {
            "wing_scheme": "unknown",
        },
    }

    with pytest.raises(InputValidationError, match="wing_scheme"):
        normalize_project_input_data(data, schemas)