from __future__ import annotations

from typing import Any
from aircraft_design.core.models.parameter import Parameter, rule_min, rule_max,rule_positive


class DataGroup:
    """Базовый класс для групп параметров. Привязывается к главному объекту проекта."""

    def __init__(self, project: 'ProjectState'):
        self._project = project


class FeasibilityData(DataGroup):
    """Данные для блока оценки реализуемости."""

    # --- Входные параметры ---
    powerplant_type = Parameter(
        "Тип силовой установки", category="Общие", default="ice", choices=("electric", "ice", "hybrid"),
        description="Определяет физические принципы расчета масс и потребления энергии в алгоритме."
    )
    target_takeoff_mass = Parameter(
        "Целевая взлётная масса", unit="кг", default=3600.0, rules=[rule_positive],
        description="Начальное приближение массы для оценки реализуемости концепта и подбора аналогов."
    )
    design_range = Parameter(
        "Практическая дальность", unit="км", default=650.0, rules=[rule_positive],
        description="Расчетная дальность полета с учетом АНЗ (аэронавигационного запаса) топлива."
    )
    flight_duration_h = Parameter(
        "Длительность полёта", unit="ч", default=4.0, rules=[rule_positive],
        description="Время нахождения в воздухе для заданного профиля миссии."
    )
    max_speed = Parameter(
        "Максимальная скорость", unit="км/ч", default=210.0, rules=[rule_positive],
        description="Максимальная скорость горизонтального полета у земли (V_max)."
    )
    practical_ceiling_m = Parameter(
        "Практический потолок", unit="м", default=5000.0, rules=[rule_positive],
        description="Высота, на которой вертикальная скороподъемность падает до 0.5 м/с."
    )
    payload_mass = Parameter(
        "Полезная нагрузка", unit="кг", default=520.0, rules=[rule_min(0)],
        description="Масса коммерческой нагрузки (пассажиры, багаж, целевое оборудование)."
    )

    # --- Выходные параметры ---
    project_score = Parameter(
        "Комплексный показатель", category="Результат", is_input=False,
        description="Расчетный критерий эффективности проекта (учитывает массу, дальность, скорость и ПН)."
    )
    max_stat_score = Parameter(
        "Показатель аналога", category="Результат", is_input=False,
        description="Критерий эффективности лучшего реально существующего самолета из статистической базы."
    )
    best_analog_name = Parameter(
        "Лучший аналог", category="Результат", default="", is_input=False,
        description="Название самолета-конкурента с наиболее близкими летно-техническими характеристиками."
    )
    is_feasible = Parameter(
        "Реализуемость", category="Результат", default=False, is_input=False,
        description="Флаг успешности: показывает, превосходит ли проект лучший мировой аналог."
    )


