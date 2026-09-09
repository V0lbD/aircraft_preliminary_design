from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
from pydantic import BaseModel, Field

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


# --- СТРОГАЯ МОДЕЛЬ ВХОДНЫХ ДАННЫХ ---
class PreliminarySizingInput(BaseModel):
    N: int = Field(..., ge=1)
    theta: float = Field(..., gt=0)
    C_x0: float = Field(..., gt=0)
    Lambda: float = Field(..., gt=0)
    e: float = Field(..., gt=0, le=1.0)
    n_max: float = Field(..., gt=0)
    sigma: float = Field(..., gt=0)
    V_s: float = Field(..., gt=0)
    V_cruise: float = Field(..., gt=0)
    V_y: float = Field(..., gt=0)
    C_y_max: float = Field(..., gt=0)
    C_y_max_TO: float = Field(..., gt=0)
    L_TODA: float = Field(..., gt=0)
    pho_V_s: float = Field(..., gt=0)
    pho_V_cruise: float = Field(..., gt=0)
    pho_V_y: float = Field(..., gt=0)

    model_config = {"extra": "ignore"}


class PreliminarySizingBlock(BaseBlock):
    """
    Предварительный блок расчета.
    """

    name = "preliminary_sizing"
    required_input_sections = ("preliminary_sizing",)

    input_schema = BlockInputSchema(
        section_name="preliminary_sizing",
        block_name="preliminary_sizing",
        display_name="Предварительные характеристики",
        description="Исходные параметры для выбора нагрузки на крыло и тяговооружённости.",
        parameters=(
            ParameterSpec(name="N", value_type="integer", display_name="Количество двигателей", description="",
                          required=True, default=2, min_value=1, group="configuration"),
            ParameterSpec(name="theta", value_type="number", display_name="Градиент набора высоты", description="",
                          required=True, default=0.06, min_value=0, group="performance"),
            ParameterSpec(name="C_x0", value_type="number", display_name="Коэф. лобового сопротивления", description="",
                          required=True, default=0.04, min_value=0, group="aerodynamics"),
            ParameterSpec(name="Lambda", value_type="number", display_name="Удлинение крыла", description="",
                          required=True, default=12.19, min_value=0, group="geometry"),
            ParameterSpec(name="e", value_type="number", display_name="Коэффициент Освальда", description="",
                          required=True, default=0.68, min_value=0, max_value=1, group="aerodynamics"),
            ParameterSpec(name="n_max", value_type="number", display_name="Макс. эксплуатационная перегрузка",
                          description="", required=True, default=2.5, min_value=1, group="performance"),
            ParameterSpec(name="sigma", value_type="number", display_name="Относ. плотность воздуха (взлёт)",
                          description="", required=True, default=1.0, min_value=0, group="atmosphere"),
            ParameterSpec(name="V_s", value_type="number", display_name="Скорость сваливания", description="",
                          unit="м/с", required=True, default=20.0, min_value=0, group="speed"),
            ParameterSpec(name="V_cruise", value_type="number", display_name="Крейсерская скорость", description="",
                          unit="м/с", required=True, default=48.0, min_value=0, group="speed"),
            ParameterSpec(name="V_y", value_type="number", display_name="Скороподъёмность", description="", unit="м/с",
                          required=True, default=10.0, min_value=0, group="performance"),
            ParameterSpec(name="C_y_max", value_type="number", display_name="Макс. коэф. подъёмной силы (посадка)",
                          description="", required=True, default=1.6, min_value=0, group="aerodynamics"),
            ParameterSpec(name="C_y_max_TO", value_type="number", display_name="Макс. коэф. подъёмной силы (взлёт)",
                          description="", required=True, default=2.6, min_value=0, group="aerodynamics"),
            ParameterSpec(name="L_TODA", value_type="number", display_name="Взлётная дистанция", description="",
                          unit="м", required=True, default=150.0, min_value=0, group="runway"),
            ParameterSpec(name="pho_V_s", value_type="number", display_name="Плотность воздуха при сваливании",
                          description="", unit="кг/м³", required=True, default=1.225, min_value=0, group="atmosphere"),
            ParameterSpec(name="pho_V_cruise", value_type="number", display_name="Плотность воздуха в крейсере",
                          description="", unit="кг/м³", required=True, default=1.06, min_value=0, group="atmosphere"),
            ParameterSpec(name="pho_V_y", value_type="number", display_name="Плотность воздуха при наборе",
                          description="", unit="кг/м³", required=True, default=1.1, min_value=0, group="atmosphere"),
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
        section_data = state.project_input.preliminary_sizing
        raw_data = section_data if isinstance(section_data, dict) else section_data.model_dump()

        try:
            PreliminarySizingInput.model_validate(raw_data)
        except Exception as e:
            raise InputValidationError(f"Ошибка валидации предварительных характеристик: {e}")

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        section_data = state.project_input.preliminary_sizing
        raw_data = section_data if isinstance(section_data, dict) else section_data.model_dump()

        # Получаем строгий валидированный объект
        inputs = PreliminarySizingInput.model_validate(raw_data)

        C_x, C_y = self.find_cx_cy(
            C_x0=inputs.C_x0,
            e=inputs.e,
            aspect_ratio=inputs.Lambda,
        )

        logger.debug("C_x for max K: %s", C_x)
        logger.debug("C_y for max K: %s", C_y)

        state.add_trace(
            block_name=self.name,
            value_name="Cx_for_max_K",
            formula=r"C_x = C_{x0} + \frac{C_y^2}{\pi e \lambda}",
            values={
                "C_x0": inputs.C_x0,
                "C_y": C_y,
                "e": inputs.e,
                "Lambda": inputs.Lambda,
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

        p0_by_V_s = 0.5 * inputs.pho_V_s * inputs.V_s ** 2 * inputs.C_y_max
        state.add_trace(
            block_name=self.name,
            value_name="p0_by_V_s",
            formula=r"p_{0,V_s} = \frac{1}{2} \cdot \rho_{V_s} \cdot V_s^2 \cdot C_{y,max}",
            values={
                "pho_V_s": inputs.pho_V_s,
                "V_s": inputs.V_s,
                "C_y_max": inputs.C_y_max,
            },
            result=float(p0_by_V_s),
            unit="N/m²",
            description="Ограничение по скорости сваливания.",
        )

        if inputs.N == 1:
            P0_by_theta = inputs.theta + 2 * math.sqrt(inputs.C_x0 / (inputs.Lambda * inputs.e * math.pi))
        else:
            P0_by_theta = (inputs.N / (inputs.N - 1)) * (
                    inputs.theta + 2 * math.sqrt(inputs.C_x0 / (inputs.Lambda * inputs.e * math.pi))
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
                "N": inputs.N,
                "theta": inputs.theta,
                "C_x0": inputs.C_x0,
                "Lambda": inputs.Lambda,
                "e": inputs.e,
            },
            result=float(P0_by_theta),
            description="Ограничение по градиенту набора высоты.",
        )

        p0_range = (10.0, p0_by_V_s * 1.2)
        p0_points = np.linspace(p0_range[0], p0_range[1], 100)
        P0_range = (P0_by_theta / 2, 2.5)

        P0_by_theta_points = [(float(p0), float(P0_by_theta)) for p0 in p0_points]

        P0_by_n_max_points = []
        for p0 in p0_points:
            P0 = ((inputs.C_x0 * 0.5 * inputs.pho_V_cruise * inputs.V_cruise ** 2) / p0 + p0 * (inputs.n_max ** 2 / (
                        math.pi * inputs.Lambda * inputs.e * 0.5 * inputs.pho_V_cruise * inputs.V_cruise ** 2)))
            P0_by_n_max_points.append((float(p0), float(P0)))

        P0_by_L_TODA_points = []
        for p0 in p0_points:
            P0 = (p0 / inputs.L_TODA) * (1 / inputs.C_y_max_TO) * (1 / inputs.sigma)
            P0_by_L_TODA_points.append((float(p0), float(P0)))

        P0_by_V_y_points = []
        for p0 in p0_points:
            P0 = (inputs.V_y / (math.sqrt(p0) * math.sqrt((2 / inputs.pho_V_y) * (1 / C_y))) + C_x / C_y)
            P0_by_V_y_points.append((float(p0), float(P0)))

        P0_by_V_cruise_points = []
        for p0 in p0_points:
            P0 = ((inputs.C_x0 * 0.5 * inputs.pho_V_cruise * inputs.V_cruise ** 2) / p0 + p0 * (
                        1 / (math.pi * inputs.Lambda * inputs.e * 0.5 * inputs.pho_V_cruise * inputs.V_cruise ** 2)))
            P0_by_V_cruise_points.append((float(p0), float(P0)))

        p0_optimal, P0_optimal, active_constraints = self.find_optimal_point(
            p0_by_V_s=p0_by_V_s,
            P0_by_theta_points=P0_by_theta_points,
            P0_by_n_max_points=P0_by_n_max_points,
            P0_by_L_TODA_points=P0_by_L_TODA_points,
            P0_by_V_y_points=P0_by_V_y_points,
            P0_by_V_cruise_points=P0_by_V_cruise_points,
        )

        P0_by_n_max_at_optimal = self._interpolate_constraint_value(P0_by_n_max_points, p0_optimal)
        P0_by_L_TODA_at_optimal = self._interpolate_constraint_value(P0_by_L_TODA_points, p0_optimal)
        P0_by_V_y_at_optimal = self._interpolate_constraint_value(P0_by_V_y_points, p0_optimal)
        P0_by_V_cruise_at_optimal = self._interpolate_constraint_value(P0_by_V_cruise_points, p0_optimal)

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_n_max",
            formula=r"P_{0,n_{max}}(p_0) = \frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0} + p_0 \cdot \frac{n_{max}^2}{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}",
            values={"p0_optimal": p0_optimal, "C_x0": inputs.C_x0, "pho_V_cruise": inputs.pho_V_cruise,
                    "V_cruise": inputs.V_cruise, "n_max": inputs.n_max, "Lambda": inputs.Lambda, "e": inputs.e,
                    "points_count": len(P0_by_n_max_points)},
            result=P0_by_n_max_at_optimal,
            description="Ограничение по максимальной эксплуатационной перегрузке. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_L_TODA",
            formula=r"P_{0,L_{TODA}}(p_0) = \frac{p_0}{L_{TODA}} \cdot \frac{1}{C_{y,max,TO}} \cdot \frac{1}{\sigma}",
            values={"p0_optimal": p0_optimal, "L_TODA": inputs.L_TODA, "C_y_max_TO": inputs.C_y_max_TO,
                    "sigma": inputs.sigma, "points_count": len(P0_by_L_TODA_points)},
            result=P0_by_L_TODA_at_optimal,
            description="Ограничение по взлётной дистанции. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_V_y",
            formula=r"P_{0,V_y}(p_0) = \frac{V_y}{\sqrt{p_0}\sqrt{\frac{2}{\rho_{V_y}}\frac{1}{C_y}}} + \frac{C_x}{C_y}",
            values={"p0_optimal": p0_optimal, "V_y": inputs.V_y, "pho_V_y": inputs.pho_V_y, "C_x": C_x, "C_y": C_y,
                    "points_count": len(P0_by_V_y_points)},
            result=P0_by_V_y_at_optimal,
            description="Ограничение по скороподъёмности. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="P0_by_V_cruise",
            formula=r"P_{0,V_{cr}}(p_0) = \frac{C_{x0} \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}{p_0} + p_0 \cdot \frac{1}{\pi \lambda e \cdot \frac{1}{2}\rho_{cr}V_{cr}^2}",
            values={"p0_optimal": p0_optimal, "C_x0": inputs.C_x0, "pho_V_cruise": inputs.pho_V_cruise,
                    "V_cruise": inputs.V_cruise, "Lambda": inputs.Lambda, "e": inputs.e,
                    "points_count": len(P0_by_V_cruise_points)},
            result=P0_by_V_cruise_at_optimal,
            description="Ограничение по крейсерскому полёту. В trace указан результат в оптимальной точке.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="optimal_point",
            formula=r"P_{0,envelope}(p_0) = \max\left(P_{0,\theta}, P_{0,n_{max}}, P_{0,L_{TODA}}, P_{0,V_y}, P_{0,V_{cr}}\right), \quad (p_{0,opt}, P_{0,opt}) = \arg\min P_{0,envelope}(p_0)",
            values={"p0_by_V_s": float(p0_by_V_s), "P0_by_theta": float(P0_by_theta),
                    "P0_by_n_max_at_optimal": P0_by_n_max_at_optimal,
                    "P0_by_L_TODA_at_optimal": P0_by_L_TODA_at_optimal, "P0_by_V_y_at_optimal": P0_by_V_y_at_optimal,
                    "P0_by_V_cruise_at_optimal": P0_by_V_cruise_at_optimal, "active_constraints": active_constraints},
            result={"p0_optimal": float(p0_optimal), "P0_optimal": float(P0_optimal)},
            description="Выбор расчётной точки по огибающей ограничений.",
        )

        active_constraint_items = [
            {"id": constraint_id, "name": CONSTRAINT_LABELS.get(constraint_id, f"Ограничение {constraint_id}")}
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
            "aerodynamics": {"C_x_for_max_K": float(C_x), "C_y_for_max_K": float(C_y), "K_max": float(C_y / C_x)},
            "chart_data": {
                "P0_by_theta_points": P0_by_theta_points,
                "P0_by_n_max_points": P0_by_n_max_points,
                "P0_by_L_TODA_points": P0_by_L_TODA_points,
                "P0_by_V_y_points": P0_by_V_y_points,
                "P0_by_V_cruise_points": P0_by_V_cruise_points,
            },
        }


    @staticmethod
    def find_cx_cy(
        C_x0: float,
        e: float,
        aspect_ratio: float,
    ) -> tuple[float, float]:
        """
        Расчёт C_x и C_y для достижения максимальной аэродинамической эффективности.
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