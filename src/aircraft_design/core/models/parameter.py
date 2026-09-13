from __future__ import annotations

from typing import Any, Callable, Iterable


class Parameter:
    """
    Дескриптор для входных и выходных параметров проекта.
    Обеспечивает валидацию, хранение метаданных и привязку к UI без тяжелых фреймворков.
    """

    def __init__(
            self,
            display_name: str,
            description: str = "",
            unit: str = "",
            category: str = "Общие",
            default: Any = None,
            choices: Iterable[Any] | None = None,
            rules: list[Callable[[Any], str | None]] | None = None,
            is_input: bool = True,
    ):
        self.display_name = display_name
        self.description = description
        self.unit = unit
        self.category = category
        self.default = default
        self.choices = set(choices) if choices else None
        self.rules = rules or []
        self.is_input = is_input

        # Внутреннее имя будет задано автоматически через __set_name__
        self.name = ""
        self._private_name = ""

    def __set_name__(self, owner, name: str):
        """Автоматически вызывается при создании класса, где объявлен Parameter."""
        self.name = name
        self._private_name = f"_{name}"

    def __get__(self, instance, owner):
        # Если обращаемся к классу (например, FeasibilityData.max_speed), отдаем сам дескриптор
        if instance is None:
            return self
        # Если обращаемся к объекту, отдаем значение
        return getattr(instance, self._private_name, self.default)

    def __set__(self, instance, value: Any):
        # 1. Проверка на Enum (выпадающие списки)
        if self.choices and value not in self.choices:
            raise ValueError(
                f"Значение '{value}' для параметра '{self.display_name}' "
                f"не входит в список допустимых: {self.choices}"
            )

        # 2. Проверка правил (rules)
        for rule in self.rules:
            warning_msg = rule(value)
            if warning_msg:
                # Пытаемся записать warning в общий лог проекта
                project = getattr(instance, "_project", None)
                full_msg = f"[{self.display_name}]: {warning_msg}"

                if project is not None:
                    block_context = f" (Блок: {project.current_block})" if project.current_block else ""
                    project.add_warning(full_msg + block_context)
                else:
                    import logging
                    logging.warning(full_msg)

        # 3. Сохраняем значение
        setattr(instance, self._private_name, value)


# --- Набор удобных функций-правил для валидации ---
def rule_min(min_val: float) -> Callable[[Any], str | None]:
    return lambda v: f"Значение {v} меньше допустимого минимума ({min_val})" if v < min_val else None


def rule_max(max_val: float) -> Callable[[Any], str | None]:
    return lambda v: f"Значение {v} превышает максимум ({max_val})" if v > max_val else None


def rule_positive(v: Any) -> str | None:
    return "Значение должно быть больше нуля" if v <= 0 else None