from typing import Dict, Any, List
from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.statistics_database import StatisticsDatabase
from core.exceptions import CalculationError
from core.aircraft_constants import (
    LANDING_K_L,
    LANDING_SAFETY_FACTORS,
    RHO_0,
    G,
    SIGMA_SEA_LEVEL,
)


class Block01Landing(BaseBlock):
    """
    Блок 1: Расчёт посадочной дистанции
    """

    # Ссылочные константы из методики
    K_L = LANDING_K_L  # кг/м² - из уравнения 5.5
    SAFETY_FACTORS = LANDING_SAFETY_FACTORS
    RHO_0 = 0
    G = G
    SIGMA = SIGMA_SEA_LEVEL

    @property
    def name(self) -> str:
        return "Посадочная дистанция"

    @property
    def block_number(self) -> int:
        return 1

    @property
    def required_inputs(self) -> List[str]:
        return [
            "landing_data.s_L",           # Посадочный путь (основной вход)
            "landing_data.engine_type",   # Тип двигателя (для safety factor)
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "landing_data.wing_flaps_type",  # Тип механизации
            "landing_data.aircraft_type",    # Тип самолёта
            "landing_data.C_L_max_L",       # Ручной ввод коэффициента
            "landing_data.m_ML_m_MTO_ratio" # Ручной ввод отношения масс
        ]

    @property
    def outputs(self) -> List[str]:
        return ["m_MTO_per_S_W"]

    def calculate(self, data: ProjectData) -> None:
        """
        Основной метод расчёта

        Уравнение 5.5 (стр. 5-5):
        m_ML/S_W = k_L × σ × C_L_max_L / s_LFL

        где:
        - k_L = 0.107 кг/м² [из методики]
        - σ = относительная плотность воздуха
        - C_L_max_L = максимальный коэффициент подъёмной силы при посадке
        - s_LFL = длина посадочного поля [м]

        Уравнение 5.6 (стр. 5-5):
        m_MTO/S_W = (m_ML/S_W) / (m_ML/m_MTO)
        """
        try:
            # ════════════════════════════════════════════════════════════
            # ШАГ 1: Получить и проверить обязательные входные данные
            # ════════════════════════════════════════════════════════════
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Шаг 1: Вычисление s_LFL из s_L
            s_L = data.landing_data.s_L
            engine_type = data.landing_data.engine_type

            if not s_L or not engine_type:
                raise CalculationError(
                    "Отсутствуют обязательные данные: s_L и engine_type",
                    self.name
                )

            print(f"✓ Входные данные: s_L = {s_L} м, тип двигателя = {engine_type.value}")

            # ════════════════════════════════════════════════════════════
            # ШАГ 2: Рассчитать s_LFL (Длина посадочного поля)
            # ════════════════════════════════════════════════════════════
            # Из CS-OPS 1.515 (упомянуто в методике, стр. 5-4)
            # Для турбореактивного двигателя: коэффициент безопасности = 1/0.6 = 1.667
            # Для турбовинтового двигателя: коэффициент безопасности = 1/0.7 = 1.429

            engine_key = engine_type.value.lower()
            safety_factor = self.SAFETY_FACTORS.get(
                engine_key,
                1.667  # по умолчанию турбореактивный
            )

            s_LFL = s_L * safety_factor

            # Сохраняем промежуточные результаты
            data.landing_data.s_LFL = s_LFL
            data.landing_data.safety_factor = safety_factor

            print(f"  Шаг 2: Коэффициент безопасности = {safety_factor:.3f}")
            print(f"  Шаг 2: s_LFL = s_L × коэффициент = {s_L} × {safety_factor:.3f} = {s_LFL:.1f} м")

            # ════════════════════════════════════════════════════════════
            # ШАГ 3: Получить C_L_max_L (Макс. коэффициент подъёма при посадке)
            # ════════════════════════════════════════════════════════════

            C_L_max_L = data.landing_data.C_L_max_L

            if C_L_max_L is None:
                # Получаем из БД по типу механизации крыла
                wing_flaps_type = data.landing_data.wing_flaps_type

                if wing_flaps_type:
                    C_L_max_L = StatisticsDatabase.FLAPS_C_L_MAX.get(wing_flaps_type)
                    if not C_L_max_L:
                        raise CalculationError(
                            f"{self.name}: Невозможно определить C_L_max_L для типа закрылков {wing_flaps_type}",
                            self.name
                        )
                    data.landing_data.C_L_max_L = C_L_max_L
                else:
                    raise CalculationError(f"{self.name}: Не предоставлены ни C_L_max_L ни wing_flaps_type", self.name)

            if C_L_max_L <= 0:
                raise CalculationError(
                    f"{self.name}: Неверное значение C_L_max_L = {C_L_max_L} (должно быть > 0)",
                    self.name
                )

            print(f"  Шаг 3: C_L_max_L = {C_L_max_L:.2f}")

            # ════════════════════════════════════════════════════════════
            # ШАГ 4: Получить m_ML/m_MTO (Коэффициент максимальной посадочной массы)
            # ════════════════════════════════════════════════════════════

            m_ML_per_m_MTO = data.landing_data.m_ML_per_m_MTO_ratio

            if m_ML_per_m_MTO is None:
                aircraft_type = data.landing_data.aircraft_type

                if aircraft_type:
                    m_ML_per_m_MTO = StatisticsDatabase.get_mass_ratio(aircraft_type)
                    data.landing_data.m_ML_per_m_MTO_ratio = m_ML_per_m_MTO
                else:
                    # Значение по умолчанию консервативное (из Таблицы 5.2, стр. 5-6)
                    m_ML_per_m_MTO = 0.88  # среднее значение для реактивных транспортов
                    data.landing_data.m_ML_per_m_MTO_ratio = m_ML_per_m_MTO
                    print(f"  Шаг 4: Используется значение по умолчанию m_ML/m_MTO = {m_ML_per_m_MTO:.3f}")

            if m_ML_per_m_MTO <= 0:
                raise CalculationError(
                    f"{self.name}: Неверное значение m_ML/m_MTO = {m_ML_per_m_MTO} (должно быть > 0)",
                    self.name
                )

            print(f"  Шаг 4: m_ML/m_MTO = {m_ML_per_m_MTO:.3f}")

            # ════════════════════════════════════════════════════════════
            # ШАГ 5: Рассчитать m_ML/S_W (Нагрузка на крыло при посадке)
            # ════════════════════════════════════════════════════════════
            # Из уравнения 5.5 (стр. 5-5):
            # m_ML/S_W = k_L × σ × C_L_max_L / s_LFL
            #
            # где:
            # k_L = 0.107 кг/м² [из методики]
            # σ = относительная плотность воздуха (1.0 на уровне моря)
            # C_L_max_L = максимальный коэффициент подъёма при посадке
            # s_LFL = длина посадочного поля [м]

            # todo: брать отношение плотностей из информации об аэропорте
            sigma = self.SIGMA  # Для посадки на уровне моря

            m_ML_per_S_W = self.K_L * sigma * C_L_max_L * s_LFL

            if m_ML_per_S_W <= 0:
                raise CalculationError(
                    f"{self.name}: Неверный расчёт m_ML/S_W: "
                    f"K_L={self.K_L:.4f}, σ={sigma:.1f}, C_L_max_L={C_L_max_L:.2f}, "
                    f"s_LFL={s_LFL:.1f}, результат={m_ML_per_S_W:.2f}",
                    self.name
                )

            data.landing_data.calculated_m_ML_per_S_W = m_ML_per_S_W

            print(f"  Шаг 5: Используется k_L = {self.K_L} кг/м² [из методики Уравнение 5.5]")
            print(f"  Шаг 5: m_ML/S_W = k_L × σ × C_L_max_L / s_LFL")
            print(f"  Шаг 5: m_ML/S_W = {self.K_L} × {sigma} × {C_L_max_L:.2f} × {s_LFL:.1f}")
            print(f"  Шаг 5: m_ML/S_W = {m_ML_per_S_W:.1f} кг/м²")

            # ════════════════════════════════════════════════════════════
            # ШАГ 6: Рассчитать m_MTO/S_W (Нагрузка на крыло при взлёте)
            # ════════════════════════════════════════════════════════════
            # Из уравнения 5.6 (стр. 5-5):
            # m_MTO/S_W = (m_ML/S_W) / (m_ML/m_MTO)

            m_MTO_per_S_W = m_ML_per_S_W / m_ML_per_m_MTO

            if m_MTO_per_S_W <= 0:
                raise CalculationError(
                    f"{self.name}: Неверный расчёт m_MTO/S_W: "
                    f"m_ML/S_W={m_ML_per_S_W:.2f}, m_ML/m_MTO={m_ML_per_m_MTO:.3f}, "
                    f"результат={m_MTO_per_S_W:.2f}",
                    self.name
                )

            data.m_MTO_per_S_W = m_MTO_per_S_W

            print(f"  Шаг 6: m_MTO/S_W = m_ML/S_W / (m_ML/m_MTO)")
            print(f"  Шаг 6: m_MTO/S_W = {m_ML_per_S_W:.1f} / {m_ML_per_m_MTO:.3f}")
            print(f"  Шаг 6: m_MTO/S_W = {m_MTO_per_S_W:.1f} кг/м²")

            print(f"✓ {self.name}: m_MTO/S_W = {m_MTO_per_S_W:.1f} кг/м²")

        except CalculationError:
            raise
        except Exception as e:
            raise CalculationError(
                f"{self.name}: {str(e)}",
                self.name
            )

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """
        Генерировать резюме расчёта
        """
        base_summary = super().get_calculation_summary(data)

        if data.m_MTO_per_S_W is not None:
            base_summary["calculation_details"] = {
                "input_parameters": {
                    "s_L (посадочный путь)": f"{data.landing_data.s_L} м" if data.landing_data.s_L else "—",
                    "тип_двигателя": data.landing_data.engine_type.value if data.landing_data.engine_type else "—",
                    "тип_самолёта": data.landing_data.aircraft_type.value if data.landing_data.aircraft_type else "—",
                    "тип_закрылков": data.landing_data.wing_flaps_type.value if data.landing_data.wing_flaps_type else "—",
                },
                "derived_parameters": {
                    "s_LFL (длина посадочного поля)": f"{data.landing_data.s_LFL:.1f} м" if data.landing_data.s_LFL else "—",
                    "коэффициент_безопасности": f"{data.landing_data.safety_factor:.3f}" if data.landing_data.safety_factor else "—",
                    "C_L_max_L": f"{data.landing_data.C_L_max_L:.2f}" if data.landing_data.C_L_max_L else "—",
                    "m_ML/m_MTO": f"{data.landing_data.m_ML_per_m_MTO_ratio:.3f}" if data.landing_data.m_ML_per_m_MTO_ratio else "—",
                },
                "intermediate_results": {
                    "m_ML/S_W": f"{data.landing_data.calculated_m_ML_per_S_W:.1f} кг/м²" if data.landing_data.calculated_m_ML_per_S_W else "—",
                },
                "final_result": {
                    "m_MTO/S_W": f"{data.m_MTO_per_S_W:.1f} кг/м²",
                },
                "description": "Ограничение нагрузки на крыло из требования посадочной дистанции (CS-25.125)",
                "equations_used": [
                    "s_LFL = s_L × коэффициент  [CS-OPS 1.515]",
                    "m_ML/S_W = k_L × σ × C_L_max_L / s_LFL  [Уравнение 5.5, k_L=0.107]",
                    "m_MTO/S_W = (m_ML/S_W) / (m_ML/m_MTO)  [Уравнение 5.6]",
                ],
            }

        return base_summary