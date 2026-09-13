from __future__ import annotations

import logging

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.models.project import ProjectState

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Управляет последовательным выполнением расчётных блоков.
    В новой архитектуре работает напрямую с объектом ProjectState.
    """

    def __init__(
        self,
        blocks: list[BaseBlock] | None = None,
        stop_on_error: bool = True,
    ) -> None:
        self.blocks = blocks or []
        self.stop_on_error = stop_on_error

    def run(self, project: ProjectState) -> bool:
        logger.info("Начало расчёта проекта")

        if not self.blocks:
            msg = "Нет настроенных блоков для расчёта."
            project.add_warning(msg)
            logger.warning(msg)
            return False

        # Конвейерный прогон через все блоки
        for block in self.blocks:
            # Напомним: block.run() теперь сам ловит исключения и пишет их в project
            success = block.run(project)

            if not success:
                if self.stop_on_error:
                    logger.error(f"Расчёт остановлен из-за ошибки в блоке: {block.name}")
                    break

        # Если в массиве ошибок проекта пусто, значит всё прошло гладко
        is_success = len(project.errors) == 0

        # Оставляем удобный вывод трассировки в дебаг-лог, как в старой версии
        if logger.isEnabledFor(logging.DEBUG):
            self._log_trace_records(project.trace_records)

        logger.info(f"Расчёт завершён. Успех: {is_success}")
        return is_success

    @staticmethod
    def _log_trace_records(records: list[dict]) -> None:
        if not records:
            logger.debug("Calculation trace is empty")
            return

        logger.debug(f"Calculation trace records: {len(records)}")

        for record in records:
            logger.debug(
                "TRACE | %s | %s = %s | formula: %s",
                record.get("block"),
                record.get("value_name"),
                record.get("result"),
                record.get("formula"),
            )