from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import BlockInputSchema, CalculationState, ParameterSpec

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

    input_schema = BlockInputSchema(
        section_name="preliminary_sizing",
        block_name="preliminary_sizing",
        display_name="Предварительные характеристики",
        description="Исходные параметры для выбора нагрузки на крыло и тяговооружённости.",
        parameters=(
            ParameterSpec(
                name="N",
                value_type="integer",
                display_name="Количество двигателей",
                description="Количество двигателей самолёта.",
                required=True,
                min_value=1,
                group="configuration",
            ),
            ParameterSpec(
                name="theta",
                value_type="number",
                display_name="Градиент набора высоты",
                description="Требуемый градиент набора высоты.",
                required=True,
                min_value=0,
                group="performance",
            ),
            ParameterSpec(
                name="C_x0",
                value_type="number",
                display_name="Cx0",
                description="Коэффициент лобового сопротивления при нулевой подъёмной силе.",
                required=True,
                min_value=0,
                group="aerodynamics",
            ),
            ParameterSpec(
                name="Lambda",
                value_type="number",
                display_name="Удлинение крыла",
                description="Геометрическое удлинение крыла.",
                required=True,
                min_value=0,
                group="geometry",
            ),
            ParameterSpec(
                name="e",
                value_type="number",
                display_name="Коэффициент Освальда",
                description="Коэффициент эффективности крыла Освальда.",
                required=True,
                min_value=0,
                max_value=1,
                group="aerodynamics",
            ),
            ParameterSpec(
                name="n_max",
                value_type="number",
                display_name="Максимальная эксплуатационная перегрузка",
                description="Максимальная эксплуатационная перегрузка.",
                required=True,
                min_value=1,
                group="performance",
            ),
            ParameterSpec(
                name="sigma",
                value_type="number",
                display_name="Относительная плотность воздуха",
                description="Относительная плотность воздуха для взлётных условий.",
                required=True,
                min_value=0,
                group="atmosphere",
            ),
            ParameterSpec(
                name="V_s",
                value_type="number",
                display_name="Скорость сваливания",
                description="Расчётная скорость сваливания.",
                unit="m/s",
                required=True,
                min_value=0,
                group="speed",
            ),
            ParameterSpec(
                name="V_cruise",
                value_type="number",
                display_name="Крейсерская скорость",
                description="Расчётная крейсерская скорость.",
                unit="m/s",
                required=True,
                min_value=0,
                group="speed",
            ),
            ParameterSpec(
                name="V_y",
                value_type="number",
                display_name="Скороподъёмность",
                description="Требуемая скороподъёмность.",
                unit="m/s",
                required=True,
                min_value=0,
                group="performance",
            ),
            ParameterSpec(
                name="C_y_max",
                value_type="number",
                display_name="Cy max",
                description="Максимальный коэффициент подъёмной силы в посадочной конфигурации.",
                required=True,
                min_value=0,
                group="aerodynamics",
            ),
            ParameterSpec(
                name="C_y_max_TO",
                value_type="number",
                display_name="Cy max TO",
                description="Максимальный коэффициент подъёмной силы во взлётной конфигурации.",
                required=True,
                min_value=0,
                group="aerodynamics",
            ),
            ParameterSpec(
                name="L_TODA",
                value_type="number",
                display_name="Взлётная дистанция",
                description="Доступная или требуемая взлётная дистанция.",
                unit="m",
                required=True,
                min_value=0,
                group="runway",
            ),
            ParameterSpec(
                name="pho_V_s",
                value_type="number",
                display_name="Плотность воздуха при V_s",
                description="Плотность воздуха для режима сваливания.",
                unit="kg/m³",
                required=True,
                min_value=0,
                group="atmosphere",
            ),
            ParameterSpec(
                name="pho_V_cruise",
                value_type="number",
                display_name="Плотность воздуха в крейсере",
                description="Плотность воздуха на крейсерском режиме.",
                unit="kg/m³",
                required=True,
                min_value=0,
                group="atmosphere",
            ),
            ParameterSpec(
                name="pho_V_y",
                value_type="number",
                display_name="Плотность воздуха при наборе",
                description="Плотность воздуха для режима скороподъёмности.",
                unit="kg/m³",
                required=True,
                min_value=0,
                group="atmosphere",
            ),
        ),
    )

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

        state.add_trace(
            block_name=self.name,
            value_name="Cx_for_max_K",
            formula=r"C_x = C_{x0} + \frac{C_y^2}{\pi e \lambda}",
            values={
                "C_x0": C_x0,
                "C_y": C_y,
                "e": e,
                "Lambda": aspect_ratio,
            },
            result=float(C_x),
            description="Коэффициент сопротивления для найденного максимального аэродинамического качества.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="K_max",
            formula=r"K_{max} = \frac{C_y}{C_x}",
            values={
                "C_y": C_y,
                "C_x": C_x,
            },
            result=float(C_y / C_x),
            description="Максимальное аэродинамическое качество по текущему численному поиску.",
        )

        p0_by_V_s = 0.5 * pho_V_s * V_s**2 * C_y_max
        state.add_trace(
            block_name=self.name,
            value_name="p0_by_V_s",
            formula=r"p_{0,V_s} = \frac{1}{2} \cdot \rho_{V_s} \cdot V_s^2 \cdot C_{y,max}",
            values={
                "pho_V_s": pho_V_s,
                "V_s": V_s,
                "C_y_max": C_y_max,
            },
            result=float(p0_by_V_s),
            unit="N/m²",
            description="Ограничение по скорости сваливания.",
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
                r"P_{0,\theta} = "
                r"\begin{cases}"
                r"\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}, & N = 1 \\ "
                r"\frac{N}{N - 1}\left(\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}\right), & N > 1"
                r"\end{cases}"
            ),
            values={
                "N": N,
                "theta": theta,
                "C_x0": C_x0,
                "Lambda": aspect_ratio,
                "e": e,
            },
            result=float(P0_by_theta),
            description="Ограничение по градиенту набора высоты.",
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

        P0_by_n_max_at_optimal = self._interpolate_constraint_value(
            P0_by_n_max_points,
            p0_optimal,
        )
        P0_by_L_TODA_at_optimal = self._interpolate_constraint_value(
            P0_by_L_TODA_points,
            p0_optimal,
        )
        P0_by_V_y_at_optimal = self._interpolate_constraint_value(
            P0_by_V_y_points,
            p0_optimal,
        )
        P0_by_V_cruise_at_optimal = self._interpolate_constraint_value(
            P0_by_V_cruise_points,
            p0_optimal,
        )

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_n_max",
            formula=(
                r"P_{0,n_{max}}(p_0) = "
                r"\frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0}"
                r" + "
                r"p_0 \cdot \frac{n_{max}^2}"
                r"{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}"
            ),
            values={
                "p0_optimal": p0_optimal,
                "C_x0": C_x0,
                "pho_V_cruise": pho_V_cruise,
                "V_cruise": V_cruise,
                "n_max": n_max,
                "Lambda": aspect_ratio,
                "e": e,
                "points_count": len(P0_by_n_max_points),
            },
            result=P0_by_n_max_at_optimal,
            description="Ограничение по максимальной эксплуатационной перегрузке. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_L_TODA",
            formula=(
                r"P_{0,L_{TODA}}(p_0) = "
                r"\frac{p_0}{L_{TODA}} \cdot "
                r"\frac{1}{C_{y,max,TO}} \cdot "
                r"\frac{1}{\sigma}"
            ),
            values={
                "p0_optimal": p0_optimal,
                "L_TODA": L_TODA,
                "C_y_max_TO": C_y_max_TO,
                "sigma": sigma,
                "points_count": len(P0_by_L_TODA_points),
            },
            result=P0_by_L_TODA_at_optimal,
            description="Ограничение по взлётной дистанции. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_V_y",
            formula=(
                r"P_{0,V_y}(p_0) = "
                r"\frac{V_y}"
                r"{\sqrt{p_0}\sqrt{\frac{2}{\rho_{V_y}}\frac{1}{C_y}}}"
                r" + \frac{C_x}{C_y}"
            ),
            values={
                "p0_optimal": p0_optimal,
                "V_y": V_y,
                "pho_V_y": pho_V_y,
                "C_x": C_x,
                "C_y": C_y,
                "points_count": len(P0_by_V_y_points),
            },
            result=P0_by_V_y_at_optimal,
            description="Ограничение по скороподъёмности. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_V_cruise",
            formula=(
                r"P_{0,V_{cr}}(p_0) = "
                r"\frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0}"
                r" + "
                r"p_0 \cdot \frac{1}"
                r"{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}"
            ),
            values={
                "p0_optimal": p0_optimal,
                "C_x0": C_x0,
                "pho_V_cruise": pho_V_cruise,
                "V_cruise": V_cruise,
                "Lambda": aspect_ratio,
                "e": e,
                "points_count": len(P0_by_V_cruise_points),
            },
            result=P0_by_V_cruise_at_optimal,
            description="Ограничение по крейсерскому полёту. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="optimal_point",
            formula=(
                r"P_{0,envelope}(p_0) = "
                r"\max\left(P_{0,\theta}, P_{0,n_{max}}, P_{0,L_{TODA}}, "
                r"P_{0,V_y}, P_{0,V_{cr}}\right)"
                r", \quad "
                r"(p_{0,opt}, P_{0,opt}) = \arg\min P_{0,envelope}(p_0)"
            ),
            values={
                "p0_by_V_s": float(p0_by_V_s),
                "P0_by_theta": float(P0_by_theta),
                "P0_by_n_max_at_optimal": P0_by_n_max_at_optimal,
                "P0_by_L_TODA_at_optimal": P0_by_L_TODA_at_optimal,
                "P0_by_V_y_at_optimal": P0_by_V_y_at_optimal,
                "P0_by_V_cruise_at_optimal": P0_by_V_cruise_at_optimal,
                "active_constraints": active_constraints,
            },
            result={
                "p0_optimal": float(p0_optimal),
                "P0_optimal": float(P0_optimal),
            },
            description="Выбор расчётной точки по огибающей ограничений.",
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


    @staticmethod
    def _interpolate_constraint_value(
        points: list[tuple[float, float]],
        p0: float,
    ) -> float | None:
        if not points:
            return None

        sorted_points = sorted(points, key=lambda item: item[0])
        p0_values = [point[0] for point in sorted_points]
        P0_values = [point[1] for point in sorted_points]

        return float(
            np.interp(
                p0,
                p0_values,
                P0_values,
                left=P0_values[0],
                right=P0_values[-1],
            )
        )