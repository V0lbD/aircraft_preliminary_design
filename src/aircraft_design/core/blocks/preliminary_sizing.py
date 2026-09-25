from __future__ import annotations

import logging
import math

import numpy as np

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError

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
            unit="",
            description="Коэффициент сопротивления для максимального аэродинамического качества.",
        )

        project.add_trace(
            value_name="K_max",
            formula=r"K_{max} = \frac{C_y}{C_x}",
            values={"C_y": C_y, "C_x": C_x},
            result=float(C_y / C_x),
            unit="",
            description="Максимальное аэродинамическое качество самолета."
        )

        # 3. Расчет ограничений (скалярные величины)
        p0_by_V_s = 0.5 * ps.pho_V_s * ps.V_s ** 2 * ps.C_y_max
        project.add_trace(
            value_name="p0_by_V_s",
            formula=r"p_{0,V_s} = \frac{1}{2} \cdot \rho_{V_s} \cdot V_s^2 \cdot C_{y,max}",
            values={"pho_V_s": ps.pho_V_s, "V_s": ps.V_s, "C_y_max": ps.C_y_max},
            result=float(p0_by_V_s),
            unit="Н/м²",
            description="Ограничение по скорости сваливания (максимальная удельная нагрузка на крыло).",
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
            unit="",
            description="Ограничение по градиенту набора высоты (минимальная тяговооруженность).",
        )

        # 4. Генерация массивов для графиков

        # --- Подготовка констант для новой формулы взлётной дистанции ---
        g = 9.80665
        mu = 0.3  # Заданный коэффициент трения
        k = 1.0 / (math.pi * ps.e * ps.Lambda)
        C_x_max = ps.C_x0 + k * (ps.C_y_max_TO ** 2)
        # Динамическое давление на характерной скорости отрыва (V_s / sqrt(2))^2
        rho_v_sq = ps.pho_V_s * (ps.V_s / math.sqrt(2)) ** 2
        # ---------------------------------------------------------------

        # Добавляем в Trace формулы, по которым будут строиться кривые ограничений
        project.add_trace(
            value_name="Уравнения границ области существования",
            formula=(
                r"P_{0, n_{max}} = \frac{C_{x0} \frac{\rho V_{cr}^2}{2}}{p_0} + \frac{p_0 n_{max}^2}{\pi \lambda e \frac{\rho V_{cr}^2}{2}} \\ "
                r"P_{0, L_{TODA}} = \frac{V_s^2}{2 g L_{TODA}} + \frac{\rho \left(\frac{V_s}{\sqrt{2}}\right)^2 C_{x}}{p_0} + \mu \left(1 - \frac{\rho \left(\frac{V_s}{\sqrt{2}}\right)^2 C_{y,max,TO}}{p_0}\right) \\ "
                r"P_{0, V_y} = \frac{V_y}{\sqrt{\frac{2 p_0}{\rho_{V_y} C_y}}} + \frac{C_x}{C_y} \\ "
                r"P_{0, V_{cr}} = \frac{C_{x0} \frac{\rho V_{cr}^2}{2}}{p_0} + \frac{p_0}{\pi \lambda e \frac{\rho V_{cr}^2}{2}}"
            ),
            values={"n_max": ps.n_max, "L_TODA": ps.L_TODA, "V_y": ps.V_y, "V_cruise": ps.V_cruise, "C_x": C_x_max, "mu": mu},
            result="Массивы точек сгенерированы",
            unit="",
            description="Формулы кривых ограничений (перегрузка, дистанция, скороподъемность, крейсер), используемые для поиска оптимума."
        )

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

            # Взлётная дистанция (Новая формула из тетради)
            term1 = (ps.V_s ** 2) / (2.0 * g * ps.L_TODA)
            term2 = (rho_v_sq * C_x_max) / p0
            term3 = mu * (1.0 - (rho_v_sq * ps.C_y_max_TO) / p0)
            P0_L_TODA = term1 + term2 + term3
            P0_by_L_TODA_points.append((float(p0), float(P0_L_TODA)))

            # Скороподъёмность
            P0_V_y = (ps.V_y / (math.sqrt(p0) * math.sqrt((2 / ps.pho_V_y) * (1 / C_y))) + C_x / C_y)
            P0_by_V_y_points.append((float(p0), float(P0_V_y)))

            # Крейсерский полёт
            P0_V_cruise = ((ps.C_x0 * 0.5 * ps.pho_V_cruise * ps.V_cruise ** 2) / p0 + p0 * (
                    1 / (math.pi * ps.Lambda * ps.e * 0.5 * ps.pho_V_cruise * ps.V_cruise ** 2)))
            P0_by_V_cruise_points.append((float(p0), float(P0_V_cruise)))

        # 5. Поиск оптимальной точки
        p0_optimal, P0_optimal, active_constraints = self.find_optimal_point(
            p0_by_V_s=p0_by_V_s,
            P0_by_theta_points=P0_by_theta_points,
            P0_by_n_max_points=P0_by_n_max_points,
            P0_by_L_TODA_points=P0_by_L_TODA_points,
            P0_by_V_y_points=P0_by_V_y_points,
            P0_by_V_cruise_points=P0_by_V_cruise_points,
        )

        # Переводим числовые ID ограничений (15, 16...) в понятный текст
        active_labels = [CONSTRAINT_LABELS.get(c, f"Ограничение {c}") for c in active_constraints]

        project.add_trace(
            value_name="p0_optimal",
            formula=r"p_{0,opt} = \arg\min P_{0,envelope}(p_0)",
            values={"Активные ограничения": ", ".join(active_labels)},
            result=float(p0_optimal),
            unit="Н/м²",
            description="Оптимальная удельная нагрузка на крыло."
        )

        project.add_trace(
            value_name="P0_optimal",
            formula=r"P_{0,opt} = \min P_{0,envelope}(p_0)",
            values={"p0_optimal": float(p0_optimal)},
            result=float(P0_optimal),
            unit="",
            description="Оптимальная стартовая тяговооруженность."
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
            n_points: int = 2000,
    ) -> tuple[float, float]:
        """
        Численный расчёт C_x и C_y методом перебора сетки по поляре.
        """
        # 1. Задаём диапазон Cy
        C_y_points = np.linspace(0.0, 2.0, n_points)
        C_x_points = []

        # 2. Вычисляем Cx для каждого Cy (строим поляру)
        k = 1.0 / (math.pi * e * aspect_ratio)
        for C_y in C_y_points:
            C_x = C_x0 + k * (C_y ** 2)
            C_x_points.append(C_x)

        # 3. Инициализируем переменные для поиска максимума
        C_x_for_max_K = C_x_points[0]
        C_y_for_max_K = C_y_points[0]
        K_max = C_y_for_max_K / C_x_for_max_K

        # 4. Один цикл по согласованным парам (Cx, Cy) на поляре
        for C_x, C_y in zip(C_x_points, C_y_points):
            K = C_y / C_x
            if K > K_max:
                K_max = K
                C_x_for_max_K = C_x
                C_y_for_max_K = C_y

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