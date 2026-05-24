import math
from typing import Dict, Any, List

import numpy as np

from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData, WingChemeEnum
from core.exceptions import CalculationError

class BlockGeometry(BaseBlock):

    def __init__(self):
        """Инициализирует движок расчётов геометрии"""
        super().__init__()

        self.calculation_log: List[str] = []
        self.errors: List[str] = []

    @property
    def name(self) -> str:
        return "Геометрия"

    @property
    def block_number(self) -> int:
        return 3

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
            self.calculation_log.append("=" * 60)
            self.calculation_log.append("НАЧАЛО РАСЧЁТА ГЕОМЕТРИЧЕСКИХ ПАРАМЕТРОВ")
            self.calculation_log.append("=" * 60)

            # Получение базовых параметров
            S_wing = data.mass_estimation.S_W  # площадь крыла [м²]
            lambda_wing = data.preliminary_sizing.Lambda  # удлинение крыла

            self.calculation_log.append(f"Площадь крыла (S_W): {S_wing:.3f} м²")
            self.calculation_log.append(f"Удлинение крыла (Lambda): {lambda_wing:.2f}")

            # Значения по умолчанию для входных параметров
            defaults = self._get_default_values(data)

            # === РАСЧЁТ ПАРАМЕТРОВ КРЫЛА ===
            self.calculation_log.append("\n1. РАСЧЁТ ПАРАМЕТРОВ КРЫЛА:")

            # 1. Размах крыла
            l_wing = math.sqrt(S_wing * lambda_wing)
            self.calculation_log.append(f"   Размах крыла: l_wing = √(S_wing × λ_крыла)")
            self.calculation_log.append(f"   l_wing = √({S_wing:.3f} × {lambda_wing:.2f}) = {l_wing:.3f} м")

            # 2. Корневая хорда крыла
            eta_wing = defaults['eta_wing']
            b0_wing = (2 * S_wing) / (l_wing * (1 + 1 / eta_wing))
            self.calculation_log.append(f"   Корневая хорда: b0_крыла = 2×S_крыла / [l_крыла × (1 + 1/η_крыла)]")
            self.calculation_log.append(
                f"   b0_крыла = 2×{S_wing:.3f} / [{l_wing:.3f} × (1 + 1/{eta_wing:.2f})] = {b0_wing:.3f} м")

            # 3. Концевая хорда крыла
            bk_wing = b0_wing / eta_wing
            self.calculation_log.append(f"   Концевая хорда: bk_крыла = b0_крыла / η_крыла")
            self.calculation_log.append(f"   bk_крыла = {b0_wing:.3f} / {eta_wing:.2f} = {bk_wing:.3f} м")

            # 4. Угол стреловидности по передней кромке
            sweep_wing_quarter_rad = math.radians(defaults['sweep_wing_quarter'])
            sweep_wing_LE_rad = math.atan(
                math.tan(sweep_wing_quarter_rad) +
                (b0_wing - bk_wing) / (2 * l_wing)
            )
            sweep_wing_LE = math.degrees(sweep_wing_LE_rad)
            self.calculation_log.append(f"   Угол стреловидности по передней кромке:")
            self.calculation_log.append(f"   χ_пк = arctg(tg(χ_¼) + (b0_крыла - bk_крыла) / (2×l_крыла))")
            self.calculation_log.append(f"   χ_пк = arctg(tg({defaults['sweep_wing_quarter']:.1f}°) + "
                                        f"({b0_wing:.3f} - {bk_wing:.3f}) / (2×{l_wing:.3f}))")
            self.calculation_log.append(f"   χ_пк = {sweep_wing_LE:.2f}°")

            # === РАСЧЁТ ПАРАМЕТРОВ ФЮЗЕЛЯЖА ===
            self.calculation_log.append("\n2. РАСЧЁТ ПАРАМЕТРОВ ФЮЗЕЛЯЖА:")

            # 5. Длина фюзеляжа
            L_fuselage = defaults['k_fuselage'] * l_wing
            self.calculation_log.append(f"   Длина фюзеляжа: L_ф = k_ф × l_крыла")
            self.calculation_log.append(f"   L_ф = {defaults['k_fuselage']:.2f} × {l_wing:.3f} = {L_fuselage:.3f} м")

            # 6. Эквивалентный диаметр фюзеляжа
            d_fuselage = L_fuselage / defaults['lambda_fuselage']
            self.calculation_log.append(f"   Эквивалентный диаметр: d_ф = L_ф / λ_ф")
            self.calculation_log.append(
                f"   d_ф = {L_fuselage:.3f} / {defaults['lambda_fuselage']:.1f} = {d_fuselage:.3f} м")

            # 7. Радиус фюзеляжа
            r_fuselage = d_fuselage / 2
            self.calculation_log.append(f"   Радиус фюзеляжа: r_ф = d_ф / 2")
            self.calculation_log.append(f"   r_ф = {d_fuselage:.3f} / 2 = {r_fuselage:.3f} м")

            # 8. Y-координата крыла (вертикальное положение)
            wing_scheme = defaults['wing_scheme']
            if wing_scheme == 'high':  # высокоплан
                y_wing = d_fuselage / 2
                scheme_name = "высокоплан"
            elif wing_scheme == 'mid':  # среднеплан
                y_wing = 0
                scheme_name = "среднеплан"
            else:  # низкоплан
                y_wing = -d_fuselage / 2
                scheme_name = "низкоплан"


            self.calculation_log.append(f"   Y-координата крыла ({scheme_name}):")
            self.calculation_log.append(f"   y_крыла = {y_wing:.3f} м")

            # 9. X-координата фюзеляжа (положение начала фюзеляжа относительно крыла)
            x_fuselage = -7.0  # стандартное смещение, можно регулировать
            self.calculation_log.append(f"   X-координата начала фюзеляжа: {x_fuselage:.1f} м")

            # === РАСЧЁТ ПАРАМЕТРОВ ГОРИЗОНТАЛЬНОГО ОПЕРЕНИЯ ===
            self.calculation_log.append("\n3. РАСЧЁТ ПАРАМЕТРОВ ГОРИЗОНТАЛЬНОГО ОПЕРЕНИЯ (ГО):")

            # 10. Площадь ГО
            S_ht = defaults['k_horizontal_tail'] * S_wing
            self.calculation_log.append(f"   Площадь ГО: S_го = k_го × S_крыла")
            self.calculation_log.append(f"   S_го = {defaults['k_horizontal_tail']:.3f} × {S_wing:.3f} = {S_ht:.3f} м²")

            # 11. Размах ГО
            l_ht = math.sqrt(S_ht * defaults['lambda_horizontal_tail'])
            self.calculation_log.append(f"   Размах ГО: l_го = √(S_го × λ_го)")
            self.calculation_log.append(
                f"   l_го = √({S_ht:.3f} × {defaults['lambda_horizontal_tail']:.2f}) = {l_ht:.3f} м")

            # 12. Корневая хорда ГО
            b0_ht = (2 * S_ht) / (l_ht * (1 + 1 / defaults['eta_horizontal_tail']))
            self.calculation_log.append(f"   Корневая хорда ГО: b0_го = 2×S_го / [l_го × (1 + 1/η_го)]")
            self.calculation_log.append(f"   b0_го = {b0_ht:.3f} м")

            # 13. Концевая хорда ГО
            bk_ht = b0_ht / defaults['eta_horizontal_tail']
            self.calculation_log.append(f"   Концевая хорда ГО: bk_го = b0_го / η_го")
            self.calculation_log.append(f"   bk_го = {bk_ht:.3f} м")

            # 14. Угол стреловидности ГО по передней кромке
            sweep_ht_quarter_rad = math.radians(defaults['sweep_horizontal_tail_quarter'])
            sweep_ht_LE_rad = math.atan(
                math.tan(sweep_ht_quarter_rad) +
                (b0_ht - bk_ht) / (2 * l_ht)
            )
            sweep_ht_LE = math.degrees(sweep_ht_LE_rad)
            self.calculation_log.append(f"   Угол стреловидности ГО по передней кромке:")
            self.calculation_log.append(f"   χ_пк_го = {sweep_ht_LE:.2f}°")

            # 15. Координаты ГО (в хвостовой части фюзеляжа)
            # X-координата ГО примерно на 70-80% длины фюзеляжа от носа
            x_ht = x_fuselage + 0.75 * L_fuselage
            y_ht = 0.0  # ГО обычно на том же уровне, что и фюзеляж
            self.calculation_log.append(f"   Координаты ГО: X={x_ht:.2f} м, Y={y_ht:.2f} м")

            # === РАСЧЁТ ПАРАМЕТРОВ ВЕРТИКАЛЬНОГО ОПЕРЕНИЯ ===
            self.calculation_log.append("\n4. РАСЧЁТ ПАРАМЕТРОВ ВЕРТИКАЛЬНОГО ОПЕРЕНИЯ (ВО):")

            # 16. Площадь ВО
            S_vt = defaults['k_vertical_tail'] * S_wing
            self.calculation_log.append(f"   Площадь ВО: S_во = k_во × S_крыла")
            self.calculation_log.append(f"   S_во = {defaults['k_vertical_tail']:.3f} × {S_wing:.3f} = {S_vt:.3f} м²")

            # 17. Высота ВО
            l_vt = math.sqrt(S_vt * defaults['lambda_vertical_tail'])
            self.calculation_log.append(f"   Высота ВО: l_во = √(S_во × λ_во)")
            self.calculation_log.append(
                f"   l_во = √({S_vt:.3f} × {defaults['lambda_vertical_tail']:.2f}) = {l_vt:.3f} м")

            # 18. Корневая хорда ВО
            b0_vt = (2 * S_vt) / (l_vt * (1 + 1 / defaults['eta_vertical_tail']))
            self.calculation_log.append(f"   Корневая хорда ВО: b0_во = {b0_vt:.3f} м")

            # 19. Концевая хорда ВО
            bk_vt = b0_vt / defaults['eta_vertical_tail']
            self.calculation_log.append(f"   Концевая хорда ВО: bk_во = {bk_vt:.3f} м")

            # 20. Угол стреловидности ВО по передней кромке
            sweep_vt_quarter_rad = math.radians(defaults['sweep_vertical_tail_quarter'])
            sweep_vt_LE_rad = math.atan(
                math.tan(sweep_vt_quarter_rad) +
                (b0_vt - bk_vt) / (2 * l_vt)
            )
            sweep_vt_LE = math.degrees(sweep_vt_LE_rad)
            self.calculation_log.append(f"   Угол стреловидности ВО по передней кромке:")
            self.calculation_log.append(f"   χ_пк_во = {sweep_vt_LE:.2f}°")

            # 21. X-координата ВО (располагается рядом с ГО)
            x_vt = x_fuselage + 0.75 * L_fuselage
            self.calculation_log.append(f"   X-координата ВО: {x_vt:.2f} м")

            # === СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ===
            data.geometry_data.l_wing = l_wing
            data.geometry_data.b0_wing = b0_wing
            data.geometry_data.bk_wing = bk_wing
            data.geometry_data.sweep_wing_LE = sweep_wing_LE
            data.geometry_data.y_wing = y_wing

            data.geometry_data.S_ht = S_ht
            data.geometry_data.l_ht = l_ht
            data.geometry_data.b0_ht = b0_ht
            data.geometry_data.bk_ht = bk_ht
            data.geometry_data.sweep_ht_LE = sweep_ht_LE
            data.geometry_data.x_ht = x_ht
            data.geometry_data.y_ht = y_ht

            data.geometry_data.S_vt = S_vt
            data.geometry_data.l_vt = l_vt
            data.geometry_data.b0_vt = b0_vt
            data.geometry_data.bk_vt = bk_vt
            data.geometry_data.sweep_vt_LE = sweep_vt_LE
            data.geometry_data.x_vt = x_vt

            data.geometry_data.L_fuselage = L_fuselage
            data.geometry_data.d_fuselage = d_fuselage
            data.geometry_data.r_fuselage = r_fuselage
            data.geometry_data.x_fuselage = x_fuselage

            self.calculation_log.append("\n" + "=" * 60)
            self.calculation_log.append("✓ ВСЕ РАСЧЁТЫ УСПЕШНО ЗАВЕРШЕНЫ")
            self.calculation_log.append("=" * 60)

            print(self.get_log())

        except CalculationError as e:
            error_msg = f"{str(e)}"
            self.errors.append(error_msg)
            self.calculation_log.append(f"✗ ОШИБКА: {error_msg}")
            self.get_log()

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}" + self.get_log(),
                    self.name
                )

        self.calculation_log.append("=" * 60)
        self.calculation_log.append("✓ ВСЕ РАСЧЁТЫ УСПЕШНО ЗАВЕРШЕНЫ")
        self.calculation_log.append("=" * 60)

        return len(self.errors) == 0

    def _get_default_values(self, data: ProjectData) -> Dict[str, Any]:
        """
        Получение значений входных параметров или значений по умолчанию
        """
        geom = data.geometry_data

        # Значения по умолчанию (для бизнес-джета)
        defaults = {
            # Крыло
            'eta_wing': 2.5,  # сужение крыла
            'sweep_wing_quarter': 25.0,  # угол стреловидности [град]
            'wing_scheme': 'low',  # низкоплан

            # ГО
            'k_horizontal_tail': 0.25,  # коэффициент площади ГО (25% от площади крыла)
            'lambda_horizontal_tail': 4.0,  # удлинение ГО
            'eta_horizontal_tail': 3.0,  # сужение ГО
            'sweep_horizontal_tail_quarter': 30.0,  # угол стреловидности ГО [град]

            # ВО
            'k_vertical_tail': 0.15,  # коэффициент площади ВО (15% от площади крыла)
            'lambda_vertical_tail': 1.5,  # удлинение ВО
            'eta_vertical_tail': 2.0,  # сужение ВО
            'sweep_vertical_tail_quarter': 35.0,  # угол стреловидности ВО [град]

            # Фюзеляж
            'k_fuselage': 1.2,  # коэффициент длины фюзеляжа
            'lambda_fuselage': 9.0,  # удлинение фюзеляжа
        }

        # Заменяем значения по умолчанию на пользовательские, если они заданы
        if geom.eta_wing is not None:
            defaults['eta_wing'] = geom.eta_wing

        if geom.sweep_wing_quarter is not None:
            defaults['sweep_wing_quarter'] = geom.sweep_wing_quarter

        if geom.wing_scheme is not None:
            defaults['wing_scheme'] = geom.wing_scheme

        if geom.k_horizontal_tail is not None:
            defaults['k_horizontal_tail'] = geom.k_horizontal_tail

        if geom.lambda_horizontal_tail is not None:
            defaults['lambda_horizontal_tail'] = geom.lambda_horizontal_tail

        if geom.eta_horizontal_tail is not None:
            defaults['eta_horizontal_tail'] = geom.eta_horizontal_tail

        if geom.sweep_horizontal_tail_quarter is not None:
            defaults['sweep_horizontal_tail_quarter'] = geom.sweep_horizontal_tail_quarter

        if geom.k_vertical_tail is not None:
            defaults['k_vertical_tail'] = geom.k_vertical_tail

        if geom.lambda_vertical_tail is not None:
            defaults['lambda_vertical_tail'] = geom.lambda_vertical_tail

        if geom.eta_vertical_tail is not None:
            defaults['eta_vertical_tail'] = geom.eta_vertical_tail

        if geom.sweep_vertical_tail_quarter is not None:
            defaults['sweep_vertical_tail_quarter'] = geom.sweep_vertical_tail_quarter

        if geom.k_fuselage is not None:
            defaults['k_fuselage'] = geom.k_fuselage

        if geom.lambda_fuselage is not None:
            defaults['lambda_fuselage'] = geom.lambda_fuselage

        return defaults

    def get_log(self) -> str:
        """Возвращает лог расчётов как одну строку"""
        return "\n".join(self.calculation_log)

    def get_errors(self) -> List[str]:
        """Возвращает список ошибок"""
        return self.errors.copy()

    def has_errors(self) -> bool:
        """Проверяет, были ли ошибки"""
        return len(self.errors) > 0