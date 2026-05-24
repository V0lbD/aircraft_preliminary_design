from typing import Dict, Any, List
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData, AircraftTypeEnum
from core.statistics_database import StatisticsDatabase
from core.exceptions import CalculationError


class Block04CruiseClimb(BaseBlock):
    """
    Блок 4: Крейсерский режим и финальный расчёт тяговооружённости
    Реализует формулы 5.14 и расчёт T/W для крейсера
    """

    @property
    def name(self) -> str:
        return "Крейсер и тяговооружённость"

    @property
    def block_number(self) -> int:
        return 4

    @property
    def required_inputs(self) -> List[str]:
        return [
            "cruise_data.V_cruise",     # Крейсерская скорость
            "cruise_data.h_cruise",     # Крейсерская высота
            "climb_data.n_engines",     # Количество двигателей (из блока 3)
            "climb_data.gamma_sin"      # sin(γ) (из блока 3)
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "cruise_data.C_D_0",        # Коэффициент лобового сопротивления
            "cruise_data.K"             # Коэффициент индуктивного сопротивления
        ]

    @property
    def outputs(self) -> List[str]:
        return ["T_W_climb"]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет расчёт T/W по формуле 5.14 и для крейсера

        Формула 5.14: T/(m_MTO*g) = (n_E/(n_E-1)) * (sin(γ) + 1/E)
        где E - аэродинамическое качество
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Проверка зависимостей от блока 3
            n_engines = data.climb_data.n_engines
            gamma_sin = data.climb_data.gamma_sin

            if not n_engines or gamma_sin is None:
                raise CalculationError(
                    "Отсутствуют результаты блока 3 (n_engines, gamma_sin). "
                    "Необходимо сначала выполнить расчёт параметров набора высоты.",
                    self.name
                )

            # Получение параметров крейсера
            V_cruise = data.cruise_data.V_cruise
            h_cruise = data.cruise_data.h_cruise

            if not V_cruise or not h_cruise:
                raise CalculationError(
                    "Отсутствуют обязательные данные: V_cruise и h_cruise",
                    self.name
                )

            # Шаг 1: Расчёт плотности воздуха на крейсерской высоте
            # Стандартная атмосфера: ρ = ρ_0 * (1 - h/44300)^4.256
            rho_0 = 1.225  # кг/м³
            sigma_h = (1 - h_cruise / 44300) ** 4.256
            rho_h = rho_0 * sigma_h

            data.cruise_data.rho_h = rho_h
            data.cruise_data.sigma_h = sigma_h

            # Шаг 2: Получение аэродинамических параметров
            C_D_0 = data.cruise_data.C_D_0
            K = data.cruise_data.K

            if not C_D_0 or not K:
                # Получаем из базы данных по типу самолёта
                aircraft_type = (data.landing_data.aircraft_type or
                                 data.takeoff_data.aircraft_type or
                                 AircraftTypeEnum.BUSINESS_JET)

                defaults = self._get_aero_parameters(aircraft_type)

                if not C_D_0:
                    C_D_0 = defaults['C_D_0']
                    data.cruise_data.C_D_0 = C_D_0

                if not K:
                    K = defaults['K']
                    data.cruise_data.K = K

            # Шаг 3: Расчёт коэффициента подъёмной силы в крейсере
            # Из условия равновесия: L = W, L = 0.5 * ρ * V² * S * C_L
            # Нужно предположить wing loading для расчёта C_L
            if data.m_MTO_per_S_W:
                # Используем результат блока 1 как базу
                wing_loading = data.m_MTO_per_S_W  # кг/м²
                # C_L = (2 * W/S) / (ρ * V²) = (2 * wing_loading * g) / (ρ * V²)
                g = 9.81  # м/с²
                C_L_cruise = (2 * wing_loading * g) / (rho_h * V_cruise**2)
            else:
                # Используем оптимальный C_L для крейсера
                C_L_cruise = math.sqrt(C_D_0 / K)

            data.cruise_data.C_L_cruise = C_L_cruise

            # Шаг 4: Расчёт аэродинамического качества E
            # E = L/D = C_L / C_D = C_L / (C_D_0 + K * C_L²)
            C_D_total = C_D_0 + K * C_L_cruise**2
            E_max = C_L_cruise / C_D_total

            data.cruise_data.E_max = E_max

            if E_max <= 0:
                raise CalculationError(
                    "Получено отрицательное или нулевое аэродинамическое качество",
                    self.name,
                    {'C_L_cruise': C_L_cruise, 'C_D_total': C_D_total, 'E_max': E_max}
                )

            # Шаг 5: Формула 5.14 - расчёт T/W для набора высоты
            # T/(m_MTO*g) = (n_E/(n_E-1)) * (sin(γ) + 1/E)
            if n_engines == 1:
                # Для однодвигательного самолёта формула упрощается
                T_W_climb = gamma_sin + (1 / E_max)
            else:
                T_W_climb = (n_engines / (n_engines - 1)) * (gamma_sin + (1 / E_max))

            # Шаг 6: Расчёт T/W для крейсера (горизонтальный полёт)
            # T/W = 1/E для установившегося горизонтального полёта
            T_W_cruise = 1 / E_max

            # Поправка на высоту для тяги двигателей
            T_W_cruise = T_W_cruise / sigma_h  # Учитываем падение тяги с высотой

            # Окончательное T/W - максимальное из условий набора и крейсера
            final_T_W = max(T_W_climb, T_W_cruise)

            # Сохранение результатов
            data.cruise_data.T_W_cruise = T_W_cruise
            data.cruise_data.T_W_climb_final = T_W_climb
            data.T_W_climb = final_T_W

            print(f"Блок 4 - T/W набор: {T_W_climb:.4f}, T/W крейсер: {T_W_cruise:.4f}")
            print(f"Блок 4 - Итоговый T/W: {final_T_W:.4f}")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def _get_aero_parameters(self, aircraft_type: AircraftTypeEnum) -> Dict[str, float]:
        """Получение аэродинамических параметров по типу самолёта"""
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

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """Подробная сводка результатов расчёта"""
        base_summary = super().get_calculation_summary(data)

        if data.T_W_climb is not None:
            base_summary['calculation_details'] = {
                'input_parameters': {
                    'V_cruise': f"{data.cruise_data.V_cruise} м/с" if data.cruise_data.V_cruise else "Не указана",
                    'h_cruise': f"{data.cruise_data.h_cruise} м" if data.cruise_data.h_cruise else "Не указана",
                    'n_engines': f"{data.climb_data.n_engines}" if data.climb_data.n_engines else "Не указано",
                    'gamma_sin': f"{data.climb_data.gamma_sin:.4f}" if data.climb_data.gamma_sin else "Не указан"
                },
                'atmospheric_conditions': {
                    'sigma_h': f"{data.cruise_data.sigma_h:.4f}" if data.cruise_data.sigma_h else "Не вычислена",
                    'rho_h': f"{data.cruise_data.rho_h:.4f} кг/м³" if data.cruise_data.rho_h else "Не вычислена"
                },
                'aerodynamic_parameters': {
                    'C_D_0': f"{data.cruise_data.C_D_0:.4f}" if data.cruise_data.C_D_0 else "Не определён",
                    'K': f"{data.cruise_data.K:.4f}" if data.cruise_data.K else "Не определён",
                    'C_L_cruise': f"{data.cruise_data.C_L_cruise:.4f}" if data.cruise_data.C_L_cruise else "Не вычислен",
                    'E_max': f"{data.cruise_data.E_max:.2f}" if data.cruise_data.E_max else "Не вычислено"
                },
                'results': {
                    'T_W_climb': f"{data.cruise_data.T_W_climb_final:.4f}" if data.cruise_data.T_W_climb_final else "Не вычислено",
                    'T_W_cruise': f"{data.cruise_data.T_W_cruise:.4f}" if data.cruise_data.T_W_cruise else "Не вычислено",
                    'T_W_final': f"{data.T_W_climb:.4f}",
                    'description': 'Максимальное отношение T/W из условий набора и крейсера'
                },
                'equations_used': [
                    'σ_h = (1 - h/44300)^4.256',
                    'E = C_L / (C_D_0 + K*C_L²)',
                    'T/W_climb = (n_E/(n_E-1)) * (sin(γ) + 1/E)',  # Формула 5.14
                    'T/W_cruise = 1/E / σ_h',
                    'T/W_final = max(T/W_climb, T/W_cruise)'
                ]
            }

        return base_summary