"""
Блок 11: Расчёт геометрии самолёта

Расчёт основных геометрических параметров на основе площадей оперения и параметров фюзеляжа.

Источник: методика предварительного проектирования и справочные данные
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import math

from core.blocks.base_block import BaseBlock
from core.data_models import ProjectData
from core.exceptions import CalculationError


@dataclass
class GeometryData:
    """Контейнер для хранения расчётных геометрических параметров"""

    # ========== КРЫЛО ==========
    wing_area: Optional[float] = None  # м² (S_W из блока 10)
    wing_aspect_ratio: Optional[float] = None  # λ (удлинение крыла, задаётся специалистом)
    wing_taper_ratio: Optional[float] = None  # η (сужение крыла)
    wing_span: Optional[float] = None  # м (размах b)
    wing_chord_root: Optional[float] = None  # м (корневая хорда b_r)
    wing_chord_tip: Optional[float] = None  # м (концевая хорда b_t)
    wing_mean_chord: Optional[float] = None  # м (средняя хорда MAC)
    wing_sweep_angle: Optional[float] = None  # град (угол стреловидности χ)
    wing_dihedral_angle: Optional[float] = None  # град (угол поперечного V)

    # ========== ГОРИЗОНТАЛЬНОЕ ОПЕРЕНИЕ ==========
    horizontal_tail_area: Optional[float] = None  # м² (S_го)
    h_tail_aspect_ratio: Optional[float] = None  # λ_го
    h_tail_taper_ratio: Optional[float] = None  # η_го
    h_tail_span: Optional[float] = None  # м (размах l_го)
    h_tail_chord_root: Optional[float] = None  # м (корневая хорда b_го_r)
    h_tail_chord_tip: Optional[float] = None  # м (концевая хорда b_го_t)
    h_tail_sweep_angle: Optional[float] = None  # град (угол стреловидности χ_го)
    h_tail_y_coord: Optional[float] = None  # м (Y-координата центра ГО)

    # ========== ВЕРТИКАЛЬНОЕ ОПЕРЕНИЕ ==========
    vertical_tail_area: Optional[float] = None  # м² (S_во)
    v_tail_aspect_ratio: Optional[float] = None  # λ_во
    v_tail_taper_ratio: Optional[float] = None  # η_во
    v_tail_height: Optional[float] = None  # м (высота l_во)
    v_tail_chord_root: Optional[float] = None  # м (корневая хорда b_во_r)
    v_tail_chord_tip: Optional[float] = None  # м (концевая хорда b_во_t)
    v_tail_sweep_angle: Optional[float] = None  # град (угол стреловидности χ_во)

    # ========== ФЮЗЕЛЯЖ ==========
    fuselage_length: Optional[float] = None  # м (L_fuz)
    fuselage_diameter: Optional[float] = None  # м (D_fuz)
    fuselage_length_to_diameter_ratio: Optional[float] = None  # λ_φ (обычно 8-10)
    fuselage_volume: Optional[float] = None  # м³
    fuselage_wetted_area: Optional[float] = None  # м² (смоченная площадь)

    # ========== СУММАРНЫЕ ПАРАМЕТРЫ ==========
    total_wetted_area: Optional[float] = None  # м² (полная смоченная площадь)
    reference_area: Optional[float] = None  # м² (площадь сравнения, обычно S_W)

    # ========== ПАРАМЕТРЫ ШАССИ ==========
    landing_gear_width: Optional[float] = None  # м (колея шасси)
    ground_clearance: Optional[float] = None  # м (клиренс под фюзеляжем)

    # ========== СЛУЖЕБНЫЕ ПАРАМЕТРЫ ==========
    k_phi: Optional[float] = 1.5  # Коэффициент для длины фюзеляжа (заглушка)


class Block11Geometry(BaseBlock):
    """
    Блок 11: Расчёт геометрии самолёта

    Вычисляет основные геометрические параметры самолёта на основе:
    - Площадей оперения (S_W, S_го, S_во)
    - Удлинений (задаются специалистом или по умолчанию)
    - Сужений крыла и оперения
    - Максимальной взлётной массы (для расчёта фюзеляжа)

    Используются формулы из таблицы БЛОК 11:
    - Размах элемента: l = sqrt(S * λ)
    - Корневая хорда: b₀ = 2S / (l·(1+η))
    - Концевая хорда: b_k = b₀ / η
    - Диаметр фюзеляжа: D = λ_φ·l_b (где λ_φ = 8...10)
    """

    @property
    def name(self) -> str:
        return "Расчёт геометрии самолёта"

    @property
    def block_number(self) -> int:
        return 11

    @property
    def required_inputs(self) -> List[str]:
        return [
            "S_W",  # Площадь крыла (м²) из блока 10
            "m_MTO",  # Максимальная взлётная масса (кг) из блока 9
        ]

    @property
    def optional_inputs(self) -> List[str]:
        return [
            "S_h",  # Площадь горизонтального оперения
            "S_v",  # Площадь вертикального оперения
            "lambda_wing",  # Удлинение крыла
            "lambda_h_tail",  # Удлинение ГО
            "lambda_v_tail",  # Удлинение ВО
            "eta_wing",  # Сужение крыла
            "eta_h_tail",  # Сужение ГО
            "eta_v_tail",  # Сужение ВО
            "wing_sweep",  # Угол стреловидности крыла
            "lambda_phi",  # Отношение L/D для фюзеляжа (8-10)
        ]

    @property
    def outputs(self) -> List[str]:
        return [
            "wing_span", "wing_chord_root", "wing_chord_tip", "wing_mean_chord",
            "h_tail_span", "h_tail_chord_root", "h_tail_chord_tip",
            "v_tail_height", "v_tail_chord_root", "v_tail_chord_tip",
            "fuselage_length", "fuselage_diameter", "total_wetted_area"
        ]

    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет расчёт геометрических параметров самолёта
        """
        try:
            # Валидация входных данных
            validation_errors = self.validate(data)
            if validation_errors:
                raise CalculationError(
                    f"Ошибки валидации в блоке {self.name}: {validation_errors}",
                    self.name
                )

            # Проверка зависимостей
            missing_data = []
            if data.S_W is None:
                missing_data.append("Блок 10 (S_W)")
            if data.m_MTO is None:
                missing_data.append("Блок 9 (m_MTO)")

            if missing_data:
                raise CalculationError(
                    f"Отсутствуют результаты от блоков: {', '.join(missing_data)}. "
                    "Необходимо завершить расчёты предыдущих блоков.",
                    self.name
                )

            # Получение входных данных
            wing_area = data.S_W  # м²
            mto_mass = data.m_MTO  # кг

            # Инициализация контейнера геометрических данных
            if not hasattr(data, 'geometry_data') or data.geometry_data is None:
                data.geometry_data = GeometryData()

            # =====================================================
            # 1. РАСЧЁТ ПАРАМЕТРОВ КРЫЛА
            # =====================================================

            wing_aspect_ratio = data.geometry_data.wing_aspect_ratio or \
                self._determine_aspect_ratio(data)

            wing_taper_ratio = data.geometry_data.wing_taper_ratio or \
                self._determine_taper_ratio(data)

            # 1.1 Размах крыла: b = sqrt(S_W * λ)
            wing_span = math.sqrt(wing_area * wing_aspect_ratio)

            # 1.2 Корневая хорда: b_r = 2*S / (b * (1 + η))
            wing_chord_root = (2 * wing_area) / (wing_span * (1 + wing_taper_ratio))

            # 1.3 Концевая хорда: b_t = b_r / η
            wing_chord_tip = wing_chord_root / wing_taper_ratio

            # 1.4 Средняя хорда: MAC = S / b
            wing_mean_chord = wing_area / wing_span

            # 1.5 Угол стреловидности (задаётся пользователем или по умолчанию)
            wing_sweep = data.geometry_data.wing_sweep_angle or \
                self._determine_wing_sweep(data)

            # 1.6 Угол поперечного V
            wing_dihedral = data.geometry_data.wing_dihedral_angle or \
                self._determine_dihedral_angle(data)

            # Сохраняем параметры крыла
            data.geometry_data.wing_area = wing_area
            data.geometry_data.wing_aspect_ratio = wing_aspect_ratio
            data.geometry_data.wing_taper_ratio = wing_taper_ratio
            data.geometry_data.wing_span = wing_span
            data.geometry_data.wing_chord_root = wing_chord_root
            data.geometry_data.wing_chord_tip = wing_chord_tip
            data.geometry_data.wing_mean_chord = wing_mean_chord
            data.geometry_data.wing_sweep_angle = wing_sweep
            data.geometry_data.wing_dihedral_angle = wing_dihedral

            # =====================================================
            # 2. РАСЧЁТ ПАРАМЕТРОВ ГОРИЗОНТАЛЬНОГО ОПЕРЕНИЯ
            # =====================================================

            # Площадь ГО: обычно S_го = 0.25-0.35 * S_W
            h_tail_area = getattr(data, 'S_h', None) or (0.30 * wing_area)

            h_tail_aspect_ratio = getattr(data, 'lambda_h_tail', None) or \
                self._determine_h_tail_aspect_ratio(data)

            h_tail_taper_ratio = getattr(data, 'eta_h_tail', None) or 0.35

            # 2.1 Размах ГО: l_го = sqrt(S_го * λ_го)
            h_tail_span = math.sqrt(h_tail_area * h_tail_aspect_ratio)

            # 2.2 Корневая хорда ГО: b_го_r = 2*S_го / (l_го * (1 + η_го))
            h_tail_chord_root = (2 * h_tail_area) / (h_tail_span * (1 + h_tail_taper_ratio))

            # 2.3 Концевая хорда ГО: b_го_t = b_го_r / η_го
            h_tail_chord_tip = h_tail_chord_root / h_tail_taper_ratio

            # 2.4 Угол стреловидности ГО (обычно в 2 раза больше, чем крыло)
            h_tail_sweep = data.geometry_data.h_tail_sweep_angle or \
                (wing_sweep * 1.3 if wing_sweep else 20.0)

            # 2.5 Y-координата ГО (0 для моноплана, или +l_bo для бипланов)
            h_tail_y_coord = data.geometry_data.h_tail_y_coord or 0.0

            # Сохраняем параметры ГО
            data.geometry_data.horizontal_tail_area = h_tail_area
            data.geometry_data.h_tail_aspect_ratio = h_tail_aspect_ratio
            data.geometry_data.h_tail_taper_ratio = h_tail_taper_ratio
            data.geometry_data.h_tail_span = h_tail_span
            data.geometry_data.h_tail_chord_root = h_tail_chord_root
            data.geometry_data.h_tail_chord_tip = h_tail_chord_tip
            data.geometry_data.h_tail_sweep_angle = h_tail_sweep
            data.geometry_data.h_tail_y_coord = h_tail_y_coord

            # =====================================================
            # 3. РАСЧЁТ ПАРАМЕТРОВ ВЕРТИКАЛЬНОГО ОПЕРЕНИЯ
            # =====================================================

            # Площадь ВО: обычно S_во = 0.08-0.15 * S_W
            v_tail_area = getattr(data, 'S_v', None) or (0.10 * wing_area)

            v_tail_aspect_ratio = getattr(data, 'lambda_v_tail', None) or \
                self._determine_v_tail_aspect_ratio(data)

            v_tail_taper_ratio = getattr(data, 'eta_v_tail', None) or 0.30

            # 3.1 Высота ВО: l_во = sqrt(S_во * λ_во)
            v_tail_height = math.sqrt(v_tail_area * v_tail_aspect_ratio)

            # 3.2 Корневая хорда ВО: b_во_r = 2*S_во / (l_во * (1 + η_во))
            v_tail_chord_root = (2 * v_tail_area) / (v_tail_height * (1 + v_tail_taper_ratio))

            # 3.3 Концевая хорда ВО: b_во_t = b_во_r / η_во
            v_tail_chord_tip = v_tail_chord_root / v_tail_taper_ratio

            # 3.4 Угол стреловидности ВО (обычно в 3-4 раза больше, чем крыло)
            v_tail_sweep = data.geometry_data.v_tail_sweep_angle or \
                (wing_sweep * 1.8 if wing_sweep else 35.0)

            # Сохраняем параметры ВО
            data.geometry_data.vertical_tail_area = v_tail_area
            data.geometry_data.v_tail_aspect_ratio = v_tail_aspect_ratio
            data.geometry_data.v_tail_taper_ratio = v_tail_taper_ratio
            data.geometry_data.v_tail_height = v_tail_height
            data.geometry_data.v_tail_chord_root = v_tail_chord_root
            data.geometry_data.v_tail_chord_tip = v_tail_chord_tip
            data.geometry_data.v_tail_sweep_angle = v_tail_sweep

            # =====================================================
            # 4. РАСЧЁТ ПАРАМЕТРОВ ФЮЗЕЛЯЖА
            # =====================================================

            # 4.1 Длина фюзеляжа: L = k_phi * m_MTO^(1/3)
            # k_phi = 1.5 (заглушка)
            k_phi = getattr(data, 'k_phi', None) or 1.5
            fuselage_length = k_phi * (mto_mass ** (1 / 3))

            # 4.2 Отношение L/D (λ_φ): обычно 8-10
            length_to_diameter_ratio = getattr(data, 'lambda_phi', None) or 9.0

            # 4.3 Диаметр фюзеляжа: D = L / λ_φ
            fuselage_diameter = fuselage_length / length_to_diameter_ratio

            # 4.4 Объём фюзеляжа: V = (π/4) * D² * L * k_fill
            fill_factor = 0.60
            fuselage_volume = (math.pi / 4) * (fuselage_diameter ** 2) * \
                fuselage_length * fill_factor

            # 4.5 Смоченная площадь фюзеляжа: S_wet = π * D * L * 0.9
            wetted_area_factor = 0.90
            fuselage_wetted_area = math.pi * fuselage_diameter * \
                fuselage_length * wetted_area_factor

            # Сохраняем параметры фюзеляжа
            data.geometry_data.fuselage_length = fuselage_length
            data.geometry_data.fuselage_diameter = fuselage_diameter
            data.geometry_data.fuselage_length_to_diameter_ratio = length_to_diameter_ratio
            data.geometry_data.fuselage_volume = fuselage_volume
            data.geometry_data.fuselage_wetted_area = fuselage_wetted_area
            data.geometry_data.k_phi = k_phi

            # =====================================================
            # 5. РАСЧЁТ СУММАРНЫХ ПАРАМЕТРОВ
            # =====================================================

            # 5.1 Полная смоченная площадь
            wing_wetted_area = wing_area * 2.0  # Обе стороны
            h_tail_wetted_area = h_tail_area * 2.0
            v_tail_wetted_area = v_tail_area * 2.0
            gear_wetted_area = 0.015 * wing_area

            total_wetted_area = (wing_wetted_area + fuselage_wetted_area +
                                h_tail_wetted_area + v_tail_wetted_area + gear_wetted_area)

            data.geometry_data.total_wetted_area = total_wetted_area
            data.geometry_data.reference_area = wing_area

            # =====================================================
            # 6. РАСЧЁТ ПАРАМЕТРОВ ШАССИ
            # =====================================================

            # 6.1 Колея шасси: обычно 0.25-0.35 от размаха
            landing_gear_width = wing_span * 0.30

            # 6.2 Клиренс под фюзеляжем
            ground_clearance = 0.40

            data.geometry_data.landing_gear_width = landing_gear_width
            data.geometry_data.ground_clearance = ground_clearance

            # =====================================================
            # 7. ВАЛИДАЦИЯ РЕЗУЛЬТАТОВ
            # =====================================================

            self._validate_results(data)
            self._print_results(data)

        except Exception as e:
            if isinstance(e, CalculationError):
                raise
            else:
                raise CalculationError(
                    f"Неожиданная ошибка в блоке {self.name}: {str(e)}",
                    self.name
                )

    # =========================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================================

    def _determine_aspect_ratio(self, data: ProjectData) -> float:
        """Определяет удлинение крыла (значение по умолчанию)"""
        aircraft_type_str = data.landing_data.aircraft_type.value \
            if data.landing_data.aircraft_type else "medium_range_jet_transport"

        aspect_ratios = {
            "business_jet": 8.0,
            "short_range_jet_transport": 8.5,
            "medium_range_jet_transport": 9.0,
            "long_range_jet_transport": 9.5,
            "ultra_long_range_jet_transport": 10.0,
            "fighter": 3.5,
            "supersonic_cruise": 4.5
        }
        return aspect_ratios.get(aircraft_type_str, 8.5)

    def _determine_taper_ratio(self, data: ProjectData) -> float:
        """Определяет сужение крыла (η)"""
        aircraft_type_str = data.landing_data.aircraft_type.value \
            if data.landing_data.aircraft_type else "medium_range_jet_transport"

        taper_ratios = {
            "business_jet": 0.40,
            "short_range_jet_transport": 0.35,
            "medium_range_jet_transport": 0.35,
            "long_range_jet_transport": 0.32,
            "ultra_long_range_jet_transport": 0.32,
            "fighter": 0.30,
            "supersonic_cruise": 0.25
        }
        return taper_ratios.get(aircraft_type_str, 0.35)

    def _determine_h_tail_aspect_ratio(self, data: ProjectData) -> float:
        """Определяет удлинение горизонтального оперения"""
        return 6.5  # Типовое значение для ГО

    def _determine_v_tail_aspect_ratio(self, data: ProjectData) -> float:
        """Определяет удлинение вертикального оперения"""
        return 2.5  # Типовое значение для ВО (обычно меньше)

    def _determine_wing_sweep(self, data: ProjectData) -> float:
        """Определяет угол стреловидности крыла"""
        aircraft_type_str = data.landing_data.aircraft_type.value \
            if data.landing_data.aircraft_type else "medium_range_jet_transport"

        sweep_angles = {
            "business_jet": 25.0,
            "short_range_jet_transport": 20.0,
            "medium_range_jet_transport": 25.0,
            "long_range_jet_transport": 30.0,
            "ultra_long_range_jet_transport": 32.0,
            "fighter": 35.0,
            "supersonic_cruise": 45.0
        }
        return sweep_angles.get(aircraft_type_str, 25.0)

    def _determine_dihedral_angle(self, data: ProjectData) -> float:
        """Определяет угол поперечного V"""
        aircraft_type_str = data.landing_data.aircraft_type.value \
            if data.landing_data.aircraft_type else "medium_range_jet_transport"

        dihedral_angles = {
            "business_jet": 6.0,
            "short_range_jet_transport": 5.0,
            "medium_range_jet_transport": 6.0,
            "long_range_jet_transport": 6.0,
            "ultra_long_range_jet_transport": 6.0,
            "fighter": 5.0,
            "supersonic_cruise": 4.0
        }
        return dihedral_angles.get(aircraft_type_str, 6.0)

    def _validate_results(self, data: ProjectData) -> None:
        """Проверяет разумность вычисленных параметров"""
        geo = data.geometry_data

        if geo.wing_span <= 0 or geo.wing_span > 100:
            raise CalculationError(
                f"Неразумное значение размаха крыла: {geo.wing_span:.1f} м",
                self.name
            )

        if geo.fuselage_length <= 0 or geo.fuselage_length > 100:
            raise CalculationError(
                f"Неразумное значение длины фюзеляжа: {geo.fuselage_length:.1f} м",
                self.name
            )

        if geo.fuselage_diameter <= 0 or geo.fuselage_diameter > 20:
            raise CalculationError(
                f"Неразумное значение диаметра фюзеляжа: {geo.fuselage_diameter:.2f} м",
                self.name
            )

        actual_ld = geo.fuselage_length / geo.fuselage_diameter
        if actual_ld < 5 or actual_ld > 15:
            raise CalculationError(
                f"Неразумное отношение L/D: {actual_ld:.1f}",
                self.name
            )

    def _print_results(self, data: ProjectData) -> None:
        """Вывод результатов расчётов"""
        geo = data.geometry_data

        print(f"\n{'=' * 70}")
        print(f"Блок 11 - Расчёт геометрии самолёта")
        print(f"{'=' * 70}\n")

        print("КРЫЛО:")
        print(f"  Площадь: {data.S_W:.1f} м²")
        print(f"  Размах (b): {geo.wing_span:.2f} м")
        print(f"  Удлинение (λ): {geo.wing_aspect_ratio:.2f}")
        print(f"  Сужение (η): {geo.wing_taper_ratio:.3f}")
        print(f"  Корневая хорда (b_r): {geo.wing_chord_root:.3f} м")
        print(f"  Концевая хорда (b_t): {geo.wing_chord_tip:.3f} м")
        print(f"  Средняя хорда (MAC): {geo.wing_mean_chord:.3f} м")
        print(f"  Стреловидность (χ): {geo.wing_sweep_angle:.1f}°")
        print(f"  Диэдр (V): {geo.wing_dihedral_angle:.1f}°")

        print("\nГОРИЗОНТАЛЬНОЕ ОПЕРЕНИЕ:")
        print(f"  Площадь (S_го): {geo.horizontal_tail_area:.2f} м²")
        print(f"  Размах (l_го): {geo.h_tail_span:.2f} м")
        print(f"  Удлинение (λ_го): {geo.h_tail_aspect_ratio:.2f}")
        print(f"  Сужение (η_го): {geo.h_tail_taper_ratio:.3f}")
        print(f"  Корневая хорда (b_го_r): {geo.h_tail_chord_root:.3f} м")
        print(f"  Концевая хорда (b_го_t): {geo.h_tail_chord_tip:.3f} м")
        print(f"  Y-координата: {geo.h_tail_y_coord:.2f} м")

        print("\nВЕРТИКАЛЬНОЕ ОПЕРЕНИЕ:")
        print(f"  Площадь (S_во): {geo.vertical_tail_area:.2f} м²")
        print(f"  Высота (l_во): {geo.v_tail_height:.2f} м")
        print(f"  Удлинение (λ_во): {geo.v_tail_aspect_ratio:.2f}")
        print(f"  Сужение (η_во): {geo.v_tail_taper_ratio:.3f}")
        print(f"  Корневая хорда (b_во_r): {geo.v_tail_chord_root:.3f} м")
        print(f"  Концевая хорда (b_во_t): {geo.v_tail_chord_tip:.3f} м")

        print("\nФЮЗЕЛЯЖ:")
        print(f"  Длина (L): {geo.fuselage_length:.2f} м")
        print(f"  Диаметр (D): {geo.fuselage_diameter:.3f} м")
        print(f"  Отношение L/D (λ_φ): {geo.fuselage_length_to_diameter_ratio:.2f}")
        print(f"  Объём: {geo.fuselage_volume:.2f} м³")
        print(f"  Смоченная площадь: {geo.fuselage_wetted_area:.1f} м²")

        print("\nСУММАРНЫЕ ПАРАМЕТРЫ:")
        print(f"  Полная смоченная площадь: {geo.total_wetted_area:.1f} м²")
        print(f"  Площадь сравнения (S_ref): {geo.reference_area:.1f} м²")

        print("\nШАССИ:")
        print(f"  Колея: {geo.landing_gear_width:.2f} м")
        print(f"  Клиренс: {geo.ground_clearance:.2f} м")

        print(f"\n{'=' * 70}")