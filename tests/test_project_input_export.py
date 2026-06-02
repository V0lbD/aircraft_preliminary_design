from __future__ import annotations

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
        mass_estimation={
            "payload_mass": 1100.0,
            "design_range": 2000.0,
            "fuel_reserve_factor": 1.15,
            "cruise_sfc": 1.8e-5,
            "cruise_L_D_ratio": 13.5,
        },
        geometry={},
    )

    data = project_input_to_dict(project_input)

    assert data["schema_version"] == "1.0"
    assert data["metadata"]["case_name"] == "export_test"
    assert data["aircraft"]["aircraft_type"] == "business_jet"

    assert data["preliminary_sizing"]["N"] == 2
    assert data["mass_estimation"]["payload_mass"] == 1100.0

    # Defaults from geometry schema must be exported too.
    assert data["geometry"]["eta_wing"] == 2.5
    assert data["geometry"]["wing_scheme"] == "mid"