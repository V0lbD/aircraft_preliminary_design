from __future__ import annotations

from aircraft_design.core.mass_components import calculate_component_mass_iteration


def test_component_mass_iteration_runs() -> None:
    result = calculate_component_mass_iteration(
        initial_m0=2500.0,
        payload_mass=300.0,
        fuel_mass_ratio=0.15,
        p0_optimal=2500.0,
        S_W=10,
        preliminary_input={
            "Lambda": 9.2,
            "n_max": 3.2,
            "V_cruise": 70.0,
            "pho_V_cruise": 1.0,
            "C_x0": 0.028,
            "e": 0.82,
        },
        mass_input={
            "component_iteration_enabled": True,
            "component_tolerance": 0.05,
            "component_max_iterations": 30,
            "engine_type": "ПД воздушного охлаждения",
            "propeller_efficiency": 0.8,
            "landing_gear_type": "колёсное с тормозами",
            "landing_gear_material": "сталь средней удельной прочности",
            "landing_gear_fairing": "нет",
            "landing_gear_strut_length_m": 1.0,
        },
        geometry_input={
            "eta_wing": 2.5,
            "k_horizontal_tail": 0.25,
            "k_vertical_tail": 0.15,
        },
    )

    assert result.enabled is True
    assert result.iterations > 0
    assert result.component_masses is not None
    assert result.final_m0 > 0

    component_masses = result.component_masses.to_dict()

    assert component_masses["wing"] > 0
    assert component_masses["fuselage"] > 0
    assert component_masses["tail"] > 0
    assert component_masses["landing_gear"] > 0