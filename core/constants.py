"""
Константы приложения Matching Chart
"""
import math

# Общепринятые константы
PI = math.pi
g = 9.80665  # м/с²


# Русские названия параметров
FIELD_LABELS = {
    # Общие и аэродинамические характеристики самолета
    'N': 'Количество двигателей',
    'Lambda': 'Удлинение крыла',
    'e': 'Коэффициент Освальда',
    'C_x0': 'Коэффициент лобового сопротивления при нулевой подъёмной силе',
    'n_max': 'Эксплуатационная перегрузка',
    
    # Характеристики крыла и взлетно-посадочные параметры
    'C_y_max': 'Максимальное значение коэффициента подъёмной силы',
    'C_y_max_TO': 'Максимальное значение коэффициента подъёмной силы со взлётной конфигурацией крыла',
    'V_s': 'Скорость сваливания',
    'L_TODA': 'Взлётная дистанция',
    'sigma': 'Коэффициент, учитывающий высотность взлётной полосы',

    # Характеристики высотного / крейсерского полета
    'V_cruise': 'Крейсерская скорость полёта',
    'theta': 'Градиент набора высоты',
    'V_y': 'Скороподъёмность',

    # Физические условия (плотность воздуха)
    'pho_V_s': 'Плотность воздуха при V_s',
    'pho_V_cruise': 'Плотность воздуха при V_cruise',
    'pho_V_y': 'Плотность воздуха при V_y',

    'p0_optimal': 'Удельная нагрузка на крыло',
    'P0_optimal': 'Тяговооружённость',

    # Целевые параметры
    'payload_mass': 'Масса полезной нагрузки',
    'design_range': 'Дальность полёта',

    # Для расчёта масс
    'fuel_reserve_factor': 'Коэффициент топливного резерва',
    'cruise_sfc': 'Удельный расход топлива в крейсерском режиме',
    'cruise_L_D_ratio': 'Аэродинамическое качество в крейсерском режиме',

    'm_MTO': 'Максимальная взлётная масса',
    'm_OE': 'Эксплуатационная масса пустого самолёта',
    'm_F': 'Масса топлива',
    'm_ML': 'Максимальная посадочная масса',
    'T_TO': 'Взлётная тяга',
    'S_W': 'Площадь крыла',

    # Параметры крыла
    'eta_wing': 'Сужение крыла',
    'sweep_wing_quarter': 'Угол стреловидности крыла по линии ¼ хорды',
    'wing_scheme': 'Схема расположения крыла',

    # Параметры горизонтального оперения (ГО)
    'k_horizontal_tail': 'Коэффициент площади ГО',
    'lambda_horizontal_tail': 'Удлинение ГО',
    'eta_horizontal_tail': 'Сужение ГО',
    'sweep_horizontal_tail_quarter': 'Угол стреловидности ГО по линии ¼ хорды',

    # Параметры вертикального оперения (ВО)
    'k_vertical_tail': 'Коэффициент площади ВО',
    'lambda_vertical_tail': 'Удлинение ВО',
    'eta_vertical_tail': 'Сужение ВО',
    'sweep_vertical_tail_quarter': 'Угол стреловидности ВО по линии ¼ хорды',

    # Параметры фюзеляжа
    'k_fuselage': 'Коэффициент длины фюзеляжа',
    'lambda_fuselage': 'Удлинение фюзеляжа',
    'x_fuselage': 'X-координата фюзеляжа',  # нужна ли?

    # Выходные параметры геометрии
    'l_wing': 'Размах крыла',
    'b0_wing': 'Корневая хорда крыла',
    'bk_wing': 'Концевая хорда крыла',
    'sweep_wing_LE': 'Угол стреловидности крыла по передней кромке',

    'S_ht': 'Площадь горизонтального оперения',
    'l_ht': 'Размах горизонтального оперения',
    'b0_ht': 'Корневая хорда ГО',
    'bk_ht': 'Концевая хорда ГО',
    'sweep_ht_LE': 'Угол стреловидности ГО по передней кромке',
    'x_ht': 'Х-координата ГО',
    'y_ht': 'Y-координата ГО',

    'S_vt': 'Площадь вертикального оперения',
    'l_vt': 'Высота вертикального оперения',
    'b0_vt': 'Корневая хорда ВО',
    'bk_vt': 'Концевая хорда ВО',
    'sweep_vt_LE': 'Угол стреловидности ВО по передней кромке',
    'x_vt': 'Х-координата ВО',

    'L_fuselage': 'Длина фюзеляжа',
    'd_fuselage': 'Эквивалентный диаметр фюзеляжа',
    'r_fuselage': 'Радиус фюзеляжа',
    'y_wing': 'Y-координата крыла',
}

