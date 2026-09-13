from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseBlock(ABC):
    """
    Базовый класс для всех расчётных блоков.

    Блок напрямую взаимодействует с единым объектом ProjectState,
    читая из него входные параметры и записывая выходные.
    """
    name: str = "base_block"
    display_name: str = "Базовый блок"

    def run(self, project: 'ProjectState') -> bool:
        """
        Запускает блок, устанавливает контекст и перехватывает критические ошибки.
        Возвращает True, если расчет успешен, и False при критической ошибке.
        """
        logger.info(f"Запуск блока: {self.name}")

        # Устанавливаем контекст, чтобы сеттеры параметров знали,
        # кто именно сейчас меняет их значения или вызывает предупреждения.
        project.current_block = self.name

        try:
            self.calculate(project)
            logger.info(f"Блок завершен: {self.name}")
            return True

        except Exception as exc:
            # Сюда прилетят критические ошибки из сеттеров или математики (например, деление на ноль)
            logger.error(f"Критическая ошибка в блоке {self.name}: {exc}")

            # Записываем ошибку в общее состояние проекта
            project.add_error(f"[{self.name}] {exc}")
            return False

        finally:
            # Очищаем контекст после завершения
            project.current_block = None

    @abstractmethod
    def calculate(self, project: 'ProjectState') -> None:
        """
        Основная логика расчёта.
        Метод ничего не возвращает. Все вычисления напрямую изменяют параметры в project.
        """
        pass