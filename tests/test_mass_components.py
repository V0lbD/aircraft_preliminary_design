from __future__ import annotations

import pytest

from aircraft_design.core.mass_components import (
    GEAR_FAIRING_NONE,
    GEAR_MATERIAL_MEDIUM_STEEL,
    GEAR_TYPE_WHEELED,
    POWERPLANT_ELECTRIC,
    POWERPLANT_ICE,
    calculate_battery_mass_ratio,
    calculate_breguet_fuel_mass_ratio,
    calculate_landing_gear_mass_ratio,
    calculate_mass_estimation,
)


def make_common_mass_input() -> dict:
    return {
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


def test_ice_mass_estimation_runs() -> None:
    mass_input = make_common_mass_input()
    mass_input["powerplant_type"] = POWERPLANT_ICE

    result = calculate_mass_estimation(mass_input)

    assert result.powerplant_type == POWERPLANT_ICE
    assert result.iterations > 0
    assert result.final_m0 > 0
    assert result.structure_ratios.total > 0
    assert result.breakdown.fuel > 0
    assert result.breakdown.powerplant > 0


def test_electric_mass_estimation_runs() -> None:
    mass_input = make_common_mass_input()
    mass_input.update(
        {
            "powerplant_type": POWERPLANT_ELECTRIC,
            "payload_mass": 5.0,
            "service_load_mass": 0.0,
            "battery_equipment_mass": 0.5,
            "control_equipment_mass": 0.2,
            "design_range": 5.0,
            "cruise_speed": 20.0,
            "wing_area_m2": 0.8,
            "horizontal_tail_area_m2": 0.2,
            "vertical_tail_area_m2": 0.12,
            "wing_aspect_ratio": 8.0,
            "ultimate_load_factor": 3.0,
            "wing_material_factor": 0.5,
            "power_loading_N0_kw_kg": 0.08,
        }
    )

    result = calculate_mass_estimation(mass_input)

    assert result.powerplant_type == POWERPLANT_ELECTRIC
    assert result.final_m0 > 0
    assert result.breakdown.battery_energy > 0
    assert result.breakdown.fuel == 0


def test_breguet_fuel_mass_ratio_matches_formula() -> None:
    ratio = calculate_breguet_fuel_mass_ratio(
        design_range_km=400.0,
        cruise_sfc_power=0.26,
        cruise_l_d_ratio=12.0,
        propeller_efficiency=0.8,
    )

    assert ratio == pytest.approx(0.0393291, rel=1e-3)


def test_battery_mass_ratio_positive() -> None:
    ratio = calculate_battery_mass_ratio(
        design_range_km=5.0,
        cruise_l_d_ratio=10.0,
        cruise_altitude_m=100.0,
        cruise_speed_m_s=20.0,
        battery_specific_energy_wh_kg=250.0,
        electric_powertrain_efficiency=0.8,
    )

    assert ratio > 0


def test_landing_gear_mass_ratio_for_wheeled_braked_gear() -> None:
    ratio = calculate_landing_gear_mass_ratio(
        has_landing_gear=True,
        landing_gear_material=GEAR_MATERIAL_MEDIUM_STEEL,
        landing_gear_fairing=GEAR_FAIRING_NONE,
        landing_gear_type=GEAR_TYPE_WHEELED,
        has_brakes=True,
        landing_gear_strut_length_m=0.6,
    )

    assert ratio == pytest.approx(0.0419)
