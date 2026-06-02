from __future__ import annotations

from aircraft_design.app import run_calculation
from aircraft_design.core.models import ProjectInput


def test_run_calculation_full_pipeline() -> None:
    project_input = ProjectInput.from_dict(
        {
            "schema_version": "1.0",
            "metadata": {
                "case_name": "smoke_test",
            },
            "aircraft": {
                "aircraft_type": "business_jet",
            },
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
            "mass_estimation": {
                "payload_mass": 1100.0,
                "design_range": 2000.0,
                "fuel_reserve_factor": 1.15,
                "cruise_sfc": 1.8e-5,
                "cruise_L_D_ratio": 13.5,
            },
            "geometry": {
                "eta_wing": 2.5,
                "sweep_wing_quarter": 25.0,
                "wing_scheme": "mid",
                "k_horizontal_tail": 0.25,
                "lambda_horizontal_tail": 4.0,
                "eta_horizontal_tail": 3.0,
                "sweep_horizontal_tail_quarter": 30.0,
                "k_vertical_tail": 0.15,
                "lambda_vertical_tail": 1.5,
                "eta_vertical_tail": 2.0,
                "sweep_vertical_tail_quarter": 35.0,
                "k_fuselage": 1.2,
                "lambda_fuselage": 9.0,
            },
        }
    )

    result = run_calculation(project_input)

    assert result.success is True

    block_names = [block_result.block_name for block_result in result.block_results]

    assert block_names == [
        "preliminary_sizing",
        "mass_estimation",
        "geometry",
    ]

    assert "p0_optimal" in result.outputs["preliminary_sizing"]
    assert "m_MTO" in result.outputs["mass_estimation"]
    assert "wing" in result.outputs["geometry"]