from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError

logger = logging.getLogger(__name__)


class FeasibilityError(Exception):
    """Исключение, выбрасываемое при нереализуемости ТТТ проекта."""
    pass


def get_resource_path(relative_path: str) -> Path:
    """Возвращает абсолютный путь к ресурсу."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Если запущено как скомпилированный .exe, ищем папку РЯДОМ с .exe
        base_path = Path(sys.executable).parent
    else:
        # Если запущено из IDE
        base_path = Path.cwd()
    return base_path / relative_path


class FeasibilityBlock(BaseBlock):
    """
    Блок оценки реализуемости БЛА.
    Сравнивает ТТТ проектируемого БЛА со статистикой существующих аналогов.
    """
    name = "feasibility_check"
    display_name = "Оценка реализуемости"

    # Индексы столбцов (относительно начала блока группы масс)
    COL_NAME = 1
    COL_RANGE = 4
    COL_DURATION = 5
    COL_SPEED = 6
    COL_CEILING = 7
    COL_PAYLOAD = 14

    def calculate(self, project: 'ProjectState') -> None:
        """
        Основная логика расчёта. Читает данные из project, считает и пишет обратно.
        """
        # 1. Для лаконичности создаем локальную ссылку на данные блока
        feas = project.feasibility

        # 2. Динамическое построение путей к таблицам
        stats_file_path = get_resource_path("inputs/tables/Статистика БЛА.xlsx")
        weights_file_path = get_resource_path("inputs/tables/Весовые коэффициенты.xlsx")

        # 3. Определение группы и подгруппы
        row_start, row_end = self._get_row_bounds(feas.powerplant_type)
        col_offset = self._get_col_offset(feas.target_takeoff_mass)

        # 4. Загрузка данных
        try:
            df_stats = pd.read_excel(stats_file_path, header=None)
            df_weights = pd.read_excel(weights_file_path)
        except FileNotFoundError as e:
            raise InputValidationError(f"Отсутствует файл статистики или весов: {e}")

        try:
            weights = df_weights.iloc[0:5, 1].astype(float).values
        except Exception:
            weights = [0.2, 0.2, 0.2, 0.2, 0.2]

        w_range, w_duration, w_speed, w_ceiling, w_payload = weights

        # 5. Извлечение аналогов
        analogs = []
        for i in range(row_start, row_end + 1):
            if i >= len(df_stats):
                break

            num_val = df_stats.iloc[i, col_offset]
            name_val = df_stats.iloc[i, col_offset + self.COL_NAME]

            if pd.isna(name_val) or str(name_val).strip() == "":
                continue

            def safe_float(val):
                try:
                    return float(val) if not pd.isna(val) else 0.0
                except (ValueError, TypeError):
                    return 0.0

            analog = {
                "name": str(name_val),
                "range": safe_float(df_stats.iloc[i, col_offset + self.COL_RANGE]),
                "duration": safe_float(df_stats.iloc[i, col_offset + self.COL_DURATION]),
                "speed": safe_float(df_stats.iloc[i, col_offset + self.COL_SPEED]),
                "ceiling": safe_float(df_stats.iloc[i, col_offset + self.COL_CEILING]),
                "payload": safe_float(df_stats.iloc[i, col_offset + self.COL_PAYLOAD]),
            }
            if any(v > 0 for k, v in analog.items() if k != "name"):
                analogs.append(analog)

        if not analogs:
            raise InputValidationError("Не найдено аналогов в базе для выбранной категории массы и типа СУ.")

        # 6. Поиск максимальных значений
        max_range = max(a["range"] for a in analogs) or 1.0
        max_duration = max(a["duration"] for a in analogs) or 1.0
        max_speed = max(a["speed"] for a in analogs) or 1.0
        max_ceiling = max(a["ceiling"] for a in analogs) or 1.0
        max_payload = max(a["payload"] for a in analogs) or 1.0

        # 7. Расчет показателя для аналогов
        max_stat_score = 0.0
        best_analog_name = ""

        for a in analogs:
            a["norm_range"] = a["range"] / max_range
            a["norm_duration"] = a["duration"] / max_duration
            a["norm_speed"] = a["speed"] / max_speed
            a["norm_ceiling"] = a["ceiling"] / max_ceiling
            a["norm_payload"] = a["payload"] / max_payload

            a["score"] = (
                    a["norm_range"] * w_range +
                    a["norm_duration"] * w_duration +
                    a["norm_speed"] * w_speed +
                    a["norm_ceiling"] * w_ceiling +
                    a["norm_payload"] * w_payload
            )

            if a["score"] > max_stat_score:
                max_stat_score = a["score"]
                best_analog_name = a["name"]

        # 8. Расчет показателя проекта
        norm_proj_range = feas.design_range / max_range
        norm_proj_duration = feas.flight_duration_h / max_duration
        norm_proj_speed = feas.max_speed / max_speed
        norm_proj_ceiling = feas.practical_ceiling_m / max_ceiling
        norm_proj_payload = feas.payload_mass / max_payload

        project_score = (
                norm_proj_range * w_range +
                norm_proj_duration * w_duration +
                norm_proj_speed * w_speed +
                norm_proj_ceiling * w_ceiling +
                norm_proj_payload * w_payload
        )

        is_feasible = project_score <= (max_stat_score * 1.10)

        # 9. Запись трассировки (Trace для Markdown)
        project.add_trace(
            value_name="I_max_stat",
            formula=r"I_{k_{max}} = \max_{1 \le i \le N_k} \sum_{j=1}^m w_j \cdot X_{kij}'",
            values={"best_analog": best_analog_name},
            result=float(max_stat_score),
            description="Максимальный комплексный показатель среди аналогов в группе.",
        )

        project.add_trace(
            value_name="I_project",
            formula=r"I_{proj} = \sum_{j=1}^m w_j \cdot \frac{x_{proj, j}}{M_{kj}}",
            values={
                "range": feas.design_range,
                "duration": feas.flight_duration_h,
                "speed": feas.max_speed,
                "ceiling": feas.practical_ceiling_m,
                "payload": feas.payload_mass
            },
            result=float(project_score),
            description="Комплексный показатель проектируемого БЛА.",
        )

        # 10. Запись результатов в проект
        # Сохраняем итоговые переменные обратно в дескрипторы проекта
        feas.project_score = float(project_score)
        feas.max_stat_score = float(max_stat_score)
        feas.best_analog_name = best_analog_name
        feas.is_feasible = is_feasible

        # Сохраняем таблицу аналогов в словарик databases проекта для UI
        project.databases["feasibility_analogs"] = analogs

        # 11. Прерывание при нереализуемости
        if not is_feasible:
            # Бросаем ошибку. Базовый класс BaseBlock перехватит её,
            # запишет в лог и остановит дальнейшие блоки.
            raise FeasibilityError(
                f"ТТТ нереализуемы. Комплексный показатель проекта ({project_score:.3f}) "
                f"превышает аналог '{best_analog_name}' ({max_stat_score:.3f}) более чем на 10%."
            )

    @staticmethod
    def _get_row_bounds(powerplant_type: str) -> tuple[int, int]:
        if powerplant_type == "electric": return 5, 27
        if powerplant_type == "ice": return 33, 82
        if powerplant_type == "hybrid": return 88, 150
        raise InputValidationError(f"Неизвестный тип СУ: {powerplant_type}")

    @staticmethod
    def _get_col_offset(mass: float) -> int:
        if mass <= 30.0: return 0
        if 30.0 < mass <= 100.0: return 17
        return 34