# Единицы измерения
FIELD_UNITS = {
    # Общие и аэродинамические характеристики самолета
    'N': '-',
    'Lambda': '-',
    'e': '-',
    'C_x0': '-',
    'n_max': '-',

    # Характеристики крыла и взлетно-посадочные параметры
    'C_y_max': '-',
    'C_y_max_TO': '-',
    'V_s': 'м/с',
    'L_TODA': 'м',
    'sigma': '-',

    # Характеристики высотного / крейсерского полета
    'V_cruise': 'м/с',
    'theta': '-',
    'V_y': 'м/с',

    # Физические условия (плотность воздуха)
    'pho_V_s': 'кг/м³',
    'pho_V_cruise': 'кг/м³',
    'pho_V_y': 'кг/м³',

    # Выходные данные
    'p0_optimal': 'Н/м²',
    'P0_optimal': '-',

    # Целевые параметры
    'payload_mass': 'кг',
    'design_range': 'км',

    # Характеристики масс

    'fuel_reserve_factor': '-',
    'cruise_sfc': 'кг/(Н·с)',
    'cruise_L_D_ratio': '-',

    'm_MTO': 'кг',
    'm_OE': 'кг',
    'm_F': 'кг',
    'm_ML': 'кг',
    'T_TO': 'Н',
    'S_W': 'м²',

    'eta_wing': '-',
    'sweep_wing_quarter': 'град',
    'wing_scheme': '-',
    'k_horizontal_tail': '-',
    'lambda_horizontal_tail': '-',
    'eta_horizontal_tail': '-',
    'sweep_horizontal_tail_quarter': 'град',
    'k_vertical_tail': '-',
    'lambda_vertical_tail': '-',
    'eta_vertical_tail': '-',
    'sweep_vertical_tail_quarter': 'град',
    'k_fuselage': '-',
    'lambda_fuselage': '-',

    'x_fuselage': 'м',

    # Выходные параметры геометрии
    'l_wing': 'м',
    'b0_wing': 'м',
    'bk_wing': 'м',
    'sweep_wing_LE': 'град',

    'S_ht': 'м²',
    'l_ht': 'м',
    'b0_ht': 'м',
    'bk_ht': 'м',
    'sweep_ht_LE': 'град',
    'x_ht': 'м',
    'y_ht': 'м',

    'S_vt': 'м²',
    'l_vt': 'м',
    'b0_vt': 'м',
    'bk_vt': 'м',
    'sweep_vt_LE': 'град',
    'x_vt': 'м',

    'L_fuselage': 'м',
    'd_fuselage': 'м',
    'r_fuselage': 'м',
    'y_wing': 'м',
}

