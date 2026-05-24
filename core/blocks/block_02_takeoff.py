
from typing import Dict, Any, List
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData, EngineTypeEnum, WingFlapsTypeEnum, AircraftTypeEnum
from core.statistics_database import StatisticsDatabase
from core.exceptions import CalculationError
from core.aircraft_constants import (
    TAKEOFF_K_TO,
    TAKEOFF_SAFETY_FACTOR,
    TAKEOFF_CL_FACTOR,
    RHO_0,
    G,
    SIGMA_SEA_LEVEL,
)


class Block02Takeoff(BaseBlock):
    """
    Блок 2: Анализ взлётной дистанции

    Рассчитывает минимально необходимую тяговооружённость из требований
    взлётной дистанции, а также коэффициент наклона прямой на графике
    зависимости тяговооружённости от удельной нагрузки на крыло.

    Процесс:
    1. Вход: s_TO, engine_type → Рассчитать s_TOFL (длина взлётного поля)
    2. Вход: wing_flaps_type, aircraft_type → Получить C_L_max_TO или вычислить
    3. Вход: m_MTO/S_W (из Блока 1) → Обязательная зависимость
    4. Рассчитать: T_TO / (m_MTO * g) минимально необходимую тяговооружённость
    5. Рассчитать: slope = [T_TO / (m_MTO * g)] / (m_MTO / S_W)
       это коэффициент наклона для графика взлёта на диаграмме паба

    ВАЖНО: Уравнение 5.10 можно переписать в виде:
    T_TO / (m_MTO * g) = slope * (m_MTO / S_W)

    где slope = k_TO / (s_TOFL * σ * C_L_max_TO)

    Это позволяет строить граничную линию взлёта на диаграмме паба как прямую.
    """

    # Ссылочные константы из методики (из aircraft_constants.py)
    K_TO = TAKEOFF_K_TO  # м³/кг - из уравнения 5.10
    SAFETY_FACTOR = TAKEOFF_SAFETY_FACTOR  # Временное значение
    CL_FACTOR = TAKEOFF_CL_FACTOR  # Временное значение
    SIGMA = SIGMA_SEA_LEVEL
    G = G
    RHO_0 = RHO_0

    @property
    def name(self) -> str:
        return "Взлётная дистанция"

    @property
    def block_number(self) -> int:
        return 2

    @property
    def required_inputs(self) -> List[str]:
        return [
            "takeoff_data.s_TO",              # Длина разбега
            "takeoff_data.engine_type",       # Тип двигателя
            "m_MTO_per_S_W"                   # Результат из блока 1
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "takeoff_data.wing_flaps_type",   # Тип механизации при взлёте
            "takeoff_data.aircraft_type",     # Тип самолёта
            "takeoff_data.C_L_max_TO",        # Коэффициент подъёма при взлёте (ручной ввод)
        ]

    @property
    def outputs(self) -> List[str]:
        return [
            "T_TO_per_m_MTO_g",           # Тяговооружённость T_TO / (m_MTO * g)
            "takeoff_slope",              # Коэффициент наклона для графика паба
        ]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет расчёт тяговооружённости и наклона линии взлёта

        Уравнение 5.10 (стр. 5-10):
        T_TO / (m_MTO * g) = k_TO * (m_MTO / S_W) / (s_TOFL * σ * C_L_max_TO)

        Переформулировка для графика паба:
        T_TO / (m_MTO * g) = slope * (m_MTO / S_W)

        где:
        slope = k_TO / (s_TOFL * σ * C_L_max_TO)

        Логика:
        1. s_TO + engine_type -> s_TOFL (через safety factor)
        2. wing_flaps_type -> C_L_max_TO (из БД для взлёта)
        3. Уравнение 5.10: T_TO/(m_MTO*g) = k_TO * (m_MTO/S_W) / (s_TOFL * σ * C_L_max_TO)
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # ════════════════════════════════════════════════════════════
            # ШАГ 1: Проверить зависимость от Блока 1
            # ════════════════════════════════════════════════════════════

            if data.m_MTO_per_S_W is None:
                raise CalculationError(
                    "Отсутствует результат блока 1 (m_MTO_per_S_W). "
                    "Необходимо сначала выполнить расчёт посадочной дистанции.",
                    self.name
                )

            # ════════════════════════════════════════════════════════════
            # ШАГ 2: Получить и проверить обязательные входные данные
            # ════════════════════════════════════════════════════════════
            s_TO = data.takeoff_data.s_TO
            engine_type = data.takeoff_data.engine_type
            m_MTO_per_S_W = data.m_MTO_per_S_W


            if not s_TO or not engine_type:
                raise CalculationError(
                    f"{self.name}: Отсутствуют обязательные данные (s_TO и/или engine_type)",
                    self.name
                )

            if m_MTO_per_S_W <= 0:
                raise CalculationError(
                    f"{self.name}: Неверное значение m_MTO/S_W = {m_MTO_per_S_W} (должно быть > 0)",
                    self.name
                )

            print(f"✓ Входные данные: s_TO = {s_TO} м, тип двигателя = {engine_type.value}")
            print(f"  Зависимость от Блока 1: m_MTO/S_W = {m_MTO_per_S_W:.1f} кг/м²")

            # ════════════════════════════════════════════════════════════
            # ШАГ 3: Рассчитать s_TOFL (Длина взлётного поля)
            # ════════════════════════════════════════════════════════════

            # Вычисляем s_TOFL = 1,5 * s_TOG
            # todo: магическая константа 1,5 не из методики
            s_TOFL = s_TO * self.SAFETY_FACTOR
            data.takeoff_data.s_TOFL = s_TOFL
            data.takeoff_data.safety_factor = self.SAFETY_FACTOR

            print(f"  Шаг 3: s_TOFL = s_TO × {self.SAFETY_FACTOR}")
            print(f"  Шаг 3: s_TOFL = {s_TO} × {self.SAFETY_FACTOR} = {s_TOFL:.1f} м")

            # ════════════════════════════════════════════════════════════
            # ШАГ 4: Получить C_L_max_TO (Коэффициент подъёма при взлёте)
            # ════════════════════════════════════════════════════════════

            C_L_max_TO = data.takeoff_data.C_L_max_TO

            if C_L_max_TO is None:
                # Попытаться получить из посадки с коэффициентом (временная заглушка)
                C_L_max_L = data.landing_data.C_L_max_L

                if C_L_max_L:
                    C_L_max_TO = C_L_max_L * self.CL_FACTOR
                    data.takeoff_data.C_L_max_TO = C_L_max_TO
                    print(f"  Шаг 4: C_L_max_TO вычислен как C_L_max_L × {self.CL_FACTOR}")
                else:
                    raise CalculationError(
                        f"{self.name}: Невозможно определить C_L_max_TO. "
                        "Укажите значение C_L_max_TO или выполните Блок 1.",
                        self.name
                    )

            if C_L_max_TO <= 0:
                raise CalculationError(
                    f"{self.name}: Неверное значение C_L_max_TO = {C_L_max_TO} (должно быть > 0)",
                    self.name
                )

            print(f"  Шаг 4: C_L_max_TO = {C_L_max_TO:.2f}")

            # ════════════════════════════════════════════════════════════
            # ШАГ 5: Рассчитать знаменатель и наклон линии взлёта
            # ════════════════════════════════════════════════════════════
            # Из уравнения 5.10:
            # T_TO / (m_MTO * g) = k_TO * (m_MTO / S_W) / (s_TOFL * σ * C_L_max_TO)
            #
            # Переформулировка:
            # T_TO / (m_MTO * g) = [k_TO / (s_TOFL * σ * C_L_max_TO)] * (m_MTO / S_W)
            #                    = slope * (m_MTO / S_W)
            #
            # где:
            # slope = k_TO / (s_TOFL * σ * C_L_max_TO)

            m_MTO_per_S_W = data.m_MTO_per_S_W

            sigma = self.SIGMA  # Плотность на уровне моря

            denominator = s_TOFL * sigma * C_L_max_TO
            if denominator <= 0:
                raise CalculationError(
                    f"{self.name}: Знаменатель в формуле равен нулю или отрицателен",
                    self.name,
                    {
                        's_TOFL': s_TOFL,
                        'sigma': sigma,
                        'C_L_max_TO': C_L_max_TO,
                        'denominator': denominator
                    }
                )

            # Коэффициент наклона линии взлёта (для графика паба)
            takeoff_slope = self.K_TO / denominator

            # Тяговооружённость, умноженная на нагрузку на крыло
            T_TO_per_m_MTO_g = takeoff_slope * m_MTO_per_S_W

            if T_TO_per_m_MTO_g <= 0:
                raise CalculationError(
                    f"{self.name}: Получено отрицательное или нулевое значение тяговооружённости",
                    self.name,
             {
                    'takeoff_slope': takeoff_slope,
                    'm_MTO_per_S_W': m_MTO_per_S_W,
                    'T_TO_per_m_MTO_g': T_TO_per_m_MTO_g
                    }
                )

            # ════════════════════════════════════════════════════════════
            # ШАГ 6: Проверка физической разумности результата
            # ════════════════════════════════════════════════════════════

            if T_TO_per_m_MTO_g > 1.0:
                print(f"  ⚠️  Предупреждение: высокая тяговооружённость {T_TO_per_m_MTO_g:.4f}")

            if T_TO_per_m_MTO_g < 0.1:
                print(f"  ⚠️  Предупреждение: низкая тяговооружённость {T_TO_per_m_MTO_g:.4f}")

            # ════════════════════════════════════════════════════════════
            # ШАГ 7: Сохранение результатов
            # ════════════════════════════════════════════════════════════

            data.T_TO_per_m_MTO_g = T_TO_per_m_MTO_g
            data.takeoff_data.takeoff_slope = takeoff_slope
            data.takeoff_slope = takeoff_slope
            data.takeoff_data.calculated_denominator = denominator

            print(f"  Шаг 5: k_TO = {self.K_TO} м³/кг [из методики Уравнение 5.10]")
            print(f"  Шаг 5: denominator = s_TOFL × σ × C_L_max_TO")
            print(f"  Шаг 5: denominator = {s_TOFL:.1f} × {sigma} × {C_L_max_TO:.2f} = {denominator:.1f}")
            print(f"  Шаг 5: slope = k_TO / denominator = {self.K_TO} / {denominator:.1f} = {takeoff_slope:.4f}")
            print(f"  Шаг 6: T_TO/(m_MTO*g) = slope × (m_MTO/S_W)")
            print(f"  Шаг 6: T_TO/(m_MTO*g) = {takeoff_slope:.4f} × {m_MTO_per_S_W:.1f}")
            print(f"  Шаг 6: T_TO/(m_MTO*g) = {T_TO_per_m_MTO_g:.4f}")
            print(f"\n✓ {self.name}: T_TO/(m_MTO*g) = {T_TO_per_m_MTO_g:.4f}")
            print(f"✓ {self.name}: slope (для графика паба) = {takeoff_slope:.4f}")

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """
        Генерировать резюме расчёта
        """
        base_summary = super().get_calculation_summary(data)

        if data.T_TO_per_m_MTO_g is not None:
            base_summary["calculation_details"] = {
                "input_parameters": {
                    "s_TO (взлётная дистанция)": f"{data.takeoff_data.s_TO} м" if data.takeoff_data.s_TO else "—",
                    "тип_двигателя": data.takeoff_data.engine_type.value if data.takeoff_data.engine_type else "—",
                    "m_MTO/S_W (из Блока 1)": f"{data.m_MTO_per_S_W:.1f} кг/м²" if data.m_MTO_per_S_W else "—",
                },
                "derived_parameters": {
                    "s_TOFL (длина взлётного поля)": f"{data.takeoff_data.s_TOFL:.1f} м" if data.takeoff_data.s_TOFL else "—",
                    "C_L_max_TO": f"{data.takeoff_data.C_L_max_TO:.2f}" if data.takeoff_data.C_L_max_TO else "—",
                },
                "intermediate_results": {
                    "denominator": f"{data.takeoff_data.calculated_denominator:.2f}" if data.takeoff_data.calculated_denominator else "—",
                    "slope (для графика паба)": f"{data.takeoff_slope:.4f}" if data.takeoff_slope else "—",
                },
                "final_result": {
                    "T_TO / (m_MTO * g)": f"{data.T_TO_per_m_MTO_g:.4f}",
                    "описание": "Минимальная тяговооружённость из условий взлёта (CS-25.109)",
                },
                "equations_used": [
                    "s_TOFL = s_TO × safety_factor",
                    "slope = k_TO / (s_TOFL × σ × C_L_max_TO)  [из Уравнения 5.10]",
                    "T_TO/(m_MTO*g) = slope × (m_MTO/S_W)",
                ],
                "typical_values": {
                    "business_jets": {"min": 0.25, "max": 0.45},
                    "transport_aircraft": {"min": 0.20, "max": 0.35},
                },
            }

        return base_summary
