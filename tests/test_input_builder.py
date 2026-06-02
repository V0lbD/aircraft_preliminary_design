from __future__ import annotations

import pytest

from aircraft_design.app import run_calculation_from_sections
from aircraft_design.core.errors import InputValidationError
from aircraft_design.input_builder import (
    create_project_input,
    create_project_input_from_sections,
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


def test_create_project_input_from_nested_dict() -> None:
    project_input = create_project_input(
        {
            "schema_version": "1.0",
            "metadata": {
                "case_name": "builder_test",
            },
            "aircraft": {
                "aircraft_type": "business_jet",
            },
            "preliminary_sizing": make_preliminary_sizing_data(),
            "mass_estimation": make_mass_estimation_data(),
            "geometry": {},
        }
    )

    assert project_input.schema_version == "1.0"
    assert project_input.metadata["case_name"] == "builder_test"

    assert project_input.geometry["eta_wing"] == 2.5
    assert project_input.geometry["wing_scheme"] == "mid"
    assert project_input.geometry["lambda_fuselage"] == 9.0


def test_create_project_input_from_sections() -> None:
    project_input = create_project_input_from_sections(
        aircraft={
            "aircraft_type": "business_jet",
        },
        metadata={
            "case_name": "section_test",
        },
        preliminary_sizing=make_preliminary_sizing_data(),
        mass_estimation=make_mass_estimation_data(),
        geometry={},
    )

    assert project_input.aircraft["aircraft_type"] == "business_jet"
    assert project_input.metadata["case_name"] == "section_test"
    assert project_input.geometry["eta_wing"] == 2.5


def test_create_project_input_rejects_invalid_ui_value() -> None:
    preliminary_sizing = make_preliminary_sizing_data()
    preliminary_sizing["N"] = 1.5

    with pytest.raises(InputValidationError, match="N must be an integer"):
        create_project_input_from_sections(
            preliminary_sizing=preliminary_sizing,
            mass_estimation=make_mass_estimation_data(),
            geometry={},
        )


def test_run_calculation_from_sections() -> None:
    result = run_calculation_from_sections(
        aircraft={
            "aircraft_type": "business_jet",
        },
        metadata={
            "case_name": "ui_like_test",
        },
        preliminary_sizing=make_preliminary_sizing_data(),
        mass_estimation=make_mass_estimation_data(),
        geometry={},
    )

    assert result.success is True

    assert "preliminary_sizing" in result.outputs
    assert "mass_estimation" in result.outputs
    assert "geometry" in result.outputs

    assert "S_W" in result.outputs["mass_estimation"]
    assert "wing" in result.outputs["geometry"]