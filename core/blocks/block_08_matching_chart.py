from typing import Dict, Any, List, Tuple
import numpy as np
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError


class Block08MatchingChart(BaseBlock):
    """
    Блок 8: Диаграмма согласования (Matching Chart)
    Выполняет графическую оптимизацию для выбора оптимальных T/W и Wing Loading
    """

    @property
    def name(self) -> str:
        return "Диаграмма согласования"

    @property
    def block_number(self) -> int:
        return 8

    @property
    def required_inputs(self) -> List[str]:
        return [
            "m_MTO_per_S_W",           # Результат блока 1 (посадка)
            "T_TO_per_m_MTO_g",       # Результат блока 2 (взлёт)
            "T_W_climb",              # Результат блока 4 (набор + крейсер)
            "T_W_missed_approach"     # Результат блока 7 (прерванная посадка)
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "matching_chart_data.wing_loading_range",
            "matching_chart_data.tw_range"
        ]

    @property
    def outputs(self) -> List[str]:
        return [
            "optimal_wing_loading",
            "optimal_tw_ratio"
        ]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет построение диаграммы согласования и выбор оптимальных параметров

        Алгоритм:
        1. Проверка всех входных данных от блоков 1-7
        2. Определение диапазонов для построения кривых
        3. Построение кривых для каждого ограничения
        4. Поиск допустимой области и оптимальной точки
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Проверка наличия всех необходимых данных от ввода пользователя
            missing_data = []

            if data.m_MTO_per_S_W is None:
                missing_data.append("Блок 1 (посадочная дистанция)")
            if data.T_TO_per_m_MTO_g is None:
                missing_data.append("Блок 2 (взлётная дистанция)")
            if data.T_W_climb is None:
                missing_data.append("Блок 4 (набор высоты и крейсер)")
            if data.T_W_missed_approach is None:
                missing_data.append("Блок 7 (прерванная посадка)")

            if missing_data:
                raise CalculationError(
                    f"Отсутствуют результаты от блоков: {', '.join(missing_data)}. "
                    "Необходимо завершить расчёты всех предыдущих блоков.",
                    self.name
                )

            # Определение диапазонов для построения
            wing_loading_range = data.matching_chart_data.wing_loading_range
            tw_range = data.matching_chart_data.tw_range

            if not wing_loading_range:
                # Автоматическое определение диапазона wing loading
                max_wing_loading = data.m_MTO_per_S_W
                wing_loading_range = (50, max_wing_loading * 1.2)
                data.matching_chart_data.wing_loading_range = wing_loading_range

            if not tw_range:
                # Автоматическое определение диапазона T/W
                max_tw = max(data.T_W_climb, data.T_W_missed_approach) * 1.2
                tw_range = (0.15, max_tw)
                data.matching_chart_data.tw_range = tw_range

            # Построение кривых ограничений
            wing_loading_points = np.linspace(wing_loading_range[0], wing_loading_range[1], 100)

            # 1. Ограничение по посадке (вертикальная линия)
            landing_limit = data.m_MTO_per_S_W
            data.matching_chart_data.landing_limit = landing_limit

            # 2. Кривая взлёта (гипербола: T/W = k / wing_loading)
            takeoff_points = []
            takeoff_factor = data.T_TO_per_m_MTO_g  # Константа из блока 2

            for wl in wing_loading_points:
                if wl <= landing_limit:  # Только допустимые значения
                    # tw_takeoff = takeoff_factor / wl
                    tw_takeoff = data.takeoff_data.takeoff_slope * wl
                    if tw_range[0] <= tw_takeoff <= tw_range[1]:
                        takeoff_points.append((wl, tw_takeoff))

            data.matching_chart_data.takeoff_curve_points = takeoff_points

            # 3. Кривая набора высоты (горизонтальная линия)
            climb_points = []
            tw_climb = data.T_W_climb

            for wl in wing_loading_points:
                if wl <= landing_limit:
                    climb_points.append((wl, tw_climb))

            data.matching_chart_data.climb_curve_points = climb_points

            # 4. Кривая крейсера (может быть функцией от wing loading)
            cruise_points = []
            tw_cruise_base = data.cruise_data.T_W_cruise or tw_climb * 0.8

            for wl in wing_loading_points:
                if wl <= landing_limit:
                    # Крейсерская кривая может слабо зависеть от wing loading
                    tw_cruise = tw_cruise_base * (1 + (wl - wing_loading_range[0]) * 0.0001)
                    cruise_points.append((wl, tw_cruise))

            data.matching_chart_data.cruise_curve_points = cruise_points

            # 5. Кривая прерванной посадки (горизонтальная линия)
            missed_approach_points = []
            tw_missed_approach = data.T_W_missed_approach

            for wl in wing_loading_points:
                if wl <= landing_limit:
                    missed_approach_points.append((wl, tw_missed_approach))

            data.matching_chart_data.missed_approach_curve_points = missed_approach_points

            # Поиск оптимальной точки
            optimal_point = self._find_optimal_point(data, wing_loading_points)

            if optimal_point:
                optimal_wl, optimal_tw = optimal_point

                # Проверка на разумность результатов
                if optimal_wl <= 0 or optimal_tw <= 0:
                    raise CalculationError(
                        "Получены недопустимые оптимальные параметры",
                        self.name,
                        {"optimal_wing_loading": optimal_wl, "optimal_tw": optimal_tw}
                    )

                # Сохранение результатов
                data.optimal_wing_loading = optimal_wl
                data.optimal_tw_ratio = optimal_tw
                data.matching_chart_data.optimal_wing_loading = optimal_wl
                data.matching_chart_data.optimal_tw_ratio = optimal_tw

                print(f"Блок 8 - Результат: Оптимальная нагрузка на крыло = {optimal_wl:.1f} кг/м²")
                print(f"Блок 8 - Результат: Оптимальное T/W = {optimal_tw:.4f}")

            else:
                raise CalculationError(
                    "Не удалось найти оптимальную точку в допустимой области",
                    self.name
                )

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def _find_optimal_point(self, data: ProjectData, wing_loading_points: np.ndarray) -> Tuple[float, float]:
        """
        Поиск оптимальной точки по критериям:
        Priority 1: минимальное T/W
        Priority 2: максимальное wing loading
        """
        landing_limit = data.m_MTO_per_S_W
        tw_climb = data.T_W_climb
        tw_missed_approach = data.T_W_missed_approach
        takeoff_factor = data.T_TO_per_m_MTO_g

        best_point = None
        best_tw = float('inf')

        # Проходим по всем возможным wing loading
        for wl in wing_loading_points:
            if wl > landing_limit:  # Нарушение ограничения по посадке
                continue

            # Находим максимальное T/W из всех ограничений для данного wing loading
            tw_takeoff = takeoff_factor / wl
            tw_required = max(tw_takeoff, tw_climb, tw_missed_approach)

            # Критерий оптимизации: минимальное T/W, затем максимальное wing loading
            if tw_required < best_tw or (tw_required == best_tw and (not best_point or wl > best_point[0])):
                best_tw = tw_required
                best_point = (wl, tw_required)

        return best_point

    def get_chart_data_for_plotting(self, data: ProjectData) -> Dict[str, Any]:
        """Возвращает данные для построения графика"""
        return {
            'wing_loading_range': data.matching_chart_data.wing_loading_range,
            'tw_range': data.matching_chart_data.tw_range,
            'landing_limit': data.matching_chart_data.landing_limit,
            'takeoff_curve': data.matching_chart_data.takeoff_curve_points,
            'climb_curve': data.matching_chart_data.climb_curve_points,
            'cruise_curve': data.matching_chart_data.cruise_curve_points,
            'missed_approach_curve': data.matching_chart_data.missed_approach_curve_points,
            'optimal_point': (
                data.matching_chart_data.optimal_wing_loading,
                data.matching_chart_data.optimal_tw_ratio
            ) if data.matching_chart_data.optimal_wing_loading else None
        }

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """Подробная сводка результатов расчёта"""
        base_summary = super().get_calculation_summary(data)

        if data.optimal_wing_loading is not None and data.optimal_tw_ratio is not None:
            base_summary['calculation_details'] = {
                'input_constraints': {
                    'landing_limit': f"{data.m_MTO_per_S_W:.1f} кг/м²" if data.m_MTO_per_S_W else "Не определён",
                    'takeoff_factor': f"{data.T_TO_per_m_MTO_g:.6f}" if data.T_TO_per_m_MTO_g else "Не определён",
                    'climb_tw': f"{data.T_W_climb:.4f}" if data.T_W_climb else "Не определён",
                    'missed_approach_tw': f"{data.T_W_missed_approach:.4f}" if data.T_W_missed_approach else "Не определён"
                },
                'chart_parameters': {
                    'wing_loading_range': f"{data.matching_chart_data.wing_loading_range[0]:.0f} - {data.matching_chart_data.wing_loading_range[1]:.0f} кг/м²" if data.matching_chart_data.wing_loading_range else "Не определён",
                    'tw_range': f"{data.matching_chart_data.tw_range[0]:.3f} - {data.matching_chart_data.tw_range[1]:.3f}" if data.matching_chart_data.tw_range else "Не определён"
                },
                'optimization_results': {
                    'optimal_wing_loading': f"{data.optimal_wing_loading:.1f} кг/м²",
                    'optimal_tw_ratio': f"{data.optimal_tw_ratio:.4f}",
                    'description': 'Результат двухкритериальной оптимизации'
                },
                'optimization_criteria': [
                    'Приоритет 1: Минимизация отношения T/W',
                    'Приоритет 2: Максимизация нагрузки на крыло',
                    'Ограничение: Все требования блоков 1-7 должны быть выполнены'
                ]
            }

        return base_summary