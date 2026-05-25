from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import CalculationState

logger = logging.getLogger(__name__)


CONSTRAINT_LABELS: dict[int, str] = {
    15: "Ограничение по скорости сваливания",
    16: "Ограничение по градиенту набора высоты",
    17: "Ограничение по эксплуатационной перегрузке",
    18: "Ограничение по взлётной дистанции",
    19: "Ограничение по скороподъёмности",
    20: "Ограничение по крейсерскому полёту",
}


class PreliminarySizingBlock(BaseBlock):
    """
    Preliminary sizing block.

    Ported from old core/block_preliminary_sizing.py.

    For now we intentionally preserve the current calculation approach.
    Formula refactoring and physics corrections should be done later in
    separate commits.
    """

    name = "preliminary_sizing"
    required_input_sections = ("preliminary_sizing",)

    required_fields: tuple[str, ...] = (
        "pho_V_s",
        "V_s",
        "C_y_max",
        "theta",
        "C_x0",
        "Lambda",
        "e",
        "N",
        "pho_V_cruise",
        "V_cruise",
        "n_max",
        "L_TODA",
        "C_y_max_TO",
        "sigma",
        "V_y",
        "pho_V_y",
    )

    def validate(self, state: CalculationState) -> None:
        super().validate(state)

        section = state.project_input.preliminary_sizing

        missing_fields = [
            field_name
            for field_name in self.required_fields
            if field_name not in section or section[field_name] is None
        ]

        if missing_fields:
            raise InputValidationError(
                "Missing required preliminary_sizing fields: "
                + ", ".join(missing_fields)
            )

        positive_fields = (
            "pho_V_s",
            "V_s",
            "C_y_max",
            "C_x0",
            "Lambda",
            "e",
            "N",
            "pho_V_cruise",
            "V_cruise",
            "n_max",
            "L_TODA",
            "C_y_max_TO",
            "sigma",
            "pho_V_y",
        )

        for field_name in positive_fields:
            value = self._get_number(section, field_name)
            if value <= 0:
                raise InputValidationError(
                    f"preliminary_sizing.{field_name} must be positive. Got: {value}"
                )

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        section = state.project_input.preliminary_sizing

        pho_V_s = self._get_number(section, "pho_V_s")
        V_s = self._get_number(section, "V_s")
        C_y_max = self._get_number(section, "C_y_max")
        theta = self._get_number(section, "theta")
        C_x0 = self._get_number(section, "C_x0")
        aspect_ratio = self._get_number(section, "Lambda")
        e = self._get_number(section, "e")
        N = int(self._get_number(section, "N"))
        pho_V_cruise = self._get_number(section, "pho_V_cruise")
        V_cruise = self._get_number(section, "V_cruise")
        n_max = self._get_number(section, "n_max")
        L_TODA = self._get_number(section, "L_TODA")
        C_y_max_TO = self._get_number(section, "C_y_max_TO")
        sigma = self._get_number(section, "sigma")
        V_y = self._get_number(section, "V_y")
        pho_V_y = self._get_number(section, "pho_V_y")

        C_x, C_y = self.find_cx_cy(
            C_x0=C_x0,
            e=e,
            aspect_ratio=aspect_ratio,
        )

        logger.debug("C_x for max K: %s", C_x)
        logger.debug("C_y for max K: %s", C_y)

        p0_by_V_s = 0.5 * pho_V_s * V_s**2 * C_y_max
        state.add_trace(
            block_name=self.name,
            value_name="p0_by_V_s",
            formula="p0_by_V_s = 0.5 * pho_V_s * V_s^2 * C_y_max",
            values={
                "pho_V_s": pho_V_s,
                "V_s": V_s,
                "C_y_max": C_y_max,
            },
            result=float(p0_by_V_s),
            unit="N/m²",
            description="Wing loading limit from stall speed.",
        )

        if N == 1:
            P0_by_theta = theta + 2 * math.sqrt(C_x0 / (aspect_ratio * e * math.pi))
        else:
            P0_by_theta = (N / (N - 1)) * (
                theta + 2 * math.sqrt(C_x0 / (aspect_ratio * e * math.pi))
            )
        state.add_trace(
            block_name=self.name,
            value_name="P0_by_theta",
            formula=(
                "P0_by_theta = theta + 2 * sqrt(C_x0 / (pi * Lambda * e)) "
                "for N = 1, otherwise multiplied by N / (N - 1)"
            ),
            values={
                "N": N,
                "theta": theta,
                "C_x0": C_x0,
                "Lambda": aspect_ratio,
                "e": e,
            },
            result=float(P0_by_theta),
            description="Thrust-to-weight limit from climb gradient.",
        )

        p0_range = (10.0, p0_by_V_s * 1.2)
        p0_points = np.linspace(p0_range[0], p0_range[1], 100)

        P0_range = (P0_by_theta / 2, 2.5)

        P0_by_theta_points = [
            (float(p0), float(P0_by_theta))
            for p0 in p0_points
        ]

        P0_by_n_max_points = []
        for p0 in p0_points:
            P0 = (
                (C_x0 * 0.5 * pho_V_cruise * V_cruise**2) / p0
                + p0
                * (
                    n_max**2
                    / (
                        math.pi
                        * aspect_ratio
                        * e
                        * 0.5
                        * pho_V_cruise
                        * V_cruise**2
                    )
                )
            )
            P0_by_n_max_points.append((float(p0), float(P0)))

        P0_by_L_TODA_points = []
        for p0 in p0_points:
            P0 = (p0 / L_TODA) * (1 / C_y_max_TO) * (1 / sigma)
            P0_by_L_TODA_points.append((float(p0), float(P0)))

        P0_by_V_y_points = []
        for p0 in p0_points:
            P0 = (
                V_y
                / (
                    math.sqrt(p0)
                    * math.sqrt((2 / pho_V_y) * (1 / C_y))
                )
                + C_x / C_y
            )
            P0_by_V_y_points.append((float(p0), float(P0)))

        P0_by_V_cruise_points = []
        for p0 in p0_points:
            P0 = (
                (C_x0 * 0.5 * pho_V_cruise * V_cruise**2) / p0
                + p0
                * (
                    1
                    / (
                        math.pi
                        * aspect_ratio
                        * e
                        * 0.5
                        * pho_V_cruise
                        * V_cruise**2
                    )
                )
            )
            P0_by_V_cruise_points.append((float(p0), float(P0)))

        p0_optimal, P0_optimal, active_constraints = self.find_optimal_point(
            p0_by_V_s=p0_by_V_s,
            P0_by_theta_points=P0_by_theta_points,
            P0_by_n_max_points=P0_by_n_max_points,
            P0_by_L_TODA_points=P0_by_L_TODA_points,
            P0_by_V_y_points=P0_by_V_y_points,
            P0_by_V_cruise_points=P0_by_V_cruise_points,
        )
        state.add_trace(
            block_name=self.name,
            value_name="optimal_point",
            formula="optimal_point = min envelope of active constraints over p0 grid",
            values={
                "p0_by_V_s": float(p0_by_V_s),
                "P0_by_theta": float(P0_by_theta),
                "active_constraints": active_constraints,
            },
            result={
                "p0_optimal": float(p0_optimal),
                "P0_optimal": float(P0_optimal),
            },
            description="Selected preliminary design point.",
        )

        active_constraint_items = [
            {
                "id": constraint_id,
                "name": CONSTRAINT_LABELS.get(
                    constraint_id,
                    f"Ограничение {constraint_id}",
                ),
            }
            for constraint_id in active_constraints
        ]

        return {
            "p0_range": p0_range,
            "P0_range": P0_range,
            "p0_by_V_s": float(p0_by_V_s),
            "P0_by_theta": float(P0_by_theta),
            "p0_optimal": float(p0_optimal),
            "P0_optimal": float(P0_optimal),
            "optimal_point": (float(p0_optimal), float(P0_optimal)),
            "active_constraints": active_constraint_items,
            "aerodynamics": {
                "C_x_for_max_K": float(C_x),
                "C_y_for_max_K": float(C_y),
                "K_max": float(C_y / C_x),
            },
            "chart_data": {
                "P0_by_theta_points": P0_by_theta_points,
                "P0_by_n_max_points": P0_by_n_max_points,
                "P0_by_L_TODA_points": P0_by_L_TODA_points,
                "P0_by_V_y_points": P0_by_V_y_points,
                "P0_by_V_cruise_points": P0_by_V_cruise_points,
            },
        }

    @staticmethod
    def _get_number(section: dict[str, Any], field_name: str) -> float:
        value = section[field_name]

        if isinstance(value, bool):
            raise InputValidationError(
                f"preliminary_sizing.{field_name} must be a number, not bool."
            )

        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(
                f"preliminary_sizing.{field_name} must be a number. Got: {value!r}"
            ) from exc

    @staticmethod
    def find_cx_cy(
        C_x0: float,
        e: float,
        aspect_ratio: float,
    ) -> tuple[float, float]:
        """
        Calculate C_x and C_y for maximum aerodynamic efficiency.

        This keeps the current behavior close to the old implementation.
        Formula cleanup will be done later.
        """
        C_y_points = np.linspace(0, 2, 1000)
        C_x_points = []

        for C_y in C_y_points:
            C_x = C_x0 + (C_y**2) / (math.pi * e * aspect_ratio)
            C_x_points.append(C_x)

        C_x_for_max_K = C_x_points[0]
        C_y_for_max_K = C_y_points[0]
        K_max = C_y_for_max_K / C_x_for_max_K

        for C_x in C_x_points:
            for C_y in C_y_points:
                K = C_y / C_x
                if K > K_max:
                    C_y_for_max_K = C_y
                    C_x_for_max_K = C_x
                    K_max = K

        return float(C_x_for_max_K), float(C_y_for_max_K)

    @staticmethod
    def find_optimal_point(
        p0_by_V_s: float,
        P0_by_theta_points: list[tuple[float, float]],
        P0_by_n_max_points: list[tuple[float, float]],
        P0_by_L_TODA_points: list[tuple[float, float]],
        P0_by_V_y_points: list[tuple[float, float]],
        P0_by_V_cruise_points: list[tuple[float, float]],
    ) -> tuple[float, float, list[int]]:
        all_points = []
        all_points.extend(P0_by_n_max_points)
        all_points.extend(P0_by_L_TODA_points)
        all_points.extend(P0_by_V_y_points)
        all_points.extend(P0_by_V_cruise_points)

        all_p0_values = [point[0] for point in all_points]

        if not all_p0_values:
            raise InputValidationError("Cannot find optimal point: no constraint points.")

        all_p0_values.append(p0_by_V_s)

        min_p0 = min(all_p0_values)
        max_p0 = p0_by_V_s

        p0_grid = np.linspace(min_p0, max_p0, 1000)

        if P0_by_theta_points:
            P0_theta = float(np.mean([point[1] for point in P0_by_theta_points]))
        else:
            P0_theta = 0.0

        def create_interp_func(points: list[tuple[float, float]]):
            if len(points) < 2:
                return lambda x: np.zeros_like(x) if isinstance(x, np.ndarray) else 0

            sorted_points = sorted(points, key=lambda item: item[0])
            p0_vals = [point[0] for point in sorted_points]
            P0_vals = [point[1] for point in sorted_points]

            def interp_func(x):
                return np.interp(
                    x,
                    p0_vals,
                    P0_vals,
                    left=P0_vals[0],
                    right=P0_vals[-1],
                )

            return interp_func

        f_n_max = create_interp_func(P0_by_n_max_points)
        f_L_TODA = create_interp_func(P0_by_L_TODA_points)
        f_V_y = create_interp_func(P0_by_V_y_points)
        f_V_cruise = create_interp_func(P0_by_V_cruise_points)

        P0_envelope = np.zeros_like(p0_grid)

        for i, p0 in enumerate(p0_grid):
            P0_values = {
                16: P0_theta,
                17: f_n_max(p0),
                18: f_L_TODA(p0),
                19: f_V_y(p0),
                20: f_V_cruise(p0),
            }

            max_P0 = max(P0_values.values())
            P0_envelope[i] = max_P0

        min_P0 = np.min(P0_envelope)
        min_indices = np.where(np.abs(P0_envelope - min_P0) < 1e-10)[0]

        if len(min_indices) == 0:
            raise InputValidationError("Cannot find optimal point: empty optimum set.")

        max_p0_idx = np.argmax(p0_grid[min_indices])
        optimal_idx = min_indices[max_p0_idx]

        optimal_p0 = float(p0_grid[optimal_idx])
        optimal_P0 = float(P0_envelope[optimal_idx])

        P0_at_optimal = {
            16: P0_theta,
            17: f_n_max(optimal_p0),
            18: f_L_TODA(optimal_p0),
            19: f_V_y(optimal_p0),
            20: f_V_cruise(optimal_p0),
        }

        active_constraints = []

        for constraint_id, P0_value in P0_at_optimal.items():
            if abs(P0_value - optimal_P0) < 1e-10:
                active_constraints.append(constraint_id)

        if abs(optimal_p0 - p0_by_V_s) < 1e-10:
            active_constraints.append(15)

        return optimal_p0, optimal_P0, sorted(active_constraints)