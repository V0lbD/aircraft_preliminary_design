from typing import Dict, Any, List
import math
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError


class Block10FinalParameters(BaseBlock):
    """
    Блок 10: Финальные параметры самолёта (раздел 5.10 методики)
    Расчёт взлётной тяги и площади крыла по формулам 5.56-5.57
    """

    @property
    def name(self) -> str:
        return "Финальные параметры"

    @property
    def block_number(self) -> int:
        return 10

    @property
    def required_inputs(self) -> List[str]:
        return [
            "m_MTO",                          # Результат блока 9
            "optimal_tw_ratio",               # Результат блока 8
            "optimal_wing_loading"            # Результат блока 8
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return []

    @property
    def outputs(self) -> List[str]:
        return ["T_TO", "S_W"]

    def calculate(self, data: ProjectData) -> None:
        """
        Расчёт финальных параметров по формулам методики:

        Формула 5.56: T_TO = (T/W) × m_MTO × g
        Формула 5.57: S_W = m_MTO / Wing_Loading
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
            missing_data = []

            if data.m_MTO is None:
                missing_data.append("Блок 9 (m_MTO)")
            if data.optimal_tw_ratio is None:
                missing_data.append("Блок 8 (optimal_tw_ratio)")
            if data.optimal_wing_loading is None:
                missing_data.append("Блок 8 (optimal_wing_loading)")

            if missing_data:
                raise CalculationError(
                    f"Отсутствуют результаты от блоков: {', '.join(missing_data)}. "
                    "Необходимо завершить расчёты предыдущих блоков.",
                    self.name
                )

            # Получение входных данных
            mto_mass = data.m_MTO
            tw_ratio = data.optimal_tw_ratio
            wing_loading = data.optimal_wing_loading

            # Проверка разумности входных данных
            if mto_mass <= 0:
                raise CalculationError(f"Недопустимая максимальная взлётная масса: {mto_mass} кг", self.name)

            if tw_ratio <= 0 or tw_ratio > 2.0:
                raise CalculationError(f"Недопустимое отношение T/W: {tw_ratio}", self.name)

            if wing_loading <= 0 or wing_loading > 2000:
                raise CalculationError(f"Недопустимая нагрузка на крыло: {wing_loading} кг/м²", self.name)

            # Расчёт взлётной тяги по формуле 5.56
            g = 9.81  # м/с² (ускорение свободного падения)
            takeoff_thrust = tw_ratio * mto_mass * g

            # Расчёт площади крыла по формуле 5.57
            wing_area = mto_mass / wing_loading

            # Проверка разумности результатов
            if takeoff_thrust <= 0 or takeoff_thrust > mto_mass * 20:  # T/W не должно превышать 2.0
                raise CalculationError(
                    f"Неразумное значение взлётной тяги: {takeoff_thrust:.0f} Н",
                    self.name,
                    {'takeoff_thrust': takeoff_thrust, 'mto_mass': mto_mass, 'tw_ratio': tw_ratio}
                )

            if wing_area <= 0 or wing_area > 2000:  # Разумные пределы для площади крыла
                raise CalculationError(
                    f"Неразумное значение площади крыла: {wing_area:.1f} м²",
                    self.name,
                    {'wing_area': wing_area, 'mto_mass': mto_mass, 'wing_loading': wing_loading}
                )

            # Сохранение основных результатов
            data.T_TO = takeoff_thrust
            data.S_W = wing_area
            data.final_parameters_data.final_takeoff_thrust = takeoff_thrust
            data.final_parameters_data.final_wing_area = wing_area

            # Сохранение финальных удельных характеристик
            data.final_parameters_data.thrust_to_weight_final = tw_ratio
            data.final_parameters_data.wing_loading_final = wing_loading

            # Дополнительные вычисления для полноты картины
            self._calculate_additional_parameters(data)

            # Отметка о завершении всех расчётов
            data.calculation_complete = True

            print(f"Блок 10 - Результат: T_TO = {takeoff_thrust:.0f} Н ({takeoff_thrust/1000:.1f} кН)")
            print(f"Блок 10 - Результат: S_W = {wing_area:.1f} м²")
            print(f"Блок 10 - Завершение: Preliminary Sizing выполнен полностью!")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def _calculate_additional_parameters(self, data: ProjectData) -> None:
        """
        Расчёт дополнительных параметров для полной характеристики самолёта
        """
        mto_mass = data.m_MTO

        # Основные массы (если ещё не рассчитаны)
        if not data.final_parameters_data.operating_empty_mass:
            relative_oe = data.mass_calculation_data.relative_oe_mass or 0.55
            data.final_parameters_data.operating_empty_mass = mto_mass * relative_oe

        if not data.final_parameters_data.fuel_mass:
            relative_fuel = data.mass_calculation_data.relative_fuel_mass or 0.30
            data.final_parameters_data.fuel_mass = mto_mass * relative_fuel

        if not data.final_parameters_data.landing_mass:
            fuel_mass = data.final_parameters_data.fuel_mass
            # Предполагаем, что 80% топлива сжигается до посадки
            remaining_fuel = fuel_mass * 0.2 if fuel_mass else mto_mass * 0.06
            data.final_parameters_data.landing_mass = mto_mass - fuel_mass + remaining_fuel

        # Удельные характеристики
        wing_area = data.S_W
        takeoff_thrust = data.T_TO

        # Нагрузка на крыло при посадочной массе
        landing_mass = data.final_parameters_data.landing_mass
        if landing_mass and wing_area:
            landing_wing_loading = landing_mass / wing_area
            # Можно добавить в данные, если нужно

        # Удельная тяга (тяга на единицу площади крыла)
        if wing_area:
            thrust_loading = takeoff_thrust / wing_area  # Н/м²
            # Можно добавить в данные, если нужно

    def get_final_aircraft_summary(self, data: ProjectData) -> Dict[str, Any]:
        """
        Получение полной сводки параметров самолёта
        """
        if not data.calculation_complete:
            return {"status": "calculation_incomplete"}

        return {
            "design_summary": {
                "aircraft_type": data.landing_data.aircraft_type.value if data.landing_data.aircraft_type else "Не определён",
                "engine_type": data.landing_data.engine_type.value if data.landing_data.engine_type else "Не определён",
                "number_of_engines": data.climb_data.n_engines or "Не определено",
                "wing_flaps_type": data.landing_data.wing_flaps_type.value if data.landing_data.wing_flaps_type else "Не определён"
            },
            "mass_characteristics": {
                "maximum_takeoff_mass": f"{data.m_MTO:.0f} кг",
                "operating_empty_mass": f"{data.final_parameters_data.operating_empty_mass:.0f} кг" if data.final_parameters_data.operating_empty_mass else "Не вычислена",
                "fuel_mass": f"{data.final_parameters_data.fuel_mass:.0f} кг" if data.final_parameters_data.fuel_mass else "Не вычислена",
                "payload_mass": f"{data.mass_calculation_data.payload_mass:.0f} кг" if data.mass_calculation_data.payload_mass else "Не указана",
                "landing_mass": f"{data.final_parameters_data.landing_mass:.0f} кг" if data.final_parameters_data.landing_mass else "Не вычислена"
            },
            "geometric_characteristics": {
                "wing_area": f"{data.S_W:.1f} м²",
                "wing_loading": f"{data.optimal_wing_loading:.1f} кг/м²"
            },
            "propulsion_characteristics": {
                "takeoff_thrust_total": f"{data.T_TO:.0f} Н ({data.T_TO/1000:.1f} кН)",
                "takeoff_thrust_per_engine": f"{data.T_TO/data.climb_data.n_engines:.0f} Н ({data.T_TO/data.climb_data.n_engines/1000:.1f} кН)" if data.climb_data.n_engines else "Не определена",
                "thrust_to_weight_ratio": f"{data.optimal_tw_ratio:.4f}"
            },
            "performance_requirements": {
                "design_range": f"{data.mass_calculation_data.design_range:.0f} км" if data.mass_calculation_data.design_range else "Не указана",
                "cruise_mach": f"{data.mass_calculation_data.cruise_mach:.2f}" if data.mass_calculation_data.cruise_mach else "Не указан",
                "cruise_altitude": f"{data.cruise_data.h_cruise:.0f} м" if data.cruise_data.h_cruise else "Не указана",
                "landing_distance": f"{data.landing_data.s_LFL:.0f} м" if data.landing_data.s_LFL else "Не указана",
                "takeoff_distance": f"{data.takeoff_data.s_TOFL:.0f} м" if data.takeoff_data.s_TOFL else "Не указана"
            },
            "calculation_status": {
                "all_blocks_completed": True,
                "preliminary_sizing_complete": data.calculation_complete
            }
        }

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """Подробная сводка результатов расчёта"""
        base_summary = super().get_calculation_summary(data)

        if data.T_TO is not None and data.S_W is not None:
            base_summary['calculation_details'] = {
                'input_parameters': {
                    'm_MTO': f"{data.m_MTO:.0f} кг" if data.m_MTO else "Не определена",
                    'optimal_tw_ratio': f"{data.optimal_tw_ratio:.4f}" if data.optimal_tw_ratio else "Не определён",
                    'optimal_wing_loading': f"{data.optimal_wing_loading:.1f} кг/м²" if data.optimal_wing_loading else "Не определена"
                },
                'calculations': {
                    'takeoff_thrust_formula': f"T_TO = {data.optimal_tw_ratio:.4f} × {data.m_MTO:.0f} × 9.81 = {data.T_TO:.0f} Н",
                    'wing_area_formula': f"S_W = {data.m_MTO:.0f} / {data.optimal_wing_loading:.1f} = {data.S_W:.1f} м²"
                },
                'final_results': {
                    'takeoff_thrust': f"{data.T_TO:.0f} Н ({data.T_TO/1000:.1f} кН)",
                    'thrust_per_engine': f"{data.T_TO/data.climb_data.n_engines:.0f} Н ({data.T_TO/data.climb_data.n_engines/1000:.1f} кН)" if data.climb_data.n_engines else "Не определена",
                    'wing_area': f"{data.S_W:.1f} м²",
                    'wing_span_estimate': f"{math.sqrt(data.S_W * 8):.1f} м (при A=8)" if data.S_W else "Не определён"  # Примерная оценка размаха
                },
                'additional_parameters': {
                    'operating_empty_mass': f"{data.final_parameters_data.operating_empty_mass:.0f} кг" if data.final_parameters_data.operating_empty_mass else "Не вычислена",
                    'fuel_mass': f"{data.final_parameters_data.fuel_mass:.0f} кг" if data.final_parameters_data.fuel_mass else "Не вычислена",
                    'landing_mass': f"{data.final_parameters_data.landing_mass:.0f} кг" if data.final_parameters_data.landing_mass else "Не вычислена"
                },
                'equations_used': [
                    'T_TO = (T/W) × m_MTO × g (формула 5.56)',
                    'S_W = m_MTO / Wing_Loading (формула 5.57)'
                ],
                'completion_status': {
                    'preliminary_sizing_complete': data.calculation_complete,
                    'all_parameters_calculated': True
                }
            }

        return base_summary