from __future__ import annotations

import logging
from typing import Any, Optional

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.blocks.mass_estimation.components import (
    ENGINE_CHOICES,
    ENGINE_PISTON,
    GEAR_FAIRING_CHOICES,
    GEAR_FAIRING_NONE,
    GEAR_MATERIAL_CHOICES,
    GEAR_MATERIAL_MEDIUM_STEEL,
    GEAR_TYPE_CHOICES,
    GEAR_TYPE_WHEELED,
    POWERPLANT_CHOICES,
    POWERPLANT_ELECTRIC,
    WING_POSITION_CHOICES,
    WING_POSITION_HIGH,
    MassEstimationInput,
    calculate_mass_estimation,
)
from aircraft_design.core.models import BlockInputSchema, CalculationState, ParameterSpec

logger = logging.getLogger(__name__)

STANDARD_GRAVITY = 9.80665


class MassEstimationBlock(BaseBlock):
    """Блок оценки масс на основе новых итерационных алгоритмов."""

    name = "mass_estimation"
    required_input_sections = ("mass_estimation",)

    input_schema = BlockInputSchema(
        section_name="mass_estimation",
        block_name="mass_estimation",
        display_name="Оценка масс",
        description="Исходные параметры для оценки взлётной массы самолёта.",
        parameters=(
            ParameterSpec(name="powerplant_type", value_type="string", display_name="Тип силовой установки",
                          description="", required=True, default=POWERPLANT_ELECTRIC, choices=POWERPLANT_CHOICES,
                          group="general"),
            ParameterSpec(name="payload_mass", value_type="number", display_name="Масса целевой нагрузки",
                          description="", unit="кг", required=True, default=1.0, min_value=0, group="general"),
            ParameterSpec(name="service_load_mass", value_type="number", display_name="Масса служебной нагрузки",
                          description="", unit="кг", required=True, default=0.0, min_value=0, group="general"),
            ParameterSpec(name="battery_equipment_mass", value_type="number", display_name="Масса АКБ оборудования",
                          description="", unit="кг", required=True, default=0.0, min_value=0, group="electric"),
            ParameterSpec(name="control_equipment_mass", value_type="number",
                          display_name="Масса оборудования управления", description="", unit="кг", required=True,
                          default=0.0, min_value=0, group="electric"),
            ParameterSpec(name="design_range", value_type="number", display_name="Расчётная дальность полёта",
                          description="", unit="км", required=True, default=10.0, min_value=0, group="mission"),
            ParameterSpec(name="cruise_L_D_ratio", value_type="number", display_name="Аэродинамическое качество",
                          description="Оценочное качество в крейсерском полёте.", required=True, default=10.0,
                          min_value=0, group="aerodynamics"),
            ParameterSpec(name="is_maneuverable", value_type="boolean", display_name="Маневренный самолёт",
                          description="", required=True, default=False, group="general"),
            ParameterSpec(name="is_under_2_5kg", value_type="boolean", display_name="Масса менее 2.5 кг",
                          description="", required=True, default=False, group="electric"),
            ParameterSpec(name="battery_specific_energy_wh_kg", value_type="number",
                          display_name="Удельная энергия АКБ", description="", unit="Вт·ч/кг", required=True,
                          default=250.0, min_value=0, group="electric"),
            ParameterSpec(name="electric_powertrain_efficiency", value_type="number",
                          display_name="КПД электродвигателя", description="", required=True, default=0.8, min_value=0,
                          max_value=1, group="electric"),
            ParameterSpec(name="cruise_altitude_m", value_type="number", display_name="Крейсерская высота",
                          description="", unit="м", required=True, default=0.0, min_value=0, group="electric"),
            ParameterSpec(name="power_loading_N0_kw_kg", value_type="number", display_name="Энерговооружённость",
                          description="", unit="кВт/кг", required=True, default=0.05, min_value=0, group="electric"),
            ParameterSpec(name="cruise_sfc_power", value_type="number", display_name="Удельный расход топлива",
                          description="", unit="кг/(л.с.·ч)", required=True, default=0.26, min_value=0, group="ice"),
            ParameterSpec(name="propeller_efficiency", value_type="number", display_name="КПД винта", description="",
                          required=True, default=0.8, min_value=0, max_value=1, group="ice"),
            ParameterSpec(name="engine_type", value_type="string", display_name="Тип двигателя", description="",
                          required=True, default=ENGINE_PISTON, choices=ENGINE_CHOICES, group="ice"),
            ParameterSpec(name="takeoff_power_hp", value_type="number", display_name="Взлётная мощность двигателя",
                          description="", unit="л.с.", required=True, default=1.0, min_value=0, group="ice"),
            ParameterSpec(name="wing_relative_thickness", value_type="number",
                          display_name="Относ. толщина профиля крыла", description="", required=True, default=0.12,
                          min_value=0.02, max_value=0.2, group="structure_wing"),
            ParameterSpec(name="f_factor", value_type="number", display_name="Коэффициент безопасности (f)",
                          description="", required=True, default=2.0, min_value=1.5, max_value=3.0,
                          group="structure_wing"),
            ParameterSpec(name="wing_material_factor", value_type="number", display_name="Массовый коэффициент крыла",
                          description="", required=True, default=1.0, min_value=0, group="structure_wing"),
            ParameterSpec(name="wing_position", value_type="string", display_name="Расположение крыла", description="",
                          required=True, default=WING_POSITION_HIGH, choices=WING_POSITION_CHOICES,
                          group="structure_fuselage"),
            ParameterSpec(name="has_landing_gear", value_type="boolean", display_name="Наличие шасси", description="",
                          required=True, default=True, group="structure_landing_gear"),
            ParameterSpec(name="landing_gear_material", value_type="string", display_name="Материал шасси",
                          description="", required=True, default=GEAR_MATERIAL_MEDIUM_STEEL,
                          choices=GEAR_MATERIAL_CHOICES, group="structure_landing_gear"),
            ParameterSpec(name="landing_gear_fairing", value_type="string", display_name="Обтекатель шасси",
                          description="", required=True, default=GEAR_FAIRING_NONE, choices=GEAR_FAIRING_CHOICES,
                          group="structure_landing_gear"),
            ParameterSpec(name="landing_gear_type", value_type="string", display_name="Тип шасси", description="",
                          required=True, default=GEAR_TYPE_WHEELED, choices=GEAR_TYPE_CHOICES,
                          group="structure_landing_gear"),
            ParameterSpec(name="has_brakes", value_type="boolean", display_name="Наличие тормозов", description="",
                          required=True, default=True, group="structure_landing_gear"),
            ParameterSpec(name="landing_gear_strut_length_m", value_type="number", display_name="Высота стойки шасси",
                          description="", unit="м", required=True, default=0.2, min_value=0,
                          group="structure_landing_gear"),
            ParameterSpec(name="wing_loading_tolerance", value_type="number", display_name="Допуск изменения массы",
                          description="", required=True, default=0.10, min_value=0, group="iteration"),
            ParameterSpec(name="max_iterations", value_type="integer", display_name="Максимум итераций", description="",
                          required=True, default=30, min_value=1, group="iteration"),
        ),
    )

    def _enrich_raw_data(self, state: CalculationState, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Собирает удаленные из UI поля автоматически из соседних блоков."""
        prelim_outputs = state.data.get("preliminary_sizing", {})
        prelim_inputs = state.project_input.preliminary_sizing
        geom_inputs = state.project_input.geometry

        def _get_val(obj, key, default):
            if isinstance(obj, dict): return obj.get(key, default)
            return getattr(obj, key, default)

        raw_data["p0_optimal"] = prelim_outputs.get("p0_optimal", 100.0)
        raw_data["cruise_speed"] = _get_val(prelim_inputs, "V_cruise", 20.0)
        raw_data["n_max"] = _get_val(prelim_inputs, "n_max", 3.0)
        raw_data["engine_count"] = _get_val(prelim_inputs, "N", 1)
        raw_data["wing_aspect_ratio"] = _get_val(prelim_inputs, "Lambda", 8.0)

        raw_data["wing_taper_ratio"] = _get_val(geom_inputs, "eta_wing", 2.5)
        raw_data["k_ht"] = _get_val(geom_inputs, "k_horizontal_tail", 0.25)
        raw_data["k_vt"] = _get_val(geom_inputs, "k_vertical_tail", 0.15)

        return raw_data

    def validate(self, state: CalculationState) -> None:
        super().validate(state)
        section_data = state.project_input.mass_estimation
        raw_data = section_data if isinstance(section_data, dict) else section_data.model_dump()

        raw_data = self._enrich_raw_data(state, dict(raw_data))

        try:
            MassEstimationInput.model_validate(raw_data)
        except Exception as e:
            raise InputValidationError(f"Ошибка валидации данных блока mass_estimation: {e}")

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        section_data = state.project_input.mass_estimation
        raw_data = section_data if isinstance(section_data, dict) else section_data.model_dump()

        raw_data = self._enrich_raw_data(state, dict(raw_data))

        iteration_result = calculate_mass_estimation(
            raw_data,
            trace=state.trace,
            block_name=self.name,
        )

        breakdown = iteration_result.breakdown
        final_m0 = iteration_result.final_m0
        final_wing_area = iteration_result.final_wing_area
        m_fuel = breakdown.fuel
        m_operating_empty = breakdown.operating_empty_mass
        m_oe_ratio = m_operating_empty / final_m0
        m_f_ratio = m_fuel / final_m0
        useful_load_ratio = (breakdown.payload + breakdown.service_load + m_fuel) / final_m0

        preliminary_outputs = state.data.get("preliminary_sizing", {})
        p0_optimal = _optional_number(preliminary_outputs, "p0_optimal")
        P0_optimal = _optional_number(preliminary_outputs, "P0_optimal")

        if P0_optimal is not None and P0_optimal > 0:
            t_to = final_m0 * STANDARD_GRAVITY * P0_optimal
        else:
            t_to = 0.0

        state.add_trace(
            block_name=self.name,
            value_name="S_W",
            formula=r"S_W=\frac{m_0 g}{p_0}",
            values={"m0": final_m0, "p0": p0_optimal},
            result=float(final_wing_area),
            unit="m²",
            description="Итоговая площадь крыла.",
        )

        return {
            "m_MTO": float(final_m0),
            "m_OE": float(m_operating_empty),
            "m_F": float(m_fuel),
            "T_TO": float(t_to),
            "S_W": float(final_wing_area),
            "m_OE_ratio": float(m_oe_ratio),
            "m_F_ratio": float(m_f_ratio),
            "useful_load_ratio": float(useful_load_ratio),
            "powerplant_type": iteration_result.powerplant_type,
            "converged": iteration_result.converged,
            "iterations": iteration_result.iterations,
            "wing_loading_relative_delta": float(iteration_result.relative_delta_wing_loading),
            "structure_mass_ratio": float(iteration_result.structure_ratios.total),
            "component_masses": breakdown.to_dict(),
            "component_mass_iteration": iteration_result.to_dict(),
        }


def _optional_number(section: Any, field_name: str) -> Optional[float]:
    if isinstance(section, dict):
        value = section.get(field_name)
    else:
        value = getattr(section, field_name, None)
    if value is None or isinstance(value, bool): return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None