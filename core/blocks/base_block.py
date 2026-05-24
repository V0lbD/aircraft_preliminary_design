from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from core.data_models import ProjectData
from core.exceptions import ValidationError, CalculationError


class BaseBlock(ABC):
    """
    Абстрактный базовый класс для всех вычислительных блоков.
    Определяет общий интерфейс и базовую функциональность.
    """

    def __init__(self):
        self._validation_rules: Dict[str, Any] = {}
        self._setup_validation_rules()

    @property
    @abstractmethod
    def name(self) -> str:
        """Возвращает человекочитаемое название блока"""
        pass

    @property
    @abstractmethod
    def block_number(self) -> int:
        """Возвращает номер блока в методике"""
        pass

    @property
    def description(self) -> str:
        """Возвращает описание блока"""
        return f"Блок {self.block_number}: {self.name}"

    @property
    def required_inputs(self) -> List[str]:
        """Возвращает список обязательных входных параметров"""
        return []

    @property
    def optional_inputs(self) -> List[str]:
        """Возвращает список необязательных входных параметров"""
        return []

    @property
    def outputs(self) -> List[str]:
        """Возвращает список выходных параметров"""
        return []

    @abstractmethod
    def calculate(self, data: ProjectData) -> None:
        """
        Выполняет основной расчёт блока.

        Args:
            data: Данные проекта для расчёта

        Raises:
            CalculationError: При ошибке расчёта
            ValidationError: При ошибке валидации входных данных
        """
        pass

    def validate(self, data: ProjectData) -> List[str]:
        """
        Валидирует входные данные для блока.

        Args:
            data: Данные для валидации

        Returns:
            Список ошибок валидации (пустой если всё корректно)
        """
        errors = []

        # Проверяем обязательные поля
        # todo: переделать проверку
        for field_name in self.required_inputs:
            if not self._check_field_exists(data, field_name):
                errors.append(f"Отсутствует обязательное поле: {field_name}")

        # Проверяем правила валидации
        for field_name, rules in self._validation_rules.items():
            field_errors = self._validate_field(data, field_name, rules)
            errors.extend(field_errors)

        return errors

    def get_default_value(self, parameter_name: str) -> Optional[float]:
        """
        Возвращает значение по умолчанию для параметра.

        Args:
            parameter_name: Название параметра

        Returns:
            Значение по умолчанию или None
        """
        defaults = self._get_default_values()
        return defaults.get(parameter_name)

    def can_execute(self, data: ProjectData) -> bool:
        """
        Проверяет, можно ли выполнить расчёт блока.

        Args:
            data: Данные проекта

        Returns:
            True если расчёт возможен, False иначе
        """
        errors = self.validate(data)
        return len(errors) == 0

    def get_calculation_summary(self, data: ProjectData) -> Dict[str, Any]:
        """
        Возвращает сводку по результатам расчёта.

        Args:
            data: Данные проекта после расчёта

        Returns:
            Словарь с основными результатами
        """
        return {
            'block_name': self.name,
            'block_number': self.block_number,
            'executed': True,
            'outputs': {param: self._get_field_value(data, param) for param in self.outputs}
        }

    def reset_outputs(self, data: ProjectData) -> None:
        """
        Сбрасывает выходные параметры блока.

        Args:
            data: Данные проекта
        """
        for output_param in self.outputs:
            self._set_field_value(data, output_param, None)

    def _setup_validation_rules(self) -> None:
        """
        Настраивает правила валидации для блока.
        Переопределяется в дочерних классах.
        """
        pass

    def _get_default_values(self, data: ProjectData) -> Dict[str, float]:
        """
        Возвращает словарь значений по умолчанию.
        Переопределяется в дочерних классах.
        """
        return {}

    def _check_field_exists(self, data: ProjectData, field_name: str) -> bool:
        """Проверяет существование поля в данных"""
        try:
            value = self._get_field_value(data, field_name)
            return value is not None
        except (AttributeError, KeyError):
            return False

    def _get_field_value(self, data: ProjectData, field_name: str) -> Any:
        """Получает значение поля из данных"""
        parts = field_name.split('.')
        obj = data

        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                raise AttributeError(f"Field {field_name} not found")

        return obj

    def _set_field_value(self, data: ProjectData, field_name: str, value: Any) -> None:
        """Устанавливает значение поля в данных"""
        parts = field_name.split('.')
        obj = data

        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                raise AttributeError(f"Field {field_name} not found")

        setattr(obj, parts[-1], value)

    def _validate_field(self, data: ProjectData, field_name: str, rules: Dict[str, Any]) -> List[str]:
        """Валидирует конкретное поле по правилам"""
        errors = []

        try:
            value = self._get_field_value(data, field_name)
        except AttributeError:
            if rules.get('required', False):
                errors.append(f"Отсутствует поле: {field_name}")
            return errors

        if value is None:
            if rules.get('required', False):
                errors.append(f"Поле {field_name} не может быть пустым")
            return errors

        # Проверка типа
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"Поле {field_name} должно быть типа {expected_type.__name__}")

        # Проверка диапазона для числовых значений
        if isinstance(value, (int, float)):
            min_val = rules.get('min')
            max_val = rules.get('max')

            if min_val is not None and value < min_val:
                errors.append(f"Значение {field_name} должно быть >= {min_val}")

            if max_val is not None and value > max_val:
                errors.append(f"Значение {field_name} должно быть <= {max_val}")

        return errors

    def __str__(self) -> str:
        return f"{self.description}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"