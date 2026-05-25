from __future__ import annotations

import logging
import math
from typing import Any

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import CalculationState

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

        # Old formula 5.49.
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

        # Breguet range factor.
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

        # Old block uses this fuel fraction formula.
        m_F_ratio = fuel_reserve_factor * (1.0 - M_ff_total)

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

        # Old block uses a typical business jet value.
        m_ML_ratio = 0.88
        m_ML = m_MTO * m_ML_ratio

        useful_load_ratio = (m_F + payload_mass) / m_MTO

        T_TO = m_MTO * STANDARD_GRAVITY * P0_optimal
        S_W = (m_MTO * STANDARD_GRAVITY) / p0_optimal
        state.add_trace(
            block_name=self.name,
            value_name="S_W",
            formula="S_W = (m_MTO * g) / p0_optimal",
            values={
                "m_MTO": m_MTO,
                "g": STANDARD_GRAVITY,
                "p0_optimal": p0_optimal,
            },
            result=float(S_W),
            unit="m²",
            description="Wing area from maximum takeoff mass and wing loading.",
        )

        return {
            "m_MTO": float(m_MTO),
            "m_OE": float(m_OE),
            "m_F": float(m_F),
            "m_ML": float(m_ML),
            "T_TO": float(T_TO),
            "S_W": float(S_W),
            "m_OE_ratio": float(m_OE_ratio),
            "m_F_ratio": float(m_F_ratio),
            "m_ML_ratio": float(m_ML_ratio),
            "useful_load_ratio": float(useful_load_ratio),
            "mission": {
                "mass_fractions": mission_segments,
                "M_ff_non_cruise": float(M_ff_non_cruise),
                "M_ff_cruise": float(M_ff_cruise),
                "M_ff_total": float(M_ff_total),
                "breguet_range_factor": float(breguet_range_factor),
            },
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