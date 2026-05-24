"""
Модель данных проекта - основная структура для хранения всех расчётных параметров
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


# ===== ENUM классы для типов =====

class EngineTypeEnum(Enum):
    """Типы двигателей"""
    TURBOJET = "turbojet"
    TURBOPROP = "turboprop"

class WingChemeEnum(Enum):
    """Типы двигателей"""
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class WingFlapsTypeEnum(Enum):
    """Типы механизации крыла (закрылки)"""
    CLEAN_AIRFOIL = "clean_airfoil"
    PLAIN_FLAP = "plain_flap"
    SPLIT_FLAP = "split_flap"
    SLOTTED_FLAP = "slotted_flap"
    FOWLER_FLAP = "fowler_flap"
    DOUBLE_SLOTTED_FLAP = "double_slotted_flap"
    TRIPLE_SLOTTED_FLAP = "triple_slotted_flap"


class AircraftTypeEnum(Enum):
    """Типы летательных аппаратов"""
    BUSINESS_JET = "business_jet"
    SHORT_RANGE_JET_TRANSPORT = "short_range_jet_transport"
    MEDIUM_RANGE_JET_TRANSPORT = "medium_range_jet_transport"
    LONG_RANGE_JET_TRANSPORT = "long_range_jet_transport"
    ULTRA_LONG_RANGE_JET_TRANSPORT = "ultra_long_range_jet_transport"
    FIGHTER = "fighter"
    SUPERSONIC_CRUISE = "supersonic_cruise"


# ===== БЛОК 1: ПОСАДКА =====

@dataclass
class LandingData:
    """Данные для расчёта посадочных характеристик (Блок 1)"""

    # Основные параметры
    s_L: Optional[float] = None  # Посадочное расстояние [м]

    # Параметры аэродинамики
    s_LFL: Optional[float] = None  # Длина взлётно-посадочной полосы [м]
    C_L_max_L: Optional[float] = None  # Максимальный коэффициент подъёмной силы на посадке

    # Параметры ВС
    m_ML_per_m_MTO_ratio: Optional[float] = None  # Отношение посадочной массы к взлётной

    # Параметры двигателя
    engine_type: Optional[EngineTypeEnum] = None  # Тип двигателя
    wing_flaps_type: Optional[WingFlapsTypeEnum] = None  # Тип закрылков
    aircraft_type: Optional[AircraftTypeEnum] = None  # Тип ВС

    # Расчётные значения
    safety_factor: Optional[float] = None  # Коэффициент безопасности
    calculated_m_ML_per_S_W: Optional[float] = None  # Рассчитанное m_ML/S_W [кг/м²]


# ===== БЛОК 2: ВЗЛЁТ =====

@dataclass
class TakeoffData:
    """Данные для расчёта взлётных характеристик (Блок 2)"""

    # Основные параметры
    s_TO: Optional[float] = None  # Взлётное расстояние [м]

    # Параметры аэродинамики
    s_TOFL: Optional[float] = None  # Длина участка взлёта
    C_L_max_TO: Optional[float] = None  # Максимальный коэффициент подъёмной силы на взлёте

    # Параметры двигателя
    engine_type: Optional[EngineTypeEnum] = None  # Тип двигателя
    wing_flaps_type: Optional[WingFlapsTypeEnum] = None  # Тип закрылков
    aircraft_type: Optional[AircraftTypeEnum] = None  # Тип ВС

    # Расчётные значения
    safety_factor: Optional[float] = None  # Коэффициент безопасности
    calculated_denominator: Optional[float] = None  # Знаменатель из расчётов
    takeoff_slope: Optional[float] = None  # Коэффициент наклона


# ===== БЛОК 3: НАБОР ВЫСОТЫ =====

@dataclass
class ClimbData:
    """Данные для расчёта характеристик набора высоты (Блок 3)"""

    n_engines: Optional[int] = None  # Количество двигателей
    climb_gradient: Optional[float] = None  # Градиент набора высоты (sin(γ))

    # Расчётные значения
    gamma_sin: Optional[float] = None  # sin(γ) - синус угла набора высоты


# ===== БЛОК 4: КРЕЙСЕР И ТЯГОВООРУЖЁННОСТЬ =====

@dataclass
class CruiseData:
    """Данные для расчёта характеристик крейсера (Блок 4)"""

    # Параметры полёта
    # V_cruise: Optional[float] = None  # Скорость крейсера [м/с]
    h_cruise: Optional[float] = None  # Высота крейсера [м]

    # Аэродинамические коэффициенты
    C_D_0: Optional[float] = None  # Коэффициент лобового сопротивления
    K: Optional[float] = None  # Коэффициент индуктивного сопротивления

    # Атмосферные параметры
    rho_h: Optional[float] = None  # Плотность воздуха на высоте [кг/м³]
    sigma_h: Optional[float] = None  # Относительная плотность воздуха

    # Параметры ВС
    C_L_cruise: Optional[float] = None  # Коэффициент подъёмной силы в крейсере
    E_max: Optional[float] = None  # Максимальное аэродинамическое качество (L/D)

    # Расчётные значения
    T_W_cruise: Optional[float] = None  # T/W в крейсере
    T_W_climb_final: Optional[float] = None  # T/W для набора высоты (итоговое)


# ===== БЛОК 5: ПРЕРВАННАЯ ПОСАДКА =====

@dataclass
class MissedApproachData:
    """Данные для расчёта характеристик прерванной посадки (Блок 5)"""

    climb_gradient_ma: Optional[float] = None  # Градиент набора высоты при прерванной посадке

    # Расчётные значения
    gamma_sin_ma: Optional[float] = None  # sin(γ) для прерванной посадки


# ===== БЛОК 6: АЭРОДИНАМИЧЕСКИЙ АНАЛИЗ =====

@dataclass
class AeroAnalysisData:
    """Данные для аэродинамического анализа (Блок 6)"""

    # Параметры полёта в особых режимах
    V_ma: Optional[float] = None  # Скорость при прерванной посадке [м/с]
    h_ma: Optional[float] = None  # Высота при прерванной посадке [м] (обычно 0)

    # Аэродинамические коэффициенты
    C_D_0_landing: Optional[float] = None  # Коэффициент лобового сопротивления при посадке
    K_landing: Optional[float] = None  # Коэффициент индуктивного сопротивления при посадке

    # Атмосферные параметры
    rho_ma: Optional[float] = None  # Плотность воздуха в режиме прерванной посадки [кг/м³]

    # Параметры ВС
    C_L_ma: Optional[float] = None  # Коэффициент подъёмной силы при прерванной посадке
    E_ma: Optional[float] = None  # Аэродинамическое качество при прерванной посадке (L/D)

    # Влияние механизации
    delta_C_D_0_flaps: Optional[float] = None  # Изменение C_D_0 от закрылков
    delta_C_D_0_gear: Optional[float] = None  # Изменение C_D_0 от шасси


# ===== БЛОК 7: T/W ДЛЯ ПРЕРВАННОЙ ПОСАДКИ =====

@dataclass
class MissedApproachTWData:
    """Данные для расчёта T/W при прерванной посадке (Блок 7)"""

    T_W_missed_approach: Optional[float] = None  # T/W при прерванной посадке

    # Расчётные значения
    calculated_numerator: Optional[float] = None  # Числитель из формулы
    mass_ratio_factor: Optional[float] = None  # Коэффициент отношения масс


# ===== БЛОК 8: ДИАГРАММА СОГЛАСОВАНИЯ =====

@dataclass
class MatchingChartData:
    """Данные для построения диаграммы согласования (Блок 8)"""

    # Диапазоны переменных
    wing_loading_range: Optional[Tuple[float, float]] = None  # Диапазон wing loading [кг/м²]
    tw_range: Optional[Tuple[float, float]] = None  # Диапазон T/W

    # Результаты оптимизации
    optimal_wing_loading: Optional[float] = None  # Оптимальное wing loading [кг/м²]
    optimal_tw_ratio: Optional[float] = None  # Оптимальное T/W

    # Кривые ограничений
    takeoff_curve_points: Optional[List[Tuple[float, float]]] = None  # Кривая взлёта (wing loading, T/W)
    climb_curve_points: Optional[List[Tuple[float, float]]] = None  # Кривая набора высоты
    cruise_curve_points: Optional[List[Tuple[float, float]]] = None  # Кривая крейсера
    missed_approach_curve_points: Optional[List[Tuple[float, float]]] = None  # Кривая прерванной посадки

    # Ограничения
    landing_limit: Optional[float] = None  # Ограничение по посадке (wing loading) [кг/м²]

@dataclass
class MassCalculationData:
    """Данные для расчёта масс ВС (Блок 9)"""

    # Входные параметры миссии
    payload_mass: Optional[float] = None  # Масса полезной нагрузки [кг]
    design_range: Optional[float] = None  # Дальность полёта [км]
    cruise_mach: Optional[float] = None  # Число Маха в крейсере
    cruise_altitude: Optional[float] = None  # Высота крейсера [м]

    # Параметры двигателя и топлива
    sfc_cruise: Optional[float] = None  # Удельный расход топлива в крейсере [кг/(кг·ч)]
    LD_cruise: Optional[float] = None  # Аэродинамическое качество в крейсере

    # Коэффициенты масс
    relative_oe_mass: Optional[float] = None  # Относительная масса конструкции (OE/MTO)
    relative_fuel_mass: Optional[float] = None  # Относительная масса топлива (Fuel/MTO)
    mission_fuel_fraction: Optional[float] = None  # Доля топлива для миссии
    breguet_factor: Optional[float] = None  # Фактор Бреге для расчёта топлива

    # Расчётные значения
    calculated_mto_mass: Optional[float] = None  # Рассчитанная взлётная масса [кг]
    iteration_count: Optional[int] = None  # Количество итераций для сходимости

# ===== БЛОК 10: ИТОГОВЫЕ ПАРАМЕТРЫ =====

@dataclass
class FinalParametersData:
    """Итоговые параметры проекта (Блок 10)"""

    # Тяга и площадь крыла
    final_takeoff_thrust: Optional[float] = None  # Итоговая взлётная тяга [Н]
    final_wing_area: Optional[float] = None  # Итоговая площадь крыла [м²]

    # Массы
    landing_mass: Optional[float] = None  # Посадочная масса [кг]
    operating_empty_mass: Optional[float] = None  # Пустая масса ВС [кг]
    fuel_mass: Optional[float] = None  # Масса топлива [кг]

    # Характеристики
    thrust_to_weight_final: Optional[float] = None  # Итоговое T/W
    wing_loading_final: Optional[float] = None  # Итоговое wing loading [кг/м²]



# === БЛОК 1: ПРЕДВАРИТЕЛЬНОЕ ОПРЕДЕЛЕНИЕ ПАРАМЕТРОВ ===
@dataclass
class PreliminarySizingData:

    # === ТРЕБОВАНИЯ ===
    # === СКОРОСТИ И ВЫСОТЫ ===
    V_min: Optional[float] = None
    h_min: Optional[float] = None

    V_max: Optional[float] = None
    h_max: Optional[float] = None

    V_cruise: Optional[float] = None
    h_cruise: Optional[float] = None

    V_y: Optional[float] = None  # скороподъёмность
    h_y: Optional[float] = None

    V_s: Optional[float] = None  # скорость сваливания
    h_s: Optional[float] = None

    # === ПЛОТНОСТИ ВОЗДУХА НА ОПРЕДЕЛЁННЫХ ВЫСОТАХ ===
    # todo: добавить модель атмосферы
    pho_V_min: Optional[float] = None
    pho_V_max: Optional[float] = None
    pho_V_cruise: Optional[float] = None
    pho_V_y: Optional[float] = None
    pho_V_s: Optional[float] = None

    n_max: Optional[float] = None  # эксплуатационная перегрузка
    theta: Optional[float] = None  # градиент набора высоты
    L_TODA: Optional[float] = None  # взлётная дистанция Takeoff Distance Available

    N: Optional[int] = None  # количество двигателей

    # === ВАРЬИРУЕМОЕ ===

    # максимальное значение коэффициента подъёмной силы
    C_y_max: Optional[float] = None

    # максимальное значение коэффициента подъёмной силы
    # со взлётной конфигурацией крыла
    C_y_max_TO: Optional[float] = None

    # коэффициент лобового сопротивления при нулевой подъёмной силе
    C_x0: Optional[float] = None

    Lambda: Optional[float] = None  # удлинение крыла
    e: Optional[float] = None  # коэффициент Освальда
    sigma: Optional[float] = None  # коэффициент, учитывающий высотность взлётной полосы

    # Набор точек для построения графиков
    p0_range = None
    P0_range = None
    p0_by_V_s = None
    P0_by_theta_points = None
    P0_by_n_max_points = None
    P0_by_L_TODA_points = None
    P0_by_V_y_points = None
    P0_by_V_cruise_points = None
    optimal_point = None
    p0_optimal = None
    P0_optimal = None


# === БЛОК 2: РАСЧЁТ МАСС ===
@dataclass
class MassEstimationData:
    """Данные для расчёта масс ВС (Блок 9)"""

    payload_mass: Optional[float] = None  # масса полезной нагрузки [кг]
    design_range: Optional[float] = None  # км

    fuel_reserve_factor: Optional[float] = None # коэффициент топливного резерва
    cruise_sfc: Optional[float] = None # удельный расход топлива
    cruise_L_D_ratio : Optional[float] = None # аэродинамическое качество при крейсерском полёте

    m_MTO: Optional[float] = None
    m_OE: Optional[float] = None
    m_F: Optional[float] = None
    m_ML: Optional[float] = None
    T_TO: Optional[float] = None
    S_W: Optional[float] = None
    m_OE_ratio: Optional[float] = None
    m_F_ratio: Optional[float] = None
    useful_load_ratio: Optional[float] = None


@dataclass
class GeometryData:
    """Геометрические параметры воздушного судна"""
    # Входные параметры
    # Крыло
    eta_wing: Optional[float] = None  # сужение крыла
    sweep_wing_quarter: Optional[float] = None  # угол стреловидности по линии ¼ хорды [град]
    wing_scheme: Optional[str] = None  # схема расположения крыла: 'high', 'mid', 'low'

    # Горизонтальное оперение (ГО)
    k_horizontal_tail: Optional[float] = None  # коэффициент площади ГО относительно крыла
    lambda_horizontal_tail: Optional[float] = None  # удлинение ГО
    eta_horizontal_tail: Optional[float] = None  # сужение ГО
    sweep_horizontal_tail_quarter: Optional[float] = None  # угол стреловидности ГО [град]

    # Вертикальное оперение (ВО)
    k_vertical_tail: Optional[float] = None  # коэффициент площади ВО относительно крыла
    lambda_vertical_tail: Optional[float] = None  # удлинение ВО
    eta_vertical_tail: Optional[float] = None  # сужение ВО
    sweep_vertical_tail_quarter: Optional[float] = None  # угол стреловидности ВО [град]

    # Фюзеляж
    k_fuselage: Optional[float] = None  # коэффициент длины фюзеляжа
    lambda_fuselage: Optional[float] = None  # удлинение фюзеляжа
    x_fuselage: Optional[float] = None  # X-координата фюзеляжа [м]

    # Расчётные параметры
    # Крыло
    l_wing: Optional[float] = None  # размах крыла [м]
    b0_wing: Optional[float] = None  # корневая хорда крыла [м]
    bk_wing: Optional[float] = None  # концевая хорда крыла [м]
    sweep_wing_LE: Optional[float] = None  # угол стреловидности по передней кромке [град]
    y_wing: Optional[float] = None  # Y-координата крыла [м]

    # Горизонтальное оперение (ГО)
    S_ht: Optional[float] = None  # площадь ГО [м²]
    l_ht: Optional[float] = None  # размах ГО [м]
    b0_ht: Optional[float] = None  # корневая хорда ГО [м]
    bk_ht: Optional[float] = None  # концевая хорда ГО [м]
    sweep_ht_LE: Optional[float] = None  # угол стреловидности ГО по передней кромке [град]
    x_ht: Optional[float] = None  # X-координата ГО [м]
    y_ht: Optional[float] = None  # Y-координата ГО [м]

    # Вертикальное оперение (ВО)
    S_vt: Optional[float] = None  # площадь ВО [м²]
    l_vt: Optional[float] = None  # высота ВО [м]
    b0_vt: Optional[float] = None  # корневая хорда ВО [м]
    bk_vt: Optional[float] = None  # концевая хорда ВО [м]
    sweep_vt_LE: Optional[float] = None  # угол стреловидности ВО по передней кромке [град]
    x_vt: Optional[float] = None  # X-координата ВО [м]

    # Фюзеляж
    L_fuselage: Optional[float] = None  # длина фюзеляжа [м]
    d_fuselage: Optional[float] = None  # эквивалентный диаметр фюзеляжа [м]
    r_fuselage: Optional[float] = None  # радиус фюзеляжа [м]


# ===== ГЛАВНАЯ МОДЕЛЬ ПРОЕКТА =====


@dataclass
class ProjectData:
    """Главная модель данных проекта - объединяет все блоки"""

    preliminary_sizing: PreliminarySizingData = field(default=PreliminarySizingData)
    mass_estimation: MassEstimationData = field(default=MassEstimationData)


    # Тип ВС
    aircraft_type: Optional[AircraftTypeEnum] = None

    # Подструктуры для каждого блока
    landing_data: LandingData = field(default_factory=LandingData)  # Блок 1
    takeoff_data: TakeoffData = field(default_factory=TakeoffData)  # Блок 2
    climb_data: ClimbData = field(default_factory=ClimbData)  # Блок 3
    cruise_data: CruiseData = field(default_factory=CruiseData)  # Блок 4
    missed_approach_data: MissedApproachData = field(default_factory=MissedApproachData)  # Блок 5
    aero_analysis_data: AeroAnalysisData = field(default_factory=AeroAnalysisData)  # Блок 6
    missed_approach_tw_data: MissedApproachTWData = field(default_factory=MissedApproachTWData)  # Блок 7
    matching_chart_data: MatchingChartData = field(default_factory=MatchingChartData)  # Блок 8
    mass_calculation_data: MassCalculationData = field(default_factory=MassCalculationData)  # Блок 9
    final_parameters_data: FinalParametersData = field(default_factory=FinalParametersData)  # Блок 10
    geometry_data: GeometryData = field(default_factory=GeometryData)  # Блок 11

    # Ключевые интегральные параметры (для ссылок с блоков 1-7)
    takeoff_slope: Optional[float] = None  # Коэффициент наклона
    m_MTO_per_S_W: Optional[float] = None  # Wing loading = m_MTO / S_W [кг/м²] (из блока 1)
    T_TO_per_m_MTO_g: Optional[float] = None  # Взлётный коэффициент тяги = T_TO / (m_MTO * g) (из блока 2)
    T_W_climb: Optional[float] = None  # T/W для набора высоты (из блока 3-4)
    T_W_missed_approach: Optional[float] = None  # T/W для прерванной посадки (из блока 7)

    # Итоговые результаты оптимизации (из блока 8)
    optimal_wing_loading: Optional[float] = None  # Оптимальное wing loading [кг/м²]
    optimal_tw_ratio: Optional[float] = None  # Оптимальное T/W

    # Взлётная масса (из блока 9)
    m_MTO: Optional[float] = None  # Взлётная масса [кг]

    # Площадь крыла (из блока 10)
    S_W: Optional[float] = None  # Площадь крыла [м²]

    T_TO: Optional[float] = None

    # Параметры для блока 11 (специальные поля)
    S_h: Optional[float] = None  # Площадь горизонтального оперения [м²]
    S_v: Optional[float] = None  # Площадь вертикального оперения [м²]
    k_phi: Optional[float] = None  # Коэффициент длины фюзеляжа
    lambda_phi: Optional[float] = None  # Отношение L/D фюзеляжа


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def create_empty_project() -> ProjectData:
    """Создаёт пустой проект с инициализированными структурами"""
    return ProjectData()


def get_all_field_names(dataclass_instance) -> List[str]:
    """Получает список всех имён полей в dataclass"""
    from dataclasses import fields
    return [f.name for f in fields(dataclass_instance)]