# Поля для INPUT таблицы (то, что вводит пользователь)
INPUT_FIELDS = [
    # Общие и аэродинамические характеристики самолета
    'N',
    'Lambda',
    'e',
    'C_x0',
    'n_max',

    # Характеристики крыла и взлетно-посадочные параметры
    'C_y_max',
    'C_y_max_TO',
    'V_s',
    'L_TODA',
    'sigma',

    # Характеристики высотного / крейсерского полета
    'V_cruise',
    'theta',
    'V_y',

    # Физические условия (плотность воздуха)
    'pho_V_s',
    'pho_V_cruise',
    'pho_V_y',

    # Целевые параметры
    'payload_mass',
    'design_range',

    # Характеристики масс
    'fuel_reserve_factor',
    'cruise_sfc',
    'cruise_L_D_ratio',

    # Параметры крыла
    'eta_wing',
    'sweep_wing_quarter',
    'wing_scheme',

    # Параметры ГО
    'k_horizontal_tail',
    'lambda_horizontal_tail',
    'eta_horizontal_tail',
    'sweep_horizontal_tail_quarter',

    # Параметры ВО
    'k_vertical_tail',
    'lambda_vertical_tail',
    'eta_vertical_tail',
    'sweep_vertical_tail_quarter',

    # Параметры фюзеляжа
    'k_fuselage',
    'lambda_fuselage',
]

# Поля для OUTPUT таблицы (то, что выводит приложение)
OUTPUT_FIELDS = [
    'p0_optimal',
    'P0_optimal',

    'm_MTO',
    'm_OE',
    'm_F',
    'm_ML',
    'T_TO',
    'S_W',

    # Крыло
    'l_wing',
    'b0_wing',
    'bk_wing',
    'sweep_wing_LE',
    'y_wing',

    # ГО
    'S_ht',
    'l_ht',
    'b0_ht',
    'bk_ht',
    'sweep_ht_LE',
    'x_ht',
    'y_ht',

    # ВО
    'S_vt',
    'l_vt',
    'b0_vt',
    'bk_vt',
    'sweep_vt_LE',
    'x_vt',

    # Фюзеляж
    'L_fuselage',
    'd_fuselage',
    'r_fuselage',
]

# Группировка полей по категориям (для красивого отображения)
FIELD_CATEGORIES = {
    'Общие и аэродинамические характеристики самолета': [
        'N', 'Lambda', 'e', 'C_x0', 'n_max',
    ],
    'Характеристики крыла и взлетно-посадочные параметры': [
        'C_y_max', 'C_y_max_TO', 'V_s', 'L_TODA', 'sigma',
    ],
    'Характеристики высотного / крейсерского полета': [
        'V_cruise', 'theta', 'V_y',
    ],
    'Физические условия': [
        'pho_V_s', 'pho_V_cruise', 'pho_V_y',
    ],
    'Целевые параметры': [
        'payload_mass', 'design_range',
    ],
    'Для расчёта масс': [
        'fuel_reserve_factor', 'cruise_sfc', 'cruise_L_D_ratio',
    ],

    'Оптимальная точка': [
        'p0_optimal', 'P0_optimal',
    ],

    'Характеристики масс': [
        'm_MTO', 'm_OE', 'm_F', 'm_ML', 'T_TO',
    ],

    'Геометрические параметры (расчётные)': [
        'S_W', 'l_wing', 'b0_wing', 'bk_wing', 'sweep_wing_LE', 'y_wing', 'S_ht', 'l_ht',
        'b0_ht', 'bk_ht', 'sweep_ht_LE', 'x_ht', 'y_ht', 'S_vt', 'l_vt', 'b0_vt',
        'bk_vt', 'sweep_vt_LE', 'x_vt', 'L_fuselage', 'd_fuselage', 'r_fuselage',
    ],

    'Геометрические параметры (входные)': [
        'eta_wing', 'sweep_wing_quarter', 'wing_scheme', 'k_horizontal_tail',
        'lambda_horizontal_tail', 'eta_horizontal_tail', 'sweep_horizontal_tail_quarter',
        'k_vertical_tail', 'lambda_vertical_tail', 'eta_vertical_tail',
        'sweep_vertical_tail_quarter', 'k_fuselage', 'lambda_fuselage',
    ],


}