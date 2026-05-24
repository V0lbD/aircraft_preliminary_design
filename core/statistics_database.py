from typing import Dict, Tuple
from core.data_models import WingFlapsTypeEnum, AircraftTypeEnum, EngineTypeEnum


class StatisticsDatabase:
    """
    База данных статистических данных из методики.
    Содержит данные из таблиц 5.1, 5.2 и рисунка 5.3
    """

    # Коэффициенты безопасности для разных типов двигателей (стр. 5-4)
    SAFETY_FACTORS = {
        EngineTypeEnum.TURBOJET: 1.667,      # 1/0.6 для реактивных
        EngineTypeEnum.TURBOPROP: 1.429      # 1/0.7 для турбовинтовых
    }

    # Максимальные коэффициенты подъёмной силы для посадки (Таблица 5.1)
    # Формат: (min_value, max_value)
    C_L_MAX_LANDING = {
        AircraftTypeEnum.BUSINESS_JET: (1.6, 2.2),
        AircraftTypeEnum.SHORT_RANGE_JET_TRANSPORT: (1.6, 2.2),
        AircraftTypeEnum.MEDIUM_RANGE_JET_TRANSPORT: (1.6, 2.2),
        AircraftTypeEnum.LONG_RANGE_JET_TRANSPORT: (1.6, 2.2),
        AircraftTypeEnum.ULTRA_LONG_RANGE_JET_TRANSPORT: (1.6, 2.2),
        AircraftTypeEnum.FIGHTER: (1.4, 2.0),
        AircraftTypeEnum.SUPERSONIC_CRUISE: (1.6, 2.0)
    }

    # Максимальные коэффициенты подъёмной силы для взлёта (Таблица 5.1)
    C_L_MAX_TAKEOFF = {
        AircraftTypeEnum.BUSINESS_JET: (1.4, 1.8),
        AircraftTypeEnum.SHORT_RANGE_JET_TRANSPORT: (1.2, 1.8),
        AircraftTypeEnum.MEDIUM_RANGE_JET_TRANSPORT: (1.2, 1.8),
        AircraftTypeEnum.LONG_RANGE_JET_TRANSPORT: (1.2, 1.8),
        AircraftTypeEnum.ULTRA_LONG_RANGE_JET_TRANSPORT: (1.2, 1.8),
        AircraftTypeEnum.FIGHTER: (1.2, 1.8),
        AircraftTypeEnum.SUPERSONIC_CRUISE: (1.2, 2.8)
    }

    # Отношения масс m_ML/m_MTO (Таблица 5.2) - средние значения
    MASS_RATIOS = {
        AircraftTypeEnum.BUSINESS_JET: 0.88,
        AircraftTypeEnum.SHORT_RANGE_JET_TRANSPORT: 0.93,
        AircraftTypeEnum.MEDIUM_RANGE_JET_TRANSPORT: 0.88,
        AircraftTypeEnum.LONG_RANGE_JET_TRANSPORT: 0.78,
        AircraftTypeEnum.ULTRA_LONG_RANGE_JET_TRANSPORT: 0.71,
        AircraftTypeEnum.FIGHTER: 0.57,  # Примерное значение
        AircraftTypeEnum.SUPERSONIC_CRUISE: 0.75
    }

    # Коэффициенты подъёмной силы для разных типов механизации (из рис. 5.3)
    # Приблизительные значения для посадочной конфигурации
    FLAPS_C_L_MAX = {
        WingFlapsTypeEnum.CLEAN_AIRFOIL: 1.45,
        WingFlapsTypeEnum.PLAIN_FLAP: 1.8,
        WingFlapsTypeEnum.SPLIT_FLAP: 1.9,
        WingFlapsTypeEnum.SLOTTED_FLAP: 2.2,
        WingFlapsTypeEnum.FOWLER_FLAP: 2.4,
        WingFlapsTypeEnum.DOUBLE_SLOTTED_FLAP: 2.6,
        WingFlapsTypeEnum.TRIPLE_SLOTTED_FLAP: 2.8
    }

    @classmethod
    def get_C_L_max_landing(cls, aircraft_type: AircraftTypeEnum,
                            flaps_type: WingFlapsTypeEnum = None) -> float:
        """
        Получить максимальный коэффициент подъёмной силы для посадки
        Учитывает как тип самолёта, так и тип механизации
        """
        # Базовое значение по типу самолёта (среднее)
        base_range = cls.C_L_MAX_LANDING.get(aircraft_type, (1.6, 2.2))
        base_value = (base_range[0] + base_range[1]) / 2

        # Корректировка по типу механизации
        if flaps_type:
            flaps_value = cls.FLAPS_C_L_MAX.get(flaps_type, base_value)
            # Используем среднее значение между статистикой самолёта и механизации
            return (base_value + flaps_value) / 2

        return base_value

    @classmethod
    def get_C_L_max_takeoff(cls, aircraft_type: AircraftTypeEnum) -> float:
        """Получить максимальный коэффициент подъёмной силы для взлёта"""
        base_range = cls.C_L_MAX_TAKEOFF.get(aircraft_type, (1.4, 1.8))
        return (base_range[0] + base_range[1]) / 2

    @classmethod
    def get_mass_ratio(cls, aircraft_type: AircraftTypeEnum) -> float:
        """Получить отношение m_ML/m_MTO"""
        return cls.MASS_RATIOS.get(aircraft_type, 0.88)  # По умолчанию как для бизнес-джета