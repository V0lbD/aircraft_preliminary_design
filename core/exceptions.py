"""
Кастомные исключения для системы расчёта самолёта
"""


class AircraftDesignError(Exception):
    """Базовое исключение для ошибок проектирования самолёта"""
    pass


class ValidationError(AircraftDesignError):
    """Исключение для ошибок валидации входных данных"""

    def __init__(self, message: str, field_name: str = None, value=None):
        super().__init__(message)
        self.field_name = field_name
        self.value = value


class CalculationError(AircraftDesignError):
    """Исключение для ошибок в процессе вычислений"""

    def __init__(self, message: str, block_name: str = None, details: dict = None):
        super().__init__(message)
        self.block_name = block_name
        self.details = details or {}


class DataImportError(AircraftDesignError):
    """Исключение для ошибок импорта данных"""
    pass


class DatabaseError(AircraftDesignError):
    """Исключение для ошибок работы с базой данных"""
    pass


class ConfigurationError(AircraftDesignError):
    """Исключение для ошибок конфигурации"""
    pass