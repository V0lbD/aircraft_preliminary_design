from __future__ import annotations

import logging
import math

import numpy as np

from aircraft_design.core.blocks.base import BaseBlock

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
    """Блок предварительного расчета."""
    name = "preliminary_sizing"
    display_name = "Предварительные характеристики"

    def calculate(self, project: 'ProjectState') -> None:
        # 1. Локальные алиасы для чистоты кода
        ps = project.preliminary

        # 2. Математика: Расчёт C_x и C_y
        C_x, C_y = self.find_cx_cy(
            C_x0=ps.C_x0,
            e=ps.e,
            aspect_ratio=ps.Lambda,
        )

        project.add_trace(
            value_name="Cx_for_max_K",
            formula=r"C_x = C_{x0} + \frac{C_y^2}{\pi e \lambda}",
            values={"C_x0": ps.C_x0, "C_y": C_y, "e": ps.e, "Lambda": ps.Lambda},
            result=float(C_x),
            description="Коэффициент сопротивления для максимального аэродинамического качества.",
        )

        project.add_trace(
            value_name="K_max",
            formula=r"K_{max} = \frac{C_y}{C_x}",
            values={"C_y": C_y, "C_x": C_x},
            result=float(C_y / C_x),
        )

        # 3. Расчет ограничений
        p0_by_V_s = 0.5 * ps.pho_V_s * ps.V_s ** 2 * ps.C_y_max
        project.add_trace(
            value_name="p0_by_V_s",
            formula=r"p_{0,V_s} = \frac{1}{2} \cdot \rho_{V_s} \cdot V_s^2 \cdot C_{y,max}",
            values={"pho_V_s": ps.pho_V_s, "V_s": ps.V_s, "C_y_max": ps.C_y_max},
            result=float(p0_by_V_s),
            description="Ограничение по скорости сваливания.",
        )

        if ps.N == 1:
            P0_by_theta = ps.theta + 2 * math.sqrt(ps.C_x0 / (ps.Lambda * ps.e * math.pi))
        else:
            P0_by_theta = (ps.N / (ps.N - 1)) * (
                    ps.theta + 2 * math.sqrt(ps.C_x0 / (ps.Lambda * ps.e * math.pi))
            )

        project.add_trace(
            value_name="P0_by_theta",
            formula=(
                r"P_{0,\theta} = "
                r"\begin{cases}"
                r"\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}, & N = 1 \\ "
                r"\frac{N}{N - 1}\left(\theta + 2\sqrt{\frac{C_{x0}}{\pi \lambda e}}\right), & N > 1"
                r"\end{cases}"
            ),
            values={"N": ps.N, "theta": ps.theta, "C_x0": ps.C_x0, "Lambda": ps.Lambda, "e": ps.e},
            result=float(P0_by_theta),
            description="Ограничение по градиенту набора высоты.",
        )

        # 4. Генерация массивов для графиков
        p0_range = (10.0, p0_by_V_s * 1.2)
        p0_points = np.linspace(p0_range[0], p0_range[1], 100)

        P0_by_theta_points = [(float(p0), float(P0_by_theta)) for p0 in p0_points]
        P0_by_n_max_points = []
        P0_by_L_TODA_points = []
        P0_by_V_y_points = []
        P0_by_V_cruise_points = []

        for p0 in p0_points:
            # Эксплуатационная перегрузка
            P0_n_max = ((ps.C_x0 * 0.5 * ps.pho_V_cruise * ps.V_cruise ** 2) / p0 + p0 * (ps.n_max ** 2 / (
                    math.pi * ps.Lambda * ps.e * 0.5 * ps.pho_V_cruise * ps.V_cruise ** 2)))
            P0_by_n_max_points.append((float(p0), float(P0_n_max)))

            # Взлётная дистанция
            P0_L_TODA = (p0 / ps.L_TODA) * (1 / ps.C_y_max_TO) * (1 / ps.sigma)
            P0_by_L_TODA_points.append((float(p0), float(P0_L_TODA)))

            # Скороподъёмность
            P0_V_y = (ps.V_y / (math.sqrt(p0) * math.sqrt((2 / ps.pho_V_y) * (1 / C_y))) + C_x / C_y)
            P0_by_V_y_points.append((float(p0), float(P0_V_y)))

            # Крейсерский полёт
            P0_V_cruise = ((ps.C_x0 * 0.5 * ps.pho_V_cruise * ps.V_cruise ** 2) / p0 + p0 * (
                    1 / (math.pi * ps.Lambda * ps.e * 0.5 * ps.pho_V_cruise * ps.V_cruise ** 2)))
            P0_by_V_cruise_points.append((float(p0), float(P0_V_cruise)))

        # 5. Поиск оптимальной точки (используем те же методы из старого кода)
        p0_optimal, P0_optimal, active_constraints = self.find_optimal_point(
            p0_by_V_s=p0_by_V_s,
            P0_by_theta_points=P0_by_theta_points,
            P0_by_n_max_points=P0_by_n_max_points,
            P0_by_L_TODA_points=P0_by_L_TODA_points,
            P0_by_V_y_points=P0_by_V_y_points,
            P0_by_V_cruise_points=P0_by_V_cruise_points,
        )

        project.add_trace(
            value_name="optimal_point",
            formula=r"(p_{0,opt}, P_{0,opt}) = \arg\min P_{0,envelope}(p_0)",
            values={"active_constraints": active_constraints},
            result={"p0_optimal": float(p0_optimal), "P0_optimal": float(P0_optimal)},
        )

        # 6. Записываем скалярные результаты обратно в проект через дескрипторы
        ps.p0_optimal = float(p0_optimal)
        ps.P0_optimal = float(P0_optimal)
        ps.C_x_for_max_K = float(C_x)
        ps.C_y_for_max_K = float(C_y)
        ps.K_max = float(C_y / C_x)

        # 7. Сохраняем массивы для графиков в базе данных проекта (не как параметры!)
        project.databases["preliminary_chart_data"] = {
            "P0_by_theta_points": P0_by_theta_points,
            "P0_by_n_max_points": P0_by_n_max_points,
            "P0_by_L_TODA_points": P0_by_L_TODA_points,
            "P0_by_V_y_points": P0_by_V_y_points,
            "P0_by_V_cruise_points": P0_by_V_cruise_points,
            "optimal_point": (float(p0_optimal), float(P0_optimal)),
            "p0_by_V_s": float(p0_by_V_s)
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