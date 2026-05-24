import math
from typing import Dict, Any, List

import numpy as np

from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError
from core.constants import PI

class BlockPreliminarySizing(BaseBlock):

    def __init__(self):
        """Инициализирует движок расчётов параметров"""
        super().__init__()
        self.blocks = [
            ("Блок 1: Предварительное определение параметров", BlockPreliminarySizing),
        ]

        self.calculation_log: List[str] = []
        self.errors: List[str] = []

    @property
    def name(self) -> str:
        return "Предварительное определение параметров"

    @property
    def block_number(self) -> int:
        return 1

    @property
    def required_inputs(self) -> List[str]:
        return []

    @property
    def optional_inputs(self) -> List[str]:
        return []

    @property
    def outputs(self) -> List[str]:
        return []

    def calculate(self, data: ProjectData) -> bool:
        self.calculation_log.clear()
        self.errors.clear()

        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            self.calculation_log.append("Начало предварительного расчёта характеристик")

            # todo: надо ли проверять, ввёл ли всё пользователь?
            pho_V_s = data.preliminary_sizing.pho_V_s
            V_s = data.preliminary_sizing.V_s
            C_y_max = data.preliminary_sizing.C_y_max
            theta = data.preliminary_sizing.theta
            C_x0 = data.preliminary_sizing.C_x0
            Lambda = data.preliminary_sizing.Lambda
            e = data.preliminary_sizing.e
            N = data.preliminary_sizing.N
            pho_V_cruise = data.preliminary_sizing.pho_V_cruise
            V_cruise = data.preliminary_sizing.V_cruise
            n_max = data.preliminary_sizing.n_max
            L_TODA = data.preliminary_sizing.L_TODA
            C_y_max_TO = data.preliminary_sizing.C_y_max_TO
            sigma = data.preliminary_sizing.sigma
            V_y = data.preliminary_sizing.V_y
            pho_V_y = data.preliminary_sizing.pho_V_y

            C_x, C_y = self.find_Cx_Cy(C_x0, PI, e, Lambda)

            # === РАСЧЁТ ПАРАМЕТРОВ ДЛЯ ПОСТРОЕНИЯ ОСС ===

            # p0 - удельная нагрузка на крыло
            # P0 - тяговооружённость

            # === ПРЯМЫЕ, ПАРАЛЛЕЛЬНЫЕ ОСЯМ ===
            # 15. Ограничение по скорости сваливания (вертикальная прямая)
            p0_by_V_s = ((1 / 2) * pho_V_s * V_s ** 2 * C_y_max)

            # 16. Ограничение по градиенту набора высоты (горизонтальная прямая)
            if data.preliminary_sizing.N == 1:
                P0_by_theta = theta + 2 * np.sqrt((C_x0 / (Lambda * e * PI)))
            else:
                P0_by_theta = ((N / (N - 1)) *
                               (theta + 2 * np.sqrt((C_x0 / (Lambda * e * PI)))))

            # Определение диапазона p0 исходя из максимального значения p0_by_V_s
            p0_range = (10, p0_by_V_s * 1.2)
            p0_points = np.linspace(p0_range[0], p0_range[1], 100)

            # Определение диапазона P0 исходя из минимального значения P0_by_theta
            P0_range = (P0_by_theta / 2, 2.5)

            # Горизонтальная прямая P0_by_theta
            P0_by_theta_points = []
            for p0 in p0_points:
                P0_by_theta_points.append((p0, P0_by_theta))

            P0_by_n_max_points = []
            # 17. Ограничение по эксплуатационной перегрузке
            for p0 in p0_points:
                P0 = ((C_x0 * (1 / 2) * pho_V_cruise * V_cruise ** 2) / p0 +
                        p0 * ((n_max ** 2) / (PI * Lambda * e * (1 / 2) * pho_V_cruise * V_cruise ** 2)))
                P0_by_n_max_points.append((p0, P0))

            P0_by_L_TODA_points = []
            # 18. Ограничение по взлётной дистанции
            for p0 in p0_points:
                P0 = (p0 / L_TODA) * (1 / C_y_max_TO) * (1 / sigma)
                P0_by_L_TODA_points.append((p0, P0))

            P0_by_V_y_points = []
            # 19. Ограничение по скороподъёмности
            for p0 in p0_points:
                P0 = V_y / (math.sqrt(p0) * math.sqrt((2 / pho_V_y) * (1 / C_y))) + C_x / C_y
                P0_by_V_y_points.append((p0, P0))

            P0_by_V_cruise_points = []
            # 20. Ограничение по крейсерскому полёту на заданной высоте и скорости
            for p0 in p0_points:
                P0 = ((C_x0 * (1 / 2) * pho_V_cruise * V_cruise ** 2) / p0 +
                      p0 * (1 / (PI * Lambda * e * (1 / 2) * pho_V_cruise * V_cruise ** 2)))
                P0_by_V_cruise_points.append((p0, P0))

            data.preliminary_sizing.p0_range = p0_range
            data.preliminary_sizing.P0_range = P0_range
            data.preliminary_sizing.p0_by_V_s = p0_by_V_s
            data.preliminary_sizing.P0_by_theta_points = P0_by_theta_points
            data.preliminary_sizing.P0_by_n_max_points = P0_by_n_max_points
            data.preliminary_sizing.P0_by_L_TODA_points = P0_by_L_TODA_points
            data.preliminary_sizing.P0_by_V_y_points = P0_by_V_y_points
            data.preliminary_sizing.P0_by_V_cruise_points = P0_by_V_cruise_points

            p0_optimal, P0_optimal, active_constraints = self._find_optimal_point(data)
            optimal_point = (p0_optimal, P0_optimal)

            data.preliminary_sizing.optimal_point = optimal_point
            data.preliminary_sizing.p0_optimal = p0_optimal
            data.preliminary_sizing.P0_optimal = P0_optimal

        except CalculationError as e:
            error_msg = f"{str(e)}"
            self.errors.append(error_msg)
            self.calculation_log.append(f"✗ ОШИБКА: {error_msg}")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

        self.calculation_log.append("=" * 60)
        self.calculation_log.append("✓ ВСЕ РАСЧЁТЫ УСПЕШНО ЗАВЕРШЕНЫ")
        self.calculation_log.append("=" * 60)

        return len(self.errors) == 0

    def find_Cx_Cy(self, C_x0: float, PI: float, e: float, Lambda: float) -> List[float]:
        """Вычисление C_y и C_x (параметров аэродинамического качества)
        при помощи построения касательной к поляре"""
        C_y_points = np.linspace(0, 2, 1000)
        C_x_points = []
        for C_y in C_y_points:
            C_x = C_x0 + (C_y ** 2) / (PI * e * Lambda)
            C_x_points.append(C_x)


        C_x_for_max_K = C_x_points[0]
        C_y_for_max_K = C_y_points[0]
        K_max = C_y_for_max_K / C_x_for_max_K  # аэродинамическое качество

        for C_x in C_x_points:
            for C_y in C_y_points:
                K = C_y / C_x
                if K > K_max:
                    C_y_for_max_K = C_y
                    C_x_for_max_K = C_x
                    K_max = K

        return [C_x_for_max_K, C_y_for_max_K]


    def get_chart_data_for_plotting(self, data: ProjectData) -> Dict[str, Any]:
        """Возвращает данные для построения графика"""
        return {
            'p0_range': data.preliminary_sizing.p0_range,
            'P0_range': data.preliminary_sizing.P0_range,
            'p0_by_V_s': data.preliminary_sizing.p0_by_V_s,
            'P0_by_theta_points': data.preliminary_sizing.P0_by_theta_points,
            'P0_by_n_max_points': data.preliminary_sizing.P0_by_n_max_points,
            'P0_by_L_TODA_points': data.preliminary_sizing.P0_by_L_TODA_points,
            'P0_by_V_y_points': data.preliminary_sizing.P0_by_V_y_points,
            'P0_by_V_cruise_points': data.preliminary_sizing.P0_by_V_cruise_points,
            'optimal_point': (
                data.preliminary_sizing.optimal_point[0],
                data.preliminary_sizing.optimal_point[1],
            ) if data.preliminary_sizing.optimal_point else None
        }

    def _find_optimal_point(self, data: ProjectData):
        """
        Находит оптимальную точку (p0, P0) по приоритетам:
        1) Минимизировать тяговооруженность P0
        2) При одинаковом P0 максимизировать удельную нагрузку на крыло p0

        Параметры:
        ----------
        p0_by_V_s : float
            Значение p0 из ограничения по скорости сваливания (вертикальная линия)
        P0_by_theta_points : list of tuple
            Точки для ограничения по градиенту набора высоты (горизонтальная линия)
        P0_by_n_max_points : list of tuple
            Точки для ограничения по эксплуатационной перегрузке
        P0_by_L_TODA_points : list of tuple
            Точки для ограничения по взлетной дистанции
        P0_by_V_y_points : list of tuple
            Точки для ограничения по скороподъемности
        P0_by_V_cruise_points : list of tuple
            Точки для ограничения по крейсерскому полету

        Возвращает:
        -----------
        tuple : (optimal_p0, optimal_P0, active_constraints)
            Оптимальная точка и список активных ограничений
        """

        # 1. Определяем диапазон p0 для анализа
        # Собираем все точки из всех ограничений для определения диапазона p0
        p0_by_V_s = data.preliminary_sizing.p0_by_V_s
        P0_by_theta_points = data.preliminary_sizing.P0_by_theta_points
        P0_by_n_max_points = data.preliminary_sizing.P0_by_n_max_points
        P0_by_L_TODA_points = data.preliminary_sizing.P0_by_L_TODA_points
        P0_by_V_y_points = data.preliminary_sizing.P0_by_V_y_points
        P0_by_V_cruise_points = data.preliminary_sizing.P0_by_V_cruise_points

        all_points = []
        all_points.extend(P0_by_n_max_points)
        all_points.extend(P0_by_L_TODA_points)
        all_points.extend(P0_by_V_y_points)
        all_points.extend(P0_by_V_cruise_points)

        # Извлекаем все значения p0
        all_p0_values = [p[0] for p in all_points]

        if not all_p0_values:
            return None, None, []

        # Добавляем p0_by_V_s как максимальное значение
        all_p0_values.append(p0_by_V_s)

        # Определяем диапазон для поиска
        min_p0 = min(all_p0_values)
        max_p0 = p0_by_V_s  # Ограничение по сваливанию - максимальное p0

        # Создаем сетку значений p0 для анализа
        # Используем достаточно мелкую сетку для точности
        p0_grid = np.linspace(min_p0, max_p0, 1000)

        # 2. Создаем интерполирующие функции для каждого ограничения
        # Ограничение по градиенту (горизонтальная линия)
        if P0_by_theta_points:
            P0_theta = np.mean([p[1] for p in P0_by_theta_points])
        else:
            P0_theta = 0

        # Функции интерполяции для криволинейных ограничений
        def create_interp_func(points):
            if len(points) < 2:
                return lambda x: np.zeros_like(x) if isinstance(x, np.ndarray) else 0

            # Сортируем по p0
            sorted_points = sorted(points, key=lambda x: x[0])
            p0_vals = [p[0] for p in sorted_points]
            P0_vals = [p[1] for p in sorted_points]

            # Создаем интерполирующую функцию
            # Используем линейную интерполяцию с постоянными значениями за пределами
            def interp_func(x):
                return np.interp(x, p0_vals, P0_vals, left=P0_vals[0], right=P0_vals[-1])

            return interp_func

        # Создаем функции для каждого ограничения
        f_n_max = create_interp_func(P0_by_n_max_points)
        f_L_TODA = create_interp_func(P0_by_L_TODA_points)
        f_V_y = create_interp_func(P0_by_V_y_points)
        f_V_cruise = create_interp_func(P0_by_V_cruise_points)

        # 3. Находим огибающую - максимальное P0 для каждого p0
        P0_envelope = np.zeros_like(p0_grid)
        constraint_ids = np.zeros_like(p0_grid, dtype=int)

        for i, p0 in enumerate(p0_grid):
            # Вычисляем P0 для каждого ограничения
            P0_values = {
                16: P0_theta,  # Ограничение по градиенту
                17: f_n_max(p0),  # Ограничение по эксплуатационной перегрузке
                18: f_L_TODA(p0),  # Ограничение по взлетной дистанции
                19: f_V_y(p0),  # Ограничение по скороподъемности
                20: f_V_cruise(p0)  # Ограничение по крейсерскому полету
            }

            # Находим максимальное значение (самое строгое ограничение)
            max_P0 = max(P0_values.values())
            P0_envelope[i] = max_P0

            # Определяем, какие ограничения активны (дают максимальное значение)
            active_for_point = [idx for idx, val in P0_values.items() if abs(val - max_P0) < 1e-10]
            # Сохраняем первое активное ограничение (для простоты)
            constraint_ids[i] = active_for_point[0] if active_for_point else 0

        # 4. Ищем оптимальную точку по приоритетам
        # Сначала находим минимальное значение P0 на огибающей
        min_P0 = np.min(P0_envelope)

        # Находим все точки с минимальным P0
        min_indices = np.where(np.abs(P0_envelope - min_P0) < 1e-10)[0]

        if len(min_indices) == 0:
            return None, None, []

        # Среди точек с минимальным P0 ищем максимальное p0 (второй приоритет)
        max_p0_at_min_P0 = np.max(p0_grid[min_indices])
        max_p0_idx = np.argmax(p0_grid[min_indices])
        optimal_idx = min_indices[max_p0_idx]

        # 5. Определяем активные ограничения для оптимальной точки
        optimal_p0 = p0_grid[optimal_idx]
        optimal_P0 = P0_envelope[optimal_idx]

        # Проверяем, какие ограничения активны в оптимальной точке
        active_constraints = []

        # Проверяем каждое ограничение
        P0_at_optimal = {
            16: P0_theta,
            17: f_n_max(optimal_p0),
            18: f_L_TODA(optimal_p0),
            19: f_V_y(optimal_p0),
            20: f_V_cruise(optimal_p0)
        }

        for constraint_id, P0_val in P0_at_optimal.items():
            if abs(P0_val - optimal_P0) < 1e-10:
                active_constraints.append(constraint_id)

        # Проверяем ограничение по сваливанию (15)
        if abs(optimal_p0 - p0_by_V_s) < 1e-10:
            active_constraints.append(15)

        return optimal_p0, optimal_P0, sorted(active_constraints)

    def get_log(self) -> str:
        """Возвращает лог расчётов как одну строку"""
        return "\n".join(self.calculation_log)

    def get_errors(self) -> List[str]:
        """Возвращает список ошибок"""
        return self.errors.copy()

    def has_errors(self) -> bool:
        """Проверяет, были ли ошибки"""
        return len(self.errors) > 0