from typing import Dict, Any, List
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData, WingFlapsTypeEnum, AircraftTypeEnum
from core.exceptions import CalculationError


class Block06AeroAnalysis(BaseBlock):
    """
    Блок 6: Аэродинамический анализ
    Вычисляет аэродинамическое качество E_MA в посадочной конфигурации
    для использования в блоке 7 (формула 5.24)
    """

    @property
    def name(self) -> str:
        return "Аэродинамический анализ"

    @property
    def block_number(self) -> int:
        return 6

    @property
    def required_inputs(self) -> List[str]:
        return [
            "aero_analysis_data.V_ma",          # Скорость прерванной посадки
            "m_MTO_per_S_W"                     # Wing loading из блока 1
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "aero_analysis_data.h_ma",          # Высота (обычно 0 для прерванной посадки)
            "aero_analysis_data.C_D_0_landing", # C_D0 в посадочной конфигурации
            "aero_analysis_data.K_landing"      # K в посадочной конфигурации
        ]

    @property
    def outputs(self) -> List[str]:
        return ["aero_analysis_data.E_ma"]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет расчёт аэродинамического качества E_MA по формулам 5.11-5.12

        Формула 5.12: E = C_L / (C_D_0 + K*C_L²)
        Формула 5.11: C_L = (2*W/S) / (ρ*V²)
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Проверка зависимости от блока 1
            if data.m_MTO_per_S_W is None:
                raise CalculationError(
                    "Отсутствует результат блока 1 (m_MTO_per_S_W). "
                    "Необходимо сначала выполнить расчёт посадочной дистанции.",
                    self.name
                )

            # Получение входных данных
            V_ma = data.aero_analysis_data.V_ma
            h_ma = data.aero_analysis_data.h_ma or 0.0  # По умолчанию на уровне моря

            if not V_ma:
                raise CalculationError(
                    "Отсутствуют обязательные данные: V_ma (скорость прерванной посадки)",
                    self.name
                )

            # Шаг 1: Определение плотности воздуха на высоте прерванной посадки
            rho_0 = 1.225  # кг/м³ на уровне моря
            if h_ma > 0:
                sigma_ma = (1 - h_ma / 44300) ** 4.256
                rho_ma = rho_0 * sigma_ma
            else:
                rho_ma = rho_0

            data.aero_analysis_data.rho_ma = rho_ma

            # Шаг 2: Получение аэродинамических параметров для посадочной конфигурации
            C_D_0_landing = data.aero_analysis_data.C_D_0_landing
            K_landing = data.aero_analysis_data.K_landing

            if not C_D_0_landing or not K_landing:
                # Получаем базовые параметры из предыдущих блоков
                base_C_D_0 = data.cruise_data.C_D_0
                base_K = data.cruise_data.K
                wing_flaps_type = data.landing_data.wing_flaps_type
                aircraft_type = data.landing_data.aircraft_type

                if not base_C_D_0 or not base_K:
                    # Используем значения по умолчанию
                    defaults = self._get_default_aero_params(aircraft_type)
                    base_C_D_0 = base_C_D_0 or defaults['C_D_0']
                    base_K = base_K or defaults['K']

                # Рассчитываем добавки для посадочной конфигурации
                flap_increment = self._get_flap_drag_increment(wing_flaps_type)
                gear_increment = 0.015  # Типичная добавка от выпущенного шасси

                if not C_D_0_landing:
                    C_D_0_landing = base_C_D_0 + flap_increment + gear_increment
                    data.aero_analysis_data.C_D_0_landing = C_D_0_landing
                    data.aero_analysis_data.delta_C_D_0_flaps = flap_increment
                    data.aero_analysis_data.delta_C_D_0_gear = gear_increment

                if not K_landing:
                    # K увеличивается из-за интерференции закрылок и шасси
                    K_landing = base_K * 1.1  # 10% увеличение
                    data.aero_analysis_data.K_landing = K_landing

            # Шаг 3: Расчёт коэффициента подъёмной силы по формуле 5.11
            # C_L = (2*W/S) / (ρ*V²)
            # Используем отношение m_ML/m_MTO для посадочной массы
            m_ML_m_MTO_ratio = data.landing_data.m_ML_per_m_MTO_ratio or 0.85  # Типичное значение
            wing_loading_landing = data.m_MTO_per_S_W * m_ML_m_MTO_ratio

            g = 9.81  # м/с²
            C_L_ma = (2 * wing_loading_landing * g) / (rho_ma * V_ma**2)

            data.aero_analysis_data.C_L_ma = C_L_ma

            # Проверка разумности C_L
            if C_L_ma <= 0 or C_L_ma > 5.0: # todo: что-то с расчётом сделать
                raise CalculationError(
                    f"Недопустимое значение C_L_ma = {C_L_ma:.3f} (должно быть от 0 до 3.0)",
                    self.name,
                    {
                        'wing_loading_landing': wing_loading_landing,
                        'rho_ma': rho_ma,
                        'V_ma': V_ma,
                        'C_L_ma': C_L_ma
                    }
                )

            # Шаг 4: Расчёт аэродинамического качества по формуле 5.12
            # E = C_L / (C_D_0 + K*C_L²)
            C_D_total = C_D_0_landing + K_landing * C_L_ma**2
            E_ma = C_L_ma / C_D_total

            if E_ma <= 0:
                raise CalculationError(
                    "Получено отрицательное или нулевое аэродинамическое качество E_ma",
                    self.name,
                    {
                        'C_L_ma': C_L_ma,
                        'C_D_0_landing': C_D_0_landing,
                        'K_landing': K_landing,
                        'C_D_total': C_D_total,
                        'E_ma': E_ma
                    }
                )

            # Проверка разумности результата
            if E_ma > 25:
                print(f"Предупреждение: высокое аэродинамическое качество E_ma = {E_ma:.2f}")

            if E_ma < 3:
                print(f"Предупреждение: низкое аэродинамическое качество E_ma = {E_ma:.2f}")

            # Сохранение результатов
            data.aero_analysis_data.E_ma = E_ma

            print(f"Блок 6 - Результат: E_ma = {E_ma:.2f} (посадочная конфигурация)")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def _get_default_aero_params(self, aircraft_type: AircraftTypeEnum) -> Dict[str, float]:
        """Получение аэродинамических параметров по умолчанию"""
        defaults_by_type = {
            AircraftTypeEnum.BUSINESS_JET: {'C_D_0': 0.025, 'K': 0.045},
            AircraftTypeEnum.SHORT_RANGE_JET_TRANSPORT: {'C_D_0': 0.020, 'K': 0.040},
            AircraftTypeEnum.MEDIUM_RANGE_JET_TRANSPORT: {'C_D_0': 0.018, 'K': 0.038},
            AircraftTypeEnum.LONG_RANGE_JET_TRANSPORT: {'C_D_0': 0.016, 'K': 0.035},
            AircraftTypeEnum.ULTRA_LONG_RANGE_JET_TRANSPORT: {'C_D_0': 0.014, 'K': 0.032},
            AircraftTypeEnum.FIGHTER: {'C_D_0': 0.020, 'K': 0.050},
            AircraftTypeEnum.SUPERSONIC_CRUISE: {'C_D_0': 0.022, 'K': 0.048}
        }

        return defaults_by_type.get(aircraft_type, {'C_D_0': 0.025, 'K': 0.045})

    def _get_flap_drag_increment(self, wing_flaps_type: WingFlapsTypeEnum) -> float:
        """Получение добавки к C_D_0 от закрылок в посадочной конфигурации"""
        # Типичные добавки для посадочной конфигурации (полный выпуск)
        flap_increments = {
            WingFlapsTypeEnum.CLEAN_AIRFOIL: 0.000,
            WingFlapsTypeEnum.PLAIN_FLAP: 0.020,
            WingFlapsTypeEnum.SPLIT_FLAP: 0.025,
            WingFlapsTypeEnum.SLOTTED_FLAP: 0.030,
            WingFlapsTypeEnum.FOWLER_FLAP: 0.035,
            WingFlapsTypeEnum.DOUBLE_SLOTTED_FLAP: 0.040,
            WingFlapsTypeEnum.TRIPLE_SLOTTED_FLAP: 0.045
        }

        return flap_increments.get(wing_flaps_type, 0.030)  # По умолчанию 0.030

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """Подробная сводка результатов расчёта"""
        base_summary = super().get_calculation_summary(data)

        if data.aero_analysis_data.E_ma is not None:
            base_summary['calculation_details'] = {
                'input_parameters': {
                    'V_ma': f"{data.aero_analysis_data.V_ma} м/с" if data.aero_analysis_data.V_ma else "Не указана",
                    'h_ma': f"{data.aero_analysis_data.h_ma or 0} м",
                    'wing_loading': f"{data.m_MTO_per_S_W:.2f} кг/м²" if data.m_MTO_per_S_W else "Не определена"
                },
                'atmospheric_conditions': {
                    'rho_ma': f"{data.aero_analysis_data.rho_ma:.4f} кг/м³" if data.aero_analysis_data.rho_ma else "Не вычислена"
                },
                'aerodynamic_parameters_landing': {
                    'C_D_0_landing': f"{data.aero_analysis_data.C_D_0_landing:.4f}" if data.aero_analysis_data.C_D_0_landing else "Не определён",
                    'K_landing': f"{data.aero_analysis_data.K_landing:.4f}" if data.aero_analysis_data.K_landing else "Не определён",
                    'C_L_ma': f"{data.aero_analysis_data.C_L_ma:.4f}" if data.aero_analysis_data.C_L_ma else "Не вычислен",
                    'delta_C_D_0_flaps': f"{data.aero_analysis_data.delta_C_D_0_flaps:.4f}" if data.aero_analysis_data.delta_C_D_0_flaps else "Не определена",
                    'delta_C_D_0_gear': f"{data.aero_analysis_data.delta_C_D_0_gear:.4f}" if data.aero_analysis_data.delta_C_D_0_gear else "Не определена"
                },
                'final_result': {
                    'E_ma': f"{data.aero_analysis_data.E_ma:.2f}",
                    'description': 'Аэродинамическое качество в посадочной конфигурации для формулы 5.24'
                },
                'equations_used': [
                    'C_L = (2*W/S) / (ρ*V²) (формула 5.11)',
                    'E = C_L / (C_D_0 + K*C_L²) (формула 5.12)',
                    'C_D_0_landing = C_D_0_base + ΔC_D_0_flaps + ΔC_D_0_gear'
                ],
                'configuration_notes': [
                    'Посадочная конфигурация: закрылки и шасси выпущены',
                    'Используется посадочная масса (m_ML = m_MTO * коэффициент)',
                    'Результат E_ma используется в блоке 7 для формулы 5.24'
                ]
            }

        return base_summary