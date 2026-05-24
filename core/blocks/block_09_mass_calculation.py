from typing import Dict, Any, List
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError


class Block09MassCalculation(BaseBlock):
    """
    Блок 9: Расчёт максимальной взлётной массы (раздел 5.9 методики)
    Итеративное решение формулы 5.45 с использованием формул 5.49 и 5.52
    """

    @property
    def name(self) -> str:
        return "Расчёт максимальной взлётной массы"

    @property
    def block_number(self) -> int:
        return 9

    @property
    def required_inputs(self) -> List[str]:
        return [
            "optimal_tw_ratio",                        # Результат блока 8
            "mass_calculation_data.payload_mass"       # Масса полезной нагрузки
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "mass_calculation_data.design_range",      # Расчётная дальность
            "mass_calculation_data.cruise_mach",       # Крейсерский Маха
            "mass_calculation_data.sfc_cruise",        # Удельный расход топлива
            "mass_calculation_data.L_D_cruise"         # Аэродинамическое качество
        ]

    @property
    def outputs(self) -> List[str]:
        return ["m_MTO"]

    def calculate(self, data: ProjectData) -> None:
        """
        Итеративное решение формулы 5.45 из методики:
        m_MTO = m_PL / (1 - m_OE/m_MTO - m_F/m_MTO)

        Где:
        - m_OE/m_MTO = 0.23 + 1.04 * T/W  [формула 5.49]
        - m_F/m_MTO = 1 - M_ff  [формула 5.52]
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Проверка зависимостей от блока 8
            if data.optimal_tw_ratio is None:
                raise CalculationError(
                    "Отсутствует результат блока 8 (optimal_tw_ratio). "
                    "Необходимо сначала построить диаграмму согласования.",
                    self.name
                )

            # Получение входных данных
            tw_ratio = data.optimal_tw_ratio
            payload_mass = data.mass_calculation_data.payload_mass

            if not payload_mass or payload_mass <= 0:
                raise CalculationError(
                    "Отсутствует или некорректная масса полезной нагрузки",
                    self.name
                )

            # Получение дополнительных параметров или использование значений по умолчанию
            design_range = data.mass_calculation_data.design_range or 5000  # км
            cruise_mach = data.mass_calculation_data.cruise_mach or 0.8
            sfc_cruise = data.mass_calculation_data.sfc_cruise or 0.5  # фунт/(фунт·ч) = 14.2 мг/(Н·с)
            L_D_cruise = data.mass_calculation_data.L_D_cruise or data.cruise_data.E_max or 18.0

            # Сохраняем использованные значения
            data.mass_calculation_data.design_range = design_range
            data.mass_calculation_data.cruise_mach = cruise_mach
            data.mass_calculation_data.sfc_cruise = sfc_cruise
            data.mass_calculation_data.L_D_cruise = L_D_cruise

            # Расчёт относительной массы пустого самолёта по формуле 5.49
            relative_oe_mass = 0.23 + 1.04 * tw_ratio
            data.mass_calculation_data.relative_oe_mass = relative_oe_mass

            # Расчёт относительной массы топлива
            relative_fuel_mass = self._calculate_relative_fuel_mass(
                design_range, cruise_mach, sfc_cruise, L_D_cruise, data
            )
            data.mass_calculation_data.relative_fuel_mass = relative_fuel_mass

            # Проверка физической корректности
            total_relative_mass = relative_oe_mass + relative_fuel_mass
            if total_relative_mass >= 1.0:
                raise CalculationError(
                    f"Сумма относительных масс превышает 100%: "
                    f"пустой самолёт {relative_oe_mass:.3f} + топливо {relative_fuel_mass:.3f} = {total_relative_mass:.3f}",
                    self.name,
                    {
                        'relative_oe_mass': relative_oe_mass,
                        'relative_fuel_mass': relative_fuel_mass,
                        'sum': total_relative_mass
                    }
                )

            # Итеративное решение формулы 5.45
            mto_mass = self._solve_mto_iteratively(payload_mass, relative_oe_mass, relative_fuel_mass, data)

            # Проверка разумности результата
            if mto_mass <= payload_mass or mto_mass > payload_mass * 10:
                raise CalculationError(
                    f"Неразумное значение максимальной взлётной массы: {mto_mass:.0f} кг "
                    f"при полезной нагрузке {payload_mass:.0f} кг",
                    self.name,
                    {'mto_mass': mto_mass, 'payload_mass': payload_mass}
                )

            # Сохранение результатов
            data.m_MTO = mto_mass
            data.mass_calculation_data.calculated_mto_mass = mto_mass

            # Расчёт компонентов массы для справки
            oe_mass = mto_mass * relative_oe_mass
            fuel_mass = mto_mass * relative_fuel_mass

            data.final_parameters_data.operating_empty_mass = oe_mass
            data.final_parameters_data.fuel_mass = fuel_mass
            data.final_parameters_data.landing_mass = mto_mass - fuel_mass * 0.8  # Примерно 80% топлива сжигается

            print(f"Блок 9 - Результат: m_MTO = {mto_mass:.0f} кг")
            print(f"Блок 9 - Компоненты: полезная нагрузка = {payload_mass:.0f} кг, "
                  f"пустой самолёт = {oe_mass:.0f} кг, топливо = {fuel_mass:.0f} кг")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def _calculate_relative_fuel_mass(self, design_range: float, cruise_mach: float,
                                     sfc_cruise: float, L_D_cruise: float, data: ProjectData) -> float:
        """
        Расчёт относительной массы топлива с использованием формулы Бреге
        """
        # Фактор Бреге для реактивных двигателей (формула 5.53)
        # B = (L/D) / (SFC * g) * V

        # Приближённая скорость крейсера
        cruise_altitude = data.cruise_data.h_cruise or 11000  # м

        # Скорость звука на высоте (упрощённо)
        if cruise_altitude <= 11000:
            temperature = 288.15 - 0.0065 * cruise_altitude  # К
        else:
            temperature = 216.65  # К (стратосфера)

        speed_of_sound = math.sqrt(1.4 * 287 * temperature)  # м/с
        cruise_speed = cruise_mach * speed_of_sound  # м/с

        # Конвертация SFC из фунт/(фунт·ч) в м/с (СИ)
        sfc_si = sfc_cruise * 2.78e-6  # приблизительная конвертация
        g = 9.81  # м/с²

        # Фактор Бреге
        breguet_factor = L_D_cruise * cruise_speed / (sfc_si * g)
        data.mass_calculation_data.breguet_factor = breguet_factor

        # Дальность в метрах
        range_m = design_range * 1000

        # Mission fuel fraction по формуле 5.55
        # m_CR/m_LOI = exp(-R_CR/B)
        mission_fuel_fraction = math.exp(-range_m / breguet_factor)
        data.mass_calculation_data.mission_fuel_fraction = mission_fuel_fraction

        # Учёт других фаз полёта (взлёт, набор, снижение, запас)
        # Используем типичные значения из таблицы 5.9
        takeoff_factor = 0.995
        climb_factor = 0.98
        descent_factor = 0.99
        reserves_factor = 0.95  # 5% запас топлива

        total_mission_factor = (takeoff_factor * climb_factor * mission_fuel_fraction *
                               descent_factor * reserves_factor)

        # Относительная масса топлива по формуле 5.52
        relative_fuel_mass = 1 - total_mission_factor

        return min(relative_fuel_mass, 0.6)  # Ограничение 60% максимум

    def _solve_mto_iteratively(self, payload_mass: float, relative_oe_mass: float,
                              relative_fuel_mass: float, data: ProjectData) -> float:
        """
        Итеративное решение формулы 5.45 методики
        """
        # Начальное приближение
        mto_guess = payload_mass / (1 - relative_oe_mass - relative_fuel_mass)

        # Итеративный процесс (формула 5.49 зависит от T/W, который может зависеть от массы)
        max_iterations = 20
        tolerance = 1.0  # кг

        for iteration in range(max_iterations):
            # Пересчитываем относительную массу пустого самолёта
            # (в простой версии она постоянна, но в более сложной может зависеть от массы)
            current_relative_oe = relative_oe_mass
            current_relative_fuel = relative_fuel_mass

            # Новое приближение по формуле 5.45
            new_mto = payload_mass / (1 - current_relative_oe - current_relative_fuel)

            # Проверка сходимости
            if abs(new_mto - mto_guess) < tolerance:
                data.mass_calculation_data.iteration_count = iteration + 1
                return new_mto

            mto_guess = new_mto

        # Если не сошлось, возвращаем последнее значение с предупреждением
        print(f"Предупреждение: итерационный процесс не сошёлся за {max_iterations} итераций")
        data.mass_calculation_data.iteration_count = max_iterations
        return mto_guess

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """Подробная сводка результатов расчёта"""
        base_summary = super().get_calculation_summary(data)

        if data.m_MTO is not None:
            base_summary['calculation_details'] = {
                'input_parameters': {
                    'optimal_tw_ratio': f"{data.optimal_tw_ratio:.4f}" if data.optimal_tw_ratio else "Не определён",
                    'payload_mass': f"{data.mass_calculation_data.payload_mass:.0f} кг" if data.mass_calculation_data.payload_mass else "Не указана",
                    'design_range': f"{data.mass_calculation_data.design_range:.0f} км" if data.mass_calculation_data.design_range else "Не указана",
                    'cruise_mach': f"{data.mass_calculation_data.cruise_mach:.2f}" if data.mass_calculation_data.cruise_mach else "Не указан"
                },
                'mass_breakdown': {
                    'relative_oe_mass': f"{data.mass_calculation_data.relative_oe_mass:.3f} ({data.mass_calculation_data.relative_oe_mass*100:.1f}%)" if data.mass_calculation_data.relative_oe_mass else "Не вычислена",
                    'relative_fuel_mass': f"{data.mass_calculation_data.relative_fuel_mass:.3f} ({data.mass_calculation_data.relative_fuel_mass*100:.1f}%)" if data.mass_calculation_data.relative_fuel_mass else "Не вычислена",
                    'payload_fraction': f"{data.mass_calculation_data.payload_mass/data.m_MTO:.3f} ({data.mass_calculation_data.payload_mass/data.m_MTO*100:.1f}%)" if data.m_MTO else "Не вычислена"
                },
                'iteration_details': {
                    'iteration_count': f"{data.mass_calculation_data.iteration_count}" if data.mass_calculation_data.iteration_count else "Не определено",
                    'mission_fuel_fraction': f"{data.mass_calculation_data.mission_fuel_fraction:.4f}" if data.mass_calculation_data.mission_fuel_fraction else "Не вычислена",
                    'breguet_factor': f"{data.mass_calculation_data.breguet_factor:.0f} м" if data.mass_calculation_data.breguet_factor else "Не вычислен"
                },
                'final_masses': {
                    'mto_mass': f"{data.m_MTO:.0f} кг",
                    'operating_empty_mass': f"{data.final_parameters_data.operating_empty_mass:.0f} кг" if data.final_parameters_data.operating_empty_mass else "Не вычислена",
                    'fuel_mass': f"{data.final_parameters_data.fuel_mass:.0f} кг" if data.final_parameters_data.fuel_mass else "Не вычислена",
                    'landing_mass': f"{data.final_parameters_data.landing_mass:.0f} кг" if data.final_parameters_data.landing_mass else "Не вычислена"
                },
                'equations_used': [
                    'm_MTO = m_PL / (1 - m_OE/m_MTO - m_F/m_MTO) (формула 5.45)',
                    'm_OE/m_MTO = 0.23 + 1.04 × T/W (формула 5.49)',
                    'm_F/m_MTO = 1 - M_ff (формула 5.52)',
                    'M_ff = exp(-R/B) × факторы_фаз_полёта (формула 5.55)'
                ]
            }

        return base_summary