class PreliminarySizingData(DataGroup):
    """Данные для блока предварительного расчета."""

    # --- Входные параметры ---
    N = Parameter(
        "Количество двигателей", default=2, rules=[rule_min(1)],
        description="Число маршевых двигателей. Влияет на статистическую массу систем и вероятность отказа."
    )
    theta = Parameter(
        "Градиент набора высоты", default=0.06, rules=[rule_positive],
        description="Требуемый нормами летной годности (АП/FAR) градиент климба при отказе одного двигателя."
    )
    C_x0 = Parameter(
        "Коэф. лобового сопротивления", default=0.04, rules=[rule_positive],
        description="Сх0. Сопротивление самолета при нулевой подъемной силе. Зависит от аэродинамической чистоты."
    )
    Lambda = Parameter(
        "Удлинение крыла", default=12.19, rules=[rule_positive],
        description="Отношение квадрата размаха к площади крыла. Чем выше, тем меньше индуктивное сопротивление."
    )
    e = Parameter(
        "Коэффициент Освальда", default=0.68, rules=[rule_positive, rule_max(1.0)],
        description="Эффективность крыла. Учитывает отклонение реального распределения циркуляции от эллиптического (обычно 0.6-0.85)."
    )
    n_max = Parameter(
        "Макс. экспл. перегрузка", default=2.5, rules=[rule_min(1.0)],
        description="Максимальная нормальная перегрузка в маневре или при вертикальном порыве ветра."
    )
    sigma = Parameter(
        "Относ. плотность (взлёт)", default=1.0, rules=[rule_positive],
        description="Отношение плотности воздуха на аэродроме взлета к плотности на уровне моря (МСА)."
    )
    V_s = Parameter(
        "Скорость сваливания", unit="м/с", default=20.0, rules=[rule_positive],
        description="Минимальная эволютивная скорость полета во взлетно-посадочной конфигурации."
    )
    V_cruise = Parameter(
        "Крейсерская скорость", unit="м/с", default=48.0, rules=[rule_positive],
        description="Скорость, на которой выполняется основной участок маршрута."
    )
    V_y = Parameter(
        "Скороподъёмность", unit="м/с", default=10.0, rules=[rule_positive],
        description="Вертикальная скорость набора высоты на номинальном режиме работы двигателей."
    )
    C_y_max = Parameter(
        "Макс. Cy (посадка)", default=1.6, rules=[rule_positive],
        description="Максимальный коэффициент подъемной силы с полностью выпущенной механизацией."
    )
    C_y_max_TO = Parameter(
        "Макс. Cy (взлёт)", default=2.6, rules=[rule_positive],
        description="Максимальный коэффициент подъемной силы во взлетной конфигурации."
    )
    L_TODA = Parameter(
        "Взлётная дистанция", unit="м", default=150.0, rules=[rule_positive],
        description="Требуемая дистанция для разбега и набора безопасной высоты над препятствием (обычно 15 м)."
    )
    pho_V_s = Parameter("Плотность воздуха при сваливании", unit="кг/м³", default=1.225, rules=[rule_positive])
    pho_V_cruise = Parameter("Плотность воздуха в крейсере", unit="кг/м³", default=1.06, rules=[rule_positive])
    pho_V_y = Parameter("Плотность воздуха при наборе", unit="кг/м³", default=1.1, rules=[rule_positive])

    # --- Выходные параметры ---
    p0_optimal = Parameter(
        "Опт. нагрузка на крыло", unit="Н/м²", is_input=False,
        description="Оптимальная удельная нагрузка на крыло, обеспечивающая выполнение всех заданных летных требований."
    )
    P0_optimal = Parameter(
        "Опт. тяговооружённость", is_input=False,
        description="Требуемая стартовая тяговооруженность (или энерговооруженность) для взлета и набора высоты."
    )
    C_x_for_max_K = Parameter(
        "Cx для макс. качества", is_input=False,
        description="Коэффициент лобового сопротивления при полете на наивыгоднейшем угле атаки."
    )
    C_y_for_max_K = Parameter(
        "Cy для макс. качества", is_input=False,
        description="Коэффициент подъемной силы, при котором достигается максимальное аэродинамическое качество."
    )
    K_max = Parameter(
        "Макс. аэродин. качество", is_input=False,
        description="Максимально достижимое аэродинамическое качество самолета (показатель аэродинамического совершенства)."
    )


