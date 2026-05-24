from typing import Dict, Any, List
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError


class Block07MissedApproachTW(BaseBlock):
    """
    Блок 7: Расчёт T/W для прерванной посадки
    Реализует формулу 5.24 из методики
    """

    @property
    def name(self) -> str:
        return "T/W прерванной посадки"

    @property
    def block_number(self) -> int:
        return 7

    @property
    def required_inputs(self) -> List[str]:
        return [
            "climb_data.n_engines",                    # Количество двигателей из блока 3
            "missed_approach_data.gamma_sin_ma",       # sin(γ_MA) из блока 5
            "aero_analysis_data.E_ma"                  # E_MA из блока 6
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "landing_data.m_ML_m_MTO_ratio"            # Отношение посадочной к взлётной массе
        ]

    @property
    def outputs(self) -> List[str]:
        return ["T_W_missed_approach"]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет расчёт T/W по формуле 5.24

        Формула 5.24: T/(m_MTO*g) = (n_E/(n_E-1)) * (sin(γ_MA) + 1/E_MA) * (m_ML/m_MTO)
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Проверка зависимостей от предыдущих блоков
            n_engines = data.climb_data.n_engines
            gamma_sin_ma = data.missed_approach_data.gamma_sin_ma
            E_ma = data.aero_analysis_data.E_ma

            if not n_engines:
                raise CalculationError(
                    "Отсутствуют данные из блока 3 (n_engines). "
                    "Необходимо сначала выполнить расчёт параметров набора высоты.",
                    self.name
                )

            if gamma_sin_ma is None:
                raise CalculationError(
                    "Отсутствуют данные из блока 5 (gamma_sin_ma). "
                    "Необходимо сначала выполнить расчёт прерванной посадки.",
                    self.name
                )

            if E_ma is None:
                raise CalculationError(
                    "Отсутствуют данные из блока 6 (E_ma). "
                    "Необходимо сначала выполнить аэродинамический анализ.",
                    self.name
                )

            # Получение отношения масс
            m_ML_m_MTO_ratio = data.landing_data.m_ML_per_m_MTO_ratio
            if not m_ML_m_MTO_ratio:
                # Используем значение по умолчанию на основе типа самолёта
                aircraft_type = data.landing_data.aircraft_type
                m_ML_m_MTO_ratio = self._get_default_mass_ratio(aircraft_type)
                print(f"Используется стандартное отношение масс: {m_ML_m_MTO_ratio}")

            # Проверка входных данных
            if n_engines < 1 or n_engines > 8:
                raise CalculationError(
                    f"Недопустимое количество двигателей: {n_engines}",
                    self.name
                )

            if gamma_sin_ma <= 0 or gamma_sin_ma > 0.5:
                raise CalculationError(
                    f"Недопустимое значение sin(γ_MA): {gamma_sin_ma}",
                    self.name
                )

            if E_ma <= 0 or E_ma > 50:
                raise CalculationError(
                    f"Недопустимое значение E_MA: {E_ma}",
                    self.name
                )

            if m_ML_m_MTO_ratio <= 0 or m_ML_m_MTO_ratio > 1:
                raise CalculationError(
                    f"Недопустимое отношение масс: {m_ML_m_MTO_ratio}",
                    self.name
                )

            # Основной расчёт по формуле 5.24
            # T/(m_MTO*g) = (n_E/(n_E-1)) * (sin(γ_MA) + 1/E_MA) * (m_ML/m_MTO)

            # Шаг 1: Коэффициент количества двигателей
            if n_engines == 1:
                # Для однодвигательного самолёта формула упрощается
                engine_factor = 1.0
            else:
                engine_factor = n_engines / (n_engines - 1)

            # Шаг 2: Аэродинамический фактор (sin(γ_MA) + 1/E_MA)
            aero_factor = gamma_sin_ma + (1 / E_ma)

            # Шаг 3: Коэффициент массы
            mass_factor = m_ML_m_MTO_ratio

            # Шаг 4: Итоговый расчёт
            T_W_missed_approach = engine_factor * aero_factor * mass_factor

            # Проверка результата
            if T_W_missed_approach <= 0:
                raise CalculationError(
                    "Получено отрицательное или нулевое значение T/W",
                    self.name,
                    {
                        'engine_factor': engine_factor,
                        'aero_factor': aero_factor,
                        'mass_factor': mass_factor,
                        'T_W_missed_approach': T_W_missed_approach
                    }
                )

            # Проверка разумности результата
            if T_W_missed_approach > 1.5:
                print(f"Предупреждение: очень высокое отношение T/W = {T_W_missed_approach:.3f}")

            if T_W_missed_approach < 0.05:
                print(f"Предупреждение: очень низкое отношение T/W = {T_W_missed_approach:.3f}")

            # Сохранение результатов
            data.T_W_missed_approach = T_W_missed_approach
            data.missed_approach_tw_data.T_W_missed_approach = T_W_missed_approach
            data.missed_approach_tw_data.calculated_numerator = engine_factor * aero_factor
            data.missed_approach_tw_data.mass_ratio_factor = mass_factor

            print(f"Блок 7 - Результат: T/W = {T_W_missed_approach:.4f} (прерванная посадка)")
            print(f"Блок 7 - Компоненты: двигатели={engine_factor:.3f}, аэро={aero_factor:.4f}, масса={mass_factor:.3f}")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def _get_default_mass_ratio(self, aircraft_type) -> float:
        """Получение стандартного отношения посадочной к взлётной массе"""
        # Типичные значения m_ML/m_MTO по типам самолётов
        if aircraft_type:
            ratios_by_type = {
                'BUSINESS_JET': 0.85,
                'SHORT_RANGE_JET_TRANSPORT': 0.80,
                'MEDIUM_RANGE_JET_TRANSPORT': 0.75,
                'LONG_RANGE_JET_TRANSPORT': 0.70,
                'ULTRA_LONG_RANGE_JET_TRANSPORT': 0.65,
                'FIGHTER': 0.90,
                'SUPERSONIC_CRUISE': 0.75
            }

            return ratios_by_type.get(aircraft_type.name, 0.80)

        return 0.80  # Значение по умолчанию

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """Подробная сводка результатов расчёта"""
        base_summary = super().get_calculation_summary(data)

        if data.T_W_missed_approach is not None:
            base_summary['calculation_details'] = {
                'input_parameters': {
                    'n_engines': f"{data.climb_data.n_engines}" if data.climb_data.n_engines else "Не указано",
                    'gamma_sin_ma': f"{data.missed_approach_data.gamma_sin_ma:.4f}" if data.missed_approach_data.gamma_sin_ma else "Не указан",
                    'E_ma': f"{data.aero_analysis_data.E_ma:.2f}" if data.aero_analysis_data.E_ma else "Не определено",
                    'm_ML_m_MTO_ratio': f"{data.landing_data.m_ML_per_m_MTO_ratio:.3f}" if data.landing_data.m_ML_per_m_MTO_ratio else "По умолчанию"
                },
                'calculation_components': {
                    'engine_factor': f"{data.climb_data.n_engines}/{data.climb_data.n_engines-1} = {data.climb_data.n_engines/(data.climb_data.n_engines-1):.3f}" if data.climb_data.n_engines and data.climb_data.n_engines > 1 else "1.000",
                    'aero_factor': f"{data.missed_approach_data.gamma_sin_ma:.4f} + 1/{data.aero_analysis_data.E_ma:.2f} = {data.missed_approach_data.gamma_sin_ma + (1/data.aero_analysis_data.E_ma):.4f}" if data.missed_approach_data.gamma_sin_ma and data.aero_analysis_data.E_ma else "Не вычислен",
                    'mass_factor': f"{data.landing_data.m_ML_per_m_MTO_ratio:.3f}" if data.landing_data.m_ML_per_m_MTO_ratio else "Стандартное значение"
                },
                'intermediate_results': {
                    'calculated_numerator': f"{data.missed_approach_tw_data.calculated_numerator:.4f}" if data.missed_approach_tw_data.calculated_numerator else "Не вычислен",
                    'mass_ratio_factor': f"{data.missed_approach_tw_data.mass_ratio_factor:.3f}" if data.missed_approach_tw_data.mass_ratio_factor else "Не определён"
                },
                'final_result': {
                    'T_W_missed_approach': f"{data.T_W_missed_approach:.4f}",
                    'description': 'Минимальная тяговооружённость для условий прерванной посадки'
                },
                'equations_used': [
                    'T/(m_MTO*g) = (n_E/(n_E-1)) * (sin(γ_MA) + 1/E_MA) * (m_ML/m_MTO) (формула 5.24)'
                ],
                'conditions': [
                    'Один двигатель отказал',
                    'Остальные двигатели на взлётной тяге',
                    'Посадочная конфигурация (шасси и закрылки выпущены)',
                    'Посадочная масса m_ML'
                ],
                'validation_ranges': {
                    'typical_values': {'min': 0.15, 'max': 0.8},
                    'high_performance': {'min': 0.3, 'max': 1.2}
                }
            }

        return base_summary