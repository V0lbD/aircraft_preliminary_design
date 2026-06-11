from __future__ import annotations

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


from aircraft_design.input_builder import (
    create_project_input_from_sections,
    project_input_to_dict,
)


def test_project_input_to_dict_exports_json_compatible_data() -> None:
    project_input = create_project_input_from_sections(
        aircraft={
            "aircraft_type": "business_jet",
        },
        metadata={
            "case_name": "export_test",
        },
        preliminary_sizing={
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
        mass_estimation=make_mass_estimation_data(),
        geometry={},
    )

    data = project_input_to_dict(project_input)

    assert data["schema_version"] == "1.0"
    assert data["metadata"]["case_name"] == "export_test"
    assert data["aircraft"]["aircraft_type"] == "business_jet"

    assert data["preliminary_sizing"]["N"] == 2
    assert data["mass_estimation"]["payload_mass"] == 520.0

    # Defaults from geometry schema must be exported too.
    assert data["geometry"]["eta_wing"] == 2.5
    assert data["geometry"]["wing_scheme"] == "mid"