class MassEstimationData(DataGroup):
    """Данные для блока расчета масс."""

    # --- Входные параметры ---
    service_load_mass = Parameter(
        "Масса служебной нагрузки", unit="кг", default=0.0, rules=[rule_min(0)],
        description="Масса экипажа, снаряжения, невырабатываемого остатка топлива и масла."
    )
    battery_equipment_mass = Parameter("Масса обор. АКБ", unit="кг", default=0.0, rules=[rule_min(0)])
    control_equipment_mass = Parameter("Масса обор. управления", unit="кг", default=0.0, rules=[rule_min(0)])
    cruise_L_D_ratio = Parameter(
        "Аэродинамическое качество", default=10.0, rules=[rule_positive],
        description="Отношение подъемной силы к лобовому сопротивлению (K) на крейсерском режиме."
    )
    is_maneuverable = Parameter(
        "Маневренный самолёт", default=False,
        description="Определяет повышенные требования к жесткости конструкции и весовые коэффициенты."
    )
    is_under_2_5kg = Parameter("Масса менее 2.5 кг", default=False)
    battery_specific_energy_wh_kg = Parameter(
        "Удельная энергия АКБ", unit="Вт·ч/кг", default=250.0, rules=[rule_positive],
        description="Плотность энергии элементов питания (например, Li-Ion/Li-Po)."
    )
    electric_powertrain_efficiency = Parameter("КПД электродвигателя", default=0.8, rules=[rule_positive, rule_max(1)])
    cruise_altitude_m = Parameter("Крейсерская высота", unit="м", default=0.0, rules=[rule_min(0)])
    power_loading_N0_kw_kg = Parameter(
        "Энерговооружённость", unit="кВт/кг", default=0.05, rules=[rule_min(0)],
        description="Отношение мощности силовой установки к взлетной массе ЛА."
    )
    cruise_sfc_power = Parameter(
        "Удельный расход топлива", unit="кг/(л.с.·ч)", default=0.26, rules=[rule_positive],
        description="Часовой расход топлива на единицу мощности. Используется в формуле Бреге."
    )
    propeller_efficiency = Parameter("КПД винта", default=0.8, rules=[rule_positive, rule_max(1)])
    engine_type = Parameter("Тип двигателя", default="piston", choices=("piston", "turboprop"))
    takeoff_power_hp = Parameter("Взлётная мощность", unit="л.с.", default=1.0, rules=[rule_positive])
    wing_relative_thickness = Parameter(
        "Относ. толщина крыла", default=0.12, rules=[rule_positive, rule_max(0.2)],
        description="Отношение максимальной толщины профиля к хорде. Влияет на массу крыла и сопротивление."
    )
    f_factor = Parameter(
        "Коэффициент безопасности", default=2.0, rules=[rule_min(1.5), rule_max(3)],
        description="Коэффициент запаса прочности (f). По нормам обычно равен 1.5 - 2.0."
    )
    wing_material_factor = Parameter("Массовый коэф. крыла", default=1.0, rules=[rule_positive])
    wing_position = Parameter(
        "Расположение крыла", default="high", choices=("high", "low"),
        description="Влияет на массу силовых шпангоутов фюзеляжа и конструкцию шасси."
    )
    has_landing_gear = Parameter("Наличие шасси", default=True)
    landing_gear_material = Parameter("Материал шасси", default="medium_steel",
                                      choices=("medium_steel", "high_strength_metal"))
    landing_gear_fairing = Parameter("Обтекатель шасси", default="none",
                                     choices=("none", "wheel_fairings", "retractable"))
    landing_gear_type = Parameter("Тип шасси", default="wheeled", choices=("ski", "wheeled"))
    has_brakes = Parameter("Наличие тормозов", default=True)
    landing_gear_strut_length_m = Parameter("Высота стойки шасси", unit="м", default=0.2, rules=[rule_min(0)])
    wing_loading_tolerance = Parameter(
        "Допуск итераций", default=0.10, rules=[rule_positive],
        description="Критерий сходимости итерационного расчета массы (относительная невязка)."
    )
    max_iterations = Parameter(
        "Максимум итераций", default=30, rules=[rule_min(1)],
        description="Предотвращает зацикливание программы, если баланс масс не сходится."
    )

    # --- Выходные параметры ---
    m_MTO = Parameter(
        "Максимальная взлётная масса", unit="кг", is_input=False,
        description="Итоговая расчетная масса самолета перед стартом (M0)."
    )
    m_OE = Parameter(
        "Масса пустого самолёта", unit="кг", is_input=False,
        description="Масса конструкции, силовой установки и оборудования без учета полезной нагрузки и топлива."
    )
    m_F = Parameter(
        "Масса топлива / АКБ", unit="кг", is_input=False,
        description="Требуемая масса энергоносителя для выполнения заданного профиля полета."
    )
    T_TO = Parameter(
        "Взлётная тяга", unit="Н", is_input=False,
        description="Потребная суммарная тяга силовой установки для безопасного взлета."
    )
    S_W = Parameter(
        "Площадь крыла", unit="м²", is_input=False,
        description="Потребная площадь несущей поверхности на основе оптимальной нагрузки на крыло."
    )
    m_OE_ratio = Parameter("Относит. масса пустого", is_input=False, description="Доля массы пустого самолета в МВМ.")
    m_F_ratio = Parameter("Относит. масса топлива", is_input=False, description="Доля массы топлива (или АКБ) в МВМ.")
    useful_load_ratio = Parameter("Относит. полезная нагрузка", is_input=False,
                                  description="Доля коммерческой и служебной нагрузки в МВМ.")
    converged = Parameter("Итерация сошлась", is_input=False,
                          description="Успешность схождения итерационного баланса масс.")
    iterations = Parameter("Кол-во итераций", is_input=False,
                           description="Затраченное количество шагов пересчета массы.")
    wing_loading_relative_delta = Parameter("Невязка итераций", is_input=False,
                                            description="Фактическая ошибка массы между последними шагами расчета.")
    structure_mass_ratio = Parameter("Относит. масса конструкции", is_input=False,
                                     description="Суммарная доля массы крыла, фюзеляжа, оперения и шасси.")


class TechnologyData(DataGroup):
    """Данные для экономического расчёта и планирования."""

    # --- Входные параметры ---
    NLA = Parameter(
        "Количество ЛА в партии", unit="шт", default=100.0, rules=[rule_positive],
        description="Программа выпуска самолетов. Сильно влияет на амортизацию технологической оснастки."
    )
    T = Parameter(
        "Срок выполнения заказа", unit="нед", default=50.0, rules=[rule_positive],
        description="Заданное время на выпуск всей партии ЛА."
    )

    # --- Выходные параметры ---
    best_cost_seb1 = Parameter(
        "Себестоимость 1 экземпляра", unit="руб.", is_input=False,
        description="Минимальная расчетная производственная себестоимость при оптимальных технологиях."
    )
    CSUM_total = Parameter(
        "Суммарная стоимость партии", unit="руб.", is_input=False,
        description="Общая стоимость производства заданного количества летательных аппаратов."
    )
    CLA_I_materials = Parameter(
        "Стоимость материалов", unit="руб.", is_input=False,
        description="Затраты на все конструкционные материалы для партии."
    )
    COSN_machines = Parameter(
        "Стоимость станков/оснастки", unit="руб.", is_input=False,
        description="Амортизационные отчисления на производственное оборудование."
    )
    CTRUD_labor = Parameter(
        "Фонд оплаты труда", unit="руб.", is_input=False,
        description="Суммарная заработная плата производственных рабочих."
    )
    CSPL_space = Parameter(
        "Стоимость площадей", unit="руб.", is_input=False,
        description="Затраты на содержание производственных, складских и административных помещений."
    )

    wing_skin_tech = Parameter("Технология обшивки крыла", is_input=False,
                               description="Выбранный оптимальный техпроцесс изготовления.")
    wing_trans_tech = Parameter("Технология попер. набора крыла", is_input=False,
                                description="Выбранный оптимальный техпроцесс изготовления.")
    wing_long_tech = Parameter("Технология прод. набора крыла", is_input=False,
                               description="Выбранный оптимальный техпроцесс изготовления.")

    fuse_skin_tech = Parameter("Технология обшивки фюзеляжа", is_input=False,
                               description="Выбранный оптимальный техпроцесс изготовления.")
    fuse_trans_tech = Parameter("Технология попер. набора фюзеляжа", is_input=False,
                                description="Выбранный оптимальный техпроцесс изготовления.")
    fuse_long_tech = Parameter("Технология прод. набора фюзеляжа", is_input=False,
                               description="Выбранный оптимальный техпроцесс изготовления.")

    tail_skin_tech = Parameter("Технология обшивки оперения", is_input=False,
                               description="Выбранный оптимальный техпроцесс изготовления.")
    tail_trans_tech = Parameter("Технология попер. набора оперения", is_input=False,
                                description="Выбранный оптимальный техпроцесс изготовления.")
    tail_long_tech = Parameter("Технология прод. набора оперения", is_input=False,
                               description="Выбранный оптимальный техпроцесс изготовления.")

    m0_new = Parameter(
        "Уточнённая взлётная масса", unit="кг", is_input=False,
        description="Масса самолета, пересчитанная после детального производственно-экономического расчета."
    )


class GeometryData(DataGroup):
    """Данные для блока расчета геометрии."""

    # --- Входные параметры (Крыло) ---
    eta_wing = Parameter(
        "Сужение крыла", default=2.5, rules=[rule_positive],
        description="Отношение корневой хорды к концевой. Влияет на распределение циркуляции и массу."
    )
    sweep_wing_quarter = Parameter(
        "Стреловидность крыла (1/4)", unit="град", default=25.0,
        description="Угол стреловидности по линии четвертей хорд."
    )
    wing_scheme = Parameter("Схема крыла", default="low", choices=("low", "mid", "high"))

    # --- Входные параметры (ГО) ---
    k_horizontal_tail = Parameter(
        "Коэф. площади ГО", default=0.25, rules=[rule_positive],
        description="Статистический коэффициент для определения требуемой площади горизонтального оперения."
    )
    lambda_horizontal_tail = Parameter("Удлинение ГО", default=4.0, rules=[rule_positive])
    eta_horizontal_tail = Parameter("Сужение ГО", default=3.0, rules=[rule_positive])
    sweep_horizontal_tail_quarter = Parameter("Стреловидность ГО (1/4)", unit="град", default=30.0)

    # --- Входные параметры (ВО) ---
    k_vertical_tail = Parameter(
        "Коэф. площади ВО", default=0.15, rules=[rule_positive],
        description="Статистический коэффициент для определения требуемой площади вертикального оперения."
    )
    lambda_vertical_tail = Parameter("Удлинение ВО", default=1.5, rules=[rule_positive])
    eta_vertical_tail = Parameter("Сужение ВО", default=2.0, rules=[rule_positive])
    sweep_vertical_tail_quarter = Parameter("Стреловидность ВО (1/4)", unit="град", default=35.0)

    # --- Входные параметры (Фюзеляж) ---
    k_fuselage = Parameter("Коэффициент длины фюзеляжа", default=1.2, rules=[rule_positive])
    lambda_fuselage = Parameter("Удлинение фюзеляжа", default=9.0, rules=[rule_positive])

    # --- Выходные параметры (is_input=False) ---
    # Крыло
    l_wing = Parameter("Размах крыла", unit="м", is_input=False, description="Расстояние между законцовками крыла.")
    b0_wing = Parameter("Корневая хорда крыла", unit="м", is_input=False,
                        description="Длина профиля крыла в плоскости симметрии самолета.")
    bk_wing = Parameter("Концевая хорда крыла", unit="м", is_input=False, description="Длина концевого профиля крыла.")
    sweep_wing_LE = Parameter("Стреловидность крыла (ПК)", unit="град", is_input=False,
                              description="Угол стреловидности крыла по передней кромке.")
    wing_scheme_ru = Parameter("Схема крыла (название)", is_input=False, default="")
    y_wing = Parameter("Положение крыла по Y", unit="м", is_input=False,
                       description="Вертикальное смещение крыла относительно продольной оси фюзеляжа.")

    # Фюзеляж
    L_fuselage = Parameter("Длина фюзеляжа", unit="м", is_input=False, description="Общая габаритная длина фюзеляжа.")
    d_fuselage = Parameter("Диаметр фюзеляжа", unit="м", is_input=False,
                           description="Максимальный эквивалентный диаметр миделевого сечения.")
    r_fuselage = Parameter("Радиус фюзеляжа", unit="м", is_input=False,
                           description="Максимальный радиус фюзеляжа (для экспорта геометрии).")
    x_fuselage = Parameter("Координата носа фюзеляжа", unit="м", is_input=False,
                           description="Положение крайней передней точки фюзеляжа по оси X.")

    # ГО
    S_ht = Parameter("Площадь ГО", unit="м²", is_input=False,
                     description="Вычисленная площадь горизонтального оперения.")
    l_ht = Parameter("Размах ГО", unit="м", is_input=False, description="Габаритный размах стабилизатора.")
    b0_ht = Parameter("Корневая хорда ГО", unit="м", is_input=False, description="Длина профиля ГО в корневом сечении.")
    bk_ht = Parameter("Концевая хорда ГО", unit="м", is_input=False, description="Длина профиля на законцовке ГО.")
    sweep_ht_LE = Parameter("Стреловидность ГО (ПК)", unit="град", is_input=False,
                            description="Угол стреловидности ГО по передней кромке.")
    x_ht = Parameter("Положение ГО по X", unit="м", is_input=False,
                     description="Продольная координата корневой хорды ГО.")
    y_ht = Parameter("Положение ГО по Y", unit="м", is_input=False,
                     description="Вертикальное смещение ГО (для T-образного или обычного оперения).")

    # ВО
    S_vt = Parameter("Площадь ВО", unit="м²", is_input=False,
                     description="Вычисленная площадь вертикального оперения (киля).")
    l_vt = Parameter("Высота ВО", unit="м", is_input=False,
                     description="Геометрическая высота киля от корневой хорды до законцовки.")
    b0_vt = Parameter("Корневая хорда ВО", unit="м", is_input=False,
                      description="Длина корневой хорды вертикального оперения.")
    bk_vt = Parameter("Концевая хорда ВО", unit="м", is_input=False,
                      description="Длина концевой хорды вертикального оперения.")
    sweep_vt_LE = Parameter("Стреловидность ВО (ПК)", unit="град", is_input=False,
                            description="Угол стреловидности ВО по передней кромке.")
    x_vt = Parameter("Положение ВО по X", unit="м", is_input=False,
                     description="Продольная координата корневой хорды ВО.")


class ProjectState:
    """
    Единый объект состояния проекта. Хранит все параметры, логи, предупреждения и трассировку.
    """

    def __init__(self):
        # Метаданные расчета
        self.schema_version = "2.0"
        self.current_block: str | None = None

        # Логи и результаты
        self.warnings: list[str] = []
        self.errors: list[str] = []
        self.trace_records: list[dict[str, Any]] = []
        self.databases: dict[str, Any] = {}  # DataFrame'ы таблиц

        # Группы параметров
        self.feasibility = FeasibilityData(self)
        self.preliminary = PreliminarySizingData(self)
        self.mass = MassEstimationData(self)
        self.geometry = GeometryData(self)
        self.technology = TechnologyData(self)

    def add_warning(self, msg: str) -> None:
        """Добавляет предупреждение из любого места программы."""
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        """Добавляет критическую ошибку, которая остановит расчет."""
        self.errors.append(msg)

    def add_trace(self, value_name: str, formula: str, values: dict, result: Any, unit: str = "", description: str = "") -> None:
        """Записывает след вычисления формулы."""
        self.trace_records.append({
            "block": self.current_block,
            "value_name": value_name,
            "formula": formula,
            "values": values,
            "result": result,
            "unit": unit,
            "description": description
        })