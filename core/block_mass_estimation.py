import math
from typing import Dict, Any, List

from reportlab.platypus.figures import demo1

from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError
from core.constants import PI, g

class BlockMassEstimation(BaseBlock):

    def __init__(self):
        """Инициализирует движок расчётов масс"""
        super().__init__()

        self.calculation_log: List[str] = []
        self.errors: List[str] = []

    @property
    def name(self) -> str:
        return "Оценка масс"

    @property
    def block_number(self) -> int:
        return 2

    @property
    def required_inputs(self) -> List[str]:
        return [
            # "p0_optimal",  # Удельная нагрузка на крыло из предварительного расчёта [Н/м²]
            # "P0_optimal",  # Тяговооружённость из предварительного расчёта [-]
            # "payload_mass",  # Масса полезной нагрузки [кг]
            # "design_range",  # Дальность полёта [км]
            # "N",  # Количество двигателей
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return []

    @property
    def outputs(self) -> List[str]:
        return [
            "m_MTO",  # Максимальная взлётная масса [кг]
            "m_OE",  # Эксплуатационная масса пустого самолёта [кг]
            "m_F",  # Масса топлива [кг]
            "m_ML",  # Максимальная посадочная масса [кг]
            "T_TO",  # Взлётная тяга [Н]
            "S_W",  # Площадь крыла [м²]
            "m_OE_ratio",  # Относительная эксплуатационная масса пустого самолёта
            "m_F_ratio",  # Относительная масса топлива
            "useful_load_ratio",  # Относительная полезная нагрузка
        ]

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

            self.calculation_log.append("Начало расчёта масс")

            # Получение входных данных из предварительного расчёта
            p0_optimal = data.preliminary_sizing.p0_optimal
            P0_optimal = data.preliminary_sizing.P0_optimal

            # Дополнительные входные данные
            m_PL = data.mass_estimation.payload_mass  # кг
            R = data.mass_estimation.design_range  # км
            N = data.preliminary_sizing.N  # количество двигателей

            # Коэффициент топливного резерва, по умолчанию 10% резерв
            fuel_reserve = getattr(data.mass_estimation, 'fuel_reserve_factor', 1.1)

            # Удельный расход топлива, кг/(Н·с) для ТВД (турбовинтового двигателя)
            cruise_sfc = getattr(data.mass_estimation, 'cruise_sfc', 1.42e-5)

            # Аэродинамическое качество при крейсерском полёте
            cruise_L_D = getattr(data.mass_estimation, 'cruise_L_D_ratio')
            cruise_V = getattr(data.preliminary_sizing, 'V_cruise')

            # Относительная эксплуатационная масса пустого самолета (формула 5.49)
            m_OE_ratio = 0.23 + 1.04 * P0_optimal

            print('p0 = ', p0_optimal)
            print('P0 = ', P0_optimal)
            print('Относительная масса пустого самолёта', m_OE_ratio)

            # Массовые доли для различных этапов полёта (таблица 5.9)
            # Для бизнес-джетов / региональных самолётов
            mission_segments = {
                'engine_start': 0.990,  # запуск двигателей
                'taxi': 0.995,  # руление
                'takeoff': 0.995,  # взлёт
                'climb': 0.980,  # набор высоты
                'descent': 0.990,  # снижение
                'landing': 0.992,  # посадка
            }

            # Расчёт массовой доли миссии (M_ff) для этапов кроме крейсерского
            M_ff_non_cruise = 1.0
            for segment_name, mass_fraction in mission_segments.items():
                M_ff_non_cruise *= mass_fraction

            print('M_ff без круиза', M_ff_non_cruise)

            # Расчёт крейсерской массовой доли по формуле Бреге (уравнения (5.53) и (5.55))

            # фактор дальности Бреге
            B_s = (cruise_L_D * cruise_V) / (cruise_sfc * g)  # м

            print('Фактор Бреге', B_s)

            # Массовая доля для крейсерского участка
            R_meters = R * 1000  # Перевод в метры
            M_ff_cruise = math.exp(-R_meters / B_s)

            print('M_ff для круиза', M_ff_cruise)

            # Общая массовая доля миссии
            M_ff_total = M_ff_non_cruise * M_ff_cruise

            print('M_ff общая', M_ff_total)

            # Учёт топливного резерва
            M_ff_total_with_reserve = M_ff_total * fuel_reserve

            print('M_ff с топливным резервом', M_ff_total_with_reserve)

            # Относительная масса топлива (уравнение 5.52)
            m_F_ratio = fuel_reserve * (1 - M_ff_total)

            print('Относительная масса топлива m_F', m_F_ratio)

            if m_F_ratio < 0:
                raise CalculationError(
                    "Отрицательная масса топлива. Проверьте входные данные (дальность, SFC, L/D).",
                    self.name
                )

            # Максимальная взлётная масса (5.45)
            denominator = 1 - m_F_ratio - m_OE_ratio

            m_MTO = m_PL / denominator

            print('Максимальная взлётная масса', m_MTO)

            # Расчёт остальных масс
            # Эксплуатационная масса пустого самолёта
            m_OE = m_MTO * m_OE_ratio

            # Масса топлива
            m_F = m_MTO * m_F_ratio

            # Типичное значение m_ML/m_MTO: 0.88 (таблица 5.2)
            m_ML_ratio = 0.88  # Для бизнес-джетов
            m_ML = m_MTO * m_ML_ratio

            # Относительная полезная нагрузка
            useful_load_ratio = (m_F + m_PL) / m_MTO

            # Расчёт взлётной тяги и площади крыла (уравнения (5.56) и (5.57))
            T_TO = m_MTO * g * P0_optimal

            # p0 = (m_MTO * g) / S_W => S_W = (m_MTO * g) / p0
            S_W = (m_MTO * g) / p0_optimal

            # Сохранение результатов
            data.mass_estimation.m_MTO = m_MTO
            data.mass_estimation.m_OE = m_OE
            data.mass_estimation.m_F = m_F
            data.mass_estimation.m_ML = m_ML
            data.mass_estimation.T_TO = T_TO
            data.mass_estimation.S_W = S_W
            data.mass_estimation.m_OE_ratio = m_OE_ratio
            data.mass_estimation.m_F_ratio = m_F_ratio
            data.mass_estimation.useful_load_ratio = useful_load_ratio

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


    def get_log(self) -> str:
        """Возвращает лог расчётов как одну строку"""
        return "\n".join(self.calculation_log)

    def get_errors(self) -> List[str]:
        """Возвращает список ошибок"""
        return self.errors.copy()

    def has_errors(self) -> bool:
        """Проверяет, были ли ошибки"""
        return len(self.errors) > 0