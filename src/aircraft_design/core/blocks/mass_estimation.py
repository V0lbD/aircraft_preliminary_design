from __future__ import annotations

import logging
import math
from typing import Any

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import BlockInputSchema, CalculationState, ParameterSpec

from aircraft_design.core.mass_components import (
    ENGINE_ELECTRIC,
    ENGINE_PISTON_AIR,
    ENGINE_PISTON_LIQUID,
    ENGINE_TURBOPROP,
    GEAR_FAIRING_NONE,
    GEAR_FAIRING_RETRACTABLE,
    GEAR_FAIRING_WHEELS,
    GEAR_MATERIAL_HIGH_STRENGTH,
    GEAR_MATERIAL_MEDIUM_STEEL,
    GEAR_NONE,
    GEAR_SKI,
    GEAR_WHEELED_BRAKED,
    GEAR_WHEELED_UNBRAKED,
    calculate_component_mass_iteration,
)

logger = logging.getLogger(__name__)

STANDARD_GRAVITY = 9.80665


class MassEstimationBlock(BaseBlock):
    """
    Mass estimation block.

    Ported from old core/block_mass_estimation.py.

    The block uses preliminary sizing outputs:
    - p0_optimal
    - P0_optimal

    Formula cleanup and physics validation should be done later in
    separate commits.
    """

    name = "mass_estimation"
    required_input_sections = ("mass_estimation",)

    input_schema = BlockInputSchema(
        section_name="mass_estimation",
        block_name="mass_estimation",
        display_name="Оценка масс",
        description="Исходные параметры для оценки взлётной массы, топлива, тяги и площади крыла.",
        parameters=(
            ParameterSpec(
                name="payload_mass",
                value_type="number",
                display_name="Масса полезной нагрузки",
                description="Расчётная масса полезной нагрузки.",
                unit="kg",
                required=True,
                min_value=0,
                group="mass",
            ),
            ParameterSpec(
                name="design_range",
                value_type="number",
                display_name="Расчётная дальность",
                description="Расчётная дальность полёта.",
                unit="km",
                required=True,
                min_value=0,
                group="mission",
            ),
            ParameterSpec(
                name="fuel_reserve_factor",
                value_type="number",
                display_name="Коэффициент запаса топлива",
                description="Множитель, учитывающий запас топлива.",
                required=True,
                min_value=1,
                group="mission",
            ),
            ParameterSpec(
                name="cruise_sfc",
                value_type="number",
                display_name="Удельный расход топлива в крейсере",
                description="Удельный расход топлива на крейсерском режиме.",
                unit="1/s",
                required=True,
                min_value=0,
                group="engine",
            ),
            ParameterSpec(
                name="cruise_L_D_ratio",
                value_type="number",
                display_name="Аэродинамическое качество в крейсере",
                description="Отношение подъёмной силы к сопротивлению на крейсерском режиме.",
                required=True,
                min_value=0,
                group="aerodynamics",
            ),
            ParameterSpec(
                name="component_iteration_enabled",
                value_type="boolean",
                display_name="Включить уточнение масс по компонентам",
                description="Если включено, после базового расчёта запускается итерационный расчёт масс компонентов.",
                required=False,
                default=True,
                group="component_iteration",
            ),
            ParameterSpec(
                name="component_tolerance",
                value_type="number",
                display_name="Допуск сходимости по массе",
                description="Относительная разница между итерациями, при которой расчёт считается сошедшимся.",
                required=False,
                default=0.05,
                min_value=0,
                group="component_iteration",
            ),
            ParameterSpec(
                name="component_max_iterations",
                value_type="integer",
                display_name="Максимум итераций",
                description="Максимальное число итераций уточнения массы.",
                required=False,
                default=30,
                min_value=1,
                group="component_iteration",
            ),
            ParameterSpec(
                name="engine_type",
                value_type="string",
                display_name="Тип двигателя",
                description="Тип силовой установки для компонентного расчёта.",
                required=False,
                default=ENGINE_PISTON_AIR,
                choices=(
                    ENGINE_ELECTRIC,
                    ENGINE_PISTON_AIR,
                    ENGINE_PISTON_LIQUID,
                    ENGINE_TURBOPROP,
                ),
                group="powerplant",
            ),
            ParameterSpec(
                name="propeller_efficiency",
                value_type="number",
                display_name="КПД винта",
                description="КПД винта для расчёта потребной мощности.",
                required=False,
                default=0.8,
                min_value=0,
                max_value=1,
                group="powerplant",
            ),
            ParameterSpec(
                name="wing_material_factor",
                value_type="number",
                display_name="Коэффициент материала крыла",
                description="Коэффициент kм в формулах массы крыла.",
                required=False,
                default=1.0,
                min_value=0,
                group="wing_mass",
            ),
            ParameterSpec(
                name="wing_relative_thickness",
                value_type="number",
                display_name="Относительная толщина крыла",
                description="Относительная толщина профиля крыла c̄.",
                required=False,
                default=0.12,
                min_value=0,
                group="wing_mass",
            ),
            ParameterSpec(
                name="wing_taper_ratio",
                value_type="number",
                display_name="Сужение крыла для массы",
                description="Сужение крыла η, если оно не задано в блоке геометрии.",
                required=False,
                default=2.5,
                min_value=0,
                group="wing_mass",
            ),
            ParameterSpec(
                name="fuselage_engine_mount_factor",
                value_type="number",
                display_name="Коэффициент установки двигателя на фюзеляже",
                description="Коэффициент kс.у для формулы массы фюзеляжа.",
                required=False,
                default=1.0,
                min_value=0,
                group="fuselage_mass",
            ),
            ParameterSpec(
                name="landing_gear_type",
                value_type="string",
                display_name="Тип шасси",
                description="Тип шасси для расчёта массы.",
                required=False,
                default=GEAR_WHEELED_BRAKED,
                choices=(
                    GEAR_NONE,
                    GEAR_SKI,
                    GEAR_WHEELED_BRAKED,
                    GEAR_WHEELED_UNBRAKED,
                ),
                group="landing_gear",
            ),
            ParameterSpec(
                name="landing_gear_material",
                value_type="string",
                display_name="Материал шасси",
                description="Материал шасси, определяющий коэффициент kкон.",
                required=False,
                default=GEAR_MATERIAL_MEDIUM_STEEL,
                choices=(
                    GEAR_MATERIAL_MEDIUM_STEEL,
                    GEAR_MATERIAL_HIGH_STRENGTH,
                ),
                group="landing_gear",
            ),
            ParameterSpec(
                name="landing_gear_fairing",
                value_type="string",
                display_name="Обтекатель шасси",
                description="Наличие и тип обтекателя шасси.",
                required=False,
                default=GEAR_FAIRING_NONE,
                choices=(
                    GEAR_FAIRING_NONE,
                    GEAR_FAIRING_WHEELS,
                    GEAR_FAIRING_RETRACTABLE,
                ),
                group="landing_gear",
            ),
            ParameterSpec(
                name="landing_gear_strut_length_m",
                value_type="number",
                display_name="Длина главной опоры шасси",
                description="hглш: длина главной опоры от ВПП до узла крепления. Если неизвестна, можно оставить 1 м.",
                unit="m",
                required=False,
                default=1.0,
                min_value=0,
                group="landing_gear",
            ),
            ParameterSpec(
                name="battery_specific_energy_wh_kg",
                value_type="number",
                display_name="Удельная энергия АКБ",
                description="Удельная энергия аккумулятора q.",
                unit="Wh/kg",
                required=False,
                default=250.0,
                min_value=0,
                group="battery",
            ),
            ParameterSpec(
                name="battery_efficiency",
                value_type="number",
                display_name="КПД электрической силовой установки",
                description="КПД ηсу для расчёта относительной массы АКБ.",
                required=False,
                default=0.85,
                min_value=0,
                max_value=1,
                group="battery",
            ),
            ParameterSpec(
                name="cruise_altitude_m",
                value_type="number",
                display_name="Крейсерская высота",
                description="Высота H для расчёта массы АКБ.",
                unit="m",
                required=False,
                default=0.0,
                min_value=0,
                group="battery",
            ),
            ParameterSpec(
                name="additional_mass_ratio",
                value_type="number",
                display_name="Дополнительная относительная масса",
                description="Временная заглушка для прочих масс, пока их формулы не заданы.",
                required=False,
                default=0.0,
                min_value=0,
                group="other",
            ),
        ),
    )

    required_fields: tuple[str, ...] = (
        "payload_mass",
        "design_range",
        "fuel_reserve_factor",
        "cruise_sfc",
        "cruise_L_D_ratio",
    )

    def validate(self, state: CalculationState) -> None:
        super().validate(state)

        section = state.project_input.mass_estimation

        missing_fields = [
            field_name
            for field_name in self.required_fields
            if field_name not in section or section[field_name] is None
        ]

        if missing_fields:
            raise InputValidationError(
                "Missing required mass_estimation fields: "
                + ", ".join(missing_fields)
            )

        for field_name in self.required_fields:
            value = self._get_number(section, field_name)
            if value <= 0:
                raise InputValidationError(
                    f"mass_estimation.{field_name} must be positive. Got: {value}"
                )

        if "preliminary_sizing" not in state.data:
            raise InputValidationError(
                "Mass estimation requires preliminary_sizing block results."
            )

        preliminary_outputs = state.data["preliminary_sizing"]

        for field_name in ("p0_optimal", "P0_optimal"):
            if field_name not in preliminary_outputs:
                raise InputValidationError(
                    f"Missing preliminary_sizing output required for mass estimation: "
                    f"{field_name}"
                )

            value = preliminary_outputs[field_name]
            if not isinstance(value, int | float) or value <= 0:
                raise InputValidationError(
                    f"preliminary_sizing.{field_name} must be positive. Got: {value}"
                )

        preliminary_input = state.project_input.preliminary_sizing

        if "V_cruise" not in preliminary_input:
            raise InputValidationError(
                "Mass estimation requires preliminary_sizing.V_cruise."
            )

        cruise_velocity = self._get_number(preliminary_input, "V_cruise")
        if cruise_velocity <= 0:
            raise InputValidationError(
                f"preliminary_sizing.V_cruise must be positive. Got: {cruise_velocity}"
            )

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        preliminary_outputs = state.data["preliminary_sizing"]
        preliminary_input = state.project_input.preliminary_sizing
        section = state.project_input.mass_estimation

        p0_optimal = float(preliminary_outputs["p0_optimal"])
        P0_optimal = float(preliminary_outputs["P0_optimal"])

        payload_mass = self._get_number(section, "payload_mass")
        design_range_km = self._get_number(section, "design_range")
        fuel_reserve_factor = self._get_number(section, "fuel_reserve_factor")
        cruise_sfc = self._get_number(section, "cruise_sfc")
        cruise_l_d_ratio = self._get_number(section, "cruise_L_D_ratio")
        cruise_velocity = self._get_number(preliminary_input, "V_cruise")

        logger.debug("p0_optimal: %s", p0_optimal)
        logger.debug("P0_optimal: %s", P0_optimal)

        # todo: надо ли такое разделение
        # if P0_optimal > 0.4:
        #     m_OE_ratio = 0.7
        # else:

        m_OE_ratio = 0.23 + 1.04 * P0_optimal

        state.add_trace(
            block_name=self.name,
            value_name="m_OE_ratio",
            formula="m_OE_ratio = 0.23 + 1.04 * P0_optimal",
            values={
                "P0_optimal": P0_optimal,
            },
            result=float(m_OE_ratio),
            description="Estimated operating empty mass ratio.",
        )

        mission_segments = {
            "engine_start": 0.990,
            "taxi": 0.995,
            "takeoff": 0.995,
            "climb": 0.980,
            "descent": 0.990,
            "landing": 0.992,
        }

        M_ff_non_cruise = 1.0
        for mass_fraction in mission_segments.values():
            M_ff_non_cruise *= mass_fraction

        # todo: разобраться, надо ли домножать на 3.6
        breguet_range_factor = (
            cruise_l_d_ratio * cruise_velocity
        ) / (cruise_sfc * STANDARD_GRAVITY)

        if breguet_range_factor <= 0:
            raise InputValidationError(
                "Breguet range factor must be positive. "
                "Check cruise_L_D_ratio, V_cruise and cruise_sfc."
            )

        design_range_m = design_range_km * 1000.0
        M_ff_cruise = math.exp(-design_range_m / breguet_range_factor)
        state.add_trace(
            block_name=self.name,
            value_name="M_ff_cruise",
            formula="M_ff_cruise = exp(-design_range_m / breguet_range_factor)",
            values={
                "design_range_m": design_range_m,
                "breguet_range_factor": breguet_range_factor,
            },
            result=float(M_ff_cruise),
            description="Cruise mission fuel fraction from Breguet range relation.",
        )

        M_ff_total = M_ff_non_cruise * M_ff_cruise

        m_F_ratio = fuel_reserve_factor * (1.0 - M_ff_total)
        # propeller_efficiency=float(state.project_input.mass_estimation.get("propeller_efficiency", 0.8))

        # todo: потом убрать
        # m_F_ratio = (math.exp(
        #     ((design_range_km * STANDARD_GRAVITY * 0.26)
        #     /
        #     (735.5 * 3.6 * cruise_l_d_ratio * propeller_efficiency))
        # ) - 1) / math.exp(
        #     ((design_range_km * STANDARD_GRAVITY * 0.26)
        #      /
        #      (735.5 * 3.6 * cruise_l_d_ratio * propeller_efficiency))
        # )

        # m_F_ratio = 1 - math.exp(-((design_range_km * 0.26 * STANDARD_GRAVITY) / (cruise_l_d_ratio * propeller_efficiency)))

        if m_F_ratio < 0:
            raise InputValidationError(
                "Calculated fuel mass ratio is negative. "
                "Check design_range, cruise_sfc and cruise_L_D_ratio."
            )

        denominator = 1.0 - m_F_ratio - m_OE_ratio

        if denominator <= 0:
            raise InputValidationError(
                "Cannot calculate maximum takeoff mass: "
                f"1 - m_F_ratio - m_OE_ratio = {denominator:.6g}. "
                "Check fuel fraction, empty mass fraction and preliminary sizing outputs."
                f"m_F_ratio = {m_F_ratio}, m_OE_ratio = {m_OE_ratio}"
            )

        m_MTO = payload_mass / denominator
        state.add_trace(
            block_name=self.name,
            value_name="M_ff_cruise",
            formula="M_ff_cruise = exp(-design_range_m / breguet_range_factor)",
            values={
                "design_range_m": design_range_m,
                "breguet_range_factor": breguet_range_factor,
            },
            result=float(M_ff_cruise),
            description="Cruise mission fuel fraction from Breguet range relation.",
        )

        m_OE = m_MTO * m_OE_ratio
        m_F = m_MTO * m_F_ratio

        useful_load_ratio = (m_F + payload_mass) / m_MTO

        T_TO = m_MTO * STANDARD_GRAVITY * P0_optimal
        S_W = m_MTO / p0_optimal
        state.add_trace(
            block_name=self.name,
            value_name="S_W",
            formula="S_W = m_MTO / p0_optimal",
            values={
                "m_MTO": m_MTO,
                "g": STANDARD_GRAVITY,
                "p0_optimal": p0_optimal,
            },
            result=float(S_W),
            unit="m²",
            description="Wing area from maximum takeoff mass and wing loading.",
        )

        component_iteration = calculate_component_mass_iteration(
            initial_m0=m_MTO,
            payload_mass=payload_mass,
            fuel_mass_ratio=m_F_ratio,
            p0_optimal=p0_optimal,
            S_W=S_W,
            preliminary_input=preliminary_input,
            mass_input=section,
            geometry_input=state.project_input.geometry,
        )

        if component_iteration.enabled:
            state.add_trace(
                block_name=self.name,
                value_name="component_mass_iteration",
                formula=(
                    "m0_new = payload + fuel + wing + fuselage + tail + "
                    "powerplant + landing_gear + battery + equipment_and_control + additional"
                ),
                values={
                    "initial_m0": component_iteration.initial_m0,
                    "tolerance": component_iteration.tolerance,
                    "max_iterations": component_iteration.max_iterations,
                    "iterations": component_iteration.iterations,
                    "converged": component_iteration.converged,
                    "relative_delta": component_iteration.relative_delta,
                },
                result={
                    "final_m0": component_iteration.final_m0,
                    "component_masses": (
                        component_iteration.component_masses.to_dict()
                        if component_iteration.component_masses is not None
                        else {}
                    ),
                },
                unit="kg",
                description="Iterative component mass refinement.",
            )

            if not component_iteration.converged:
                warning = (
                    "Component mass iteration did not converge after "
                    f"{component_iteration.max_iterations} iterations. "
                    f"Last relative delta: {component_iteration.relative_delta:.5f}"
                )
                state.warnings.append(warning)
                logger.warning(warning)

            if component_iteration.converged and component_iteration.component_masses is not None:
                m_MTO = component_iteration.final_m0
                m_F = m_MTO * m_F_ratio
                m_OE = component_iteration.component_masses.operating_empty_mass
                useful_load_ratio = (m_F + payload_mass) / m_MTO
                T_TO = m_MTO * STANDARD_GRAVITY * P0_optimal
                S_W = m_MTO / p0_optimal
            else:
                warning = (
                    "Component mass iteration did not converge. "
                    "Base mass estimation values were kept."
                )
                state.warnings.append(warning)
                logger.warning(warning)

        return {
            "m_MTO": float(m_MTO),
            "m_OE": float(m_OE),
            "m_F": float(m_F),
            "T_TO": float(T_TO),
            "S_W": float(S_W),
            "m_OE_ratio": float(m_OE_ratio),
            "m_F_ratio": float(m_F_ratio),
            "useful_load_ratio": float(useful_load_ratio),
            "mission": {
                "mass_fractions": mission_segments,
                "M_ff_non_cruise": float(M_ff_non_cruise),
                "M_ff_cruise": float(M_ff_cruise),
                "M_ff_total": float(M_ff_total),
                "breguet_range_factor": float(breguet_range_factor),
            },
            "component_mass_iteration": component_iteration.to_dict(),
            "component_masses": (
                component_iteration.component_masses.to_dict()
                if component_iteration.component_masses is not None
                else {}
            ),
            "inputs_from_preliminary_sizing": {
                "p0_optimal": float(p0_optimal),
                "P0_optimal": float(P0_optimal),
            },
        }

    @staticmethod
    def _get_number(section: dict[str, Any], field_name: str) -> float:
        value = section[field_name]

        if isinstance(value, bool):
            raise InputValidationError(
                f"{field_name} must be a number, not bool."
            )

        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(
                f"{field_name} must be a number. Got: {value!r}"
            ) from exc