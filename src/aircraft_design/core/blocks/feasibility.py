from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import BlockInputSchema, CalculationState, ParameterSpec
def get_resource_path(relative_path: str) -> Path:
    """
    Возвращает абсолютный путь к ресурсу.
    Работает как для обычного запуска из кода, так и для скомпилированного .exe.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Если запущено как скомпилированный .exe, ищем во временной папке PyInstaller
        base_path = Path(sys._MEIPASS)
    else:
        # Если запущено как обычный скрипт, ищем относительно корня проекта (или текущей директории)
        base_path = Path.cwd()

    return base_path / relative_path
logger = logging.getLogger(__name__)


class FeasibilityError(Exception):
    """Исключение, выбрасываемое при нереализуемости ТТТ проекта."""
    pass


# --- СТРОГАЯ МОДЕЛЬ ВХОДНЫХ ДАННЫХ ---
class FeasibilityInput(BaseModel):
    powerplant_type: str = Field(..., description="Тип силовой установки: electric, ice, hybrid")
    target_takeoff_mass: float = Field(..., gt=0, description="Ожидаемая взлётная масса (кг)")
    design_range: float = Field(..., gt=0, description="Практическая дальность (км)")
    flight_duration_h: float = Field(..., gt=0, description="Длительность полёта (час)")
    max_speed: float = Field(..., gt=0, description="Максимальная скорость (км/ч)")
    practical_ceiling_m: float = Field(..., gt=0, description="Практический потолок (м)")
    payload_mass: float = Field(..., ge=0, description="Полезная нагрузка (кг)")

    model_config = {"extra": "ignore"}


class FeasibilityBlock(BaseBlock):
    """
    Блок оценки реализуемости БЛА.
    Сравнивает ТТТ проектируемого БЛА со статистикой существующих аналогов.
    """

    name = "feasibility_check"
    required_input_sections = ("feasibility",)

    input_schema = BlockInputSchema(
        section_name="feasibility",
        block_name="feasibility_check",
        display_name="Оценка реализуемости",
        description="Проверка ТТТ проекта на соответствие статистике аналогов.",
        parameters=(
            ParameterSpec(
                name="powerplant_type",
                value_type="string",
                display_name="Тип силовой установки",
                description="Электрический, топливный или гибридный.",
                required=True,
                default="ice",
                choices=("electric", "ice", "hybrid"),
                group="general",
            ),
            ParameterSpec(
                name="target_takeoff_mass",
                value_type="number",
                display_name="Целевая взлётная масса",
                description="Ожидаемая взлётная масса для выбора группы аналогов.",
                unit="kg",
                required=True,
                default=3600.0,
                min_value=0.0,
                group="general",
            ),
            ParameterSpec(
                name="design_range",
                value_type="number",
                display_name="Практическая дальность",
                description="Требуемая дальность полёта.",
                unit="km",
                required=True,
                default=650.0,
                min_value=0.0,
                group="mission",
            ),
            ParameterSpec(
                name="flight_duration_h",
                value_type="number",
                display_name="Длительность полёта",
                description="Требуемое время нахождения в воздухе.",
                unit="h",
                required=True,
                default=4.0,
                min_value=0.0,
                group="mission",
            ),
            ParameterSpec(
                name="max_speed",
                value_type="number",
                display_name="Максимальная скорость",
                description="Максимальная скорость горизонтального полёта.",
                unit="km/h",
                required=True,
                default=210.0,
                min_value=0.0,
                group="performance",
            ),
            ParameterSpec(
                name="practical_ceiling_m",
                value_type="number",
                display_name="Практический потолок",
                description="Максимальная высота полёта.",
                unit="m",
                required=True,
                default=5000.0,
                min_value=0.0,
                group="performance",
            ),
            ParameterSpec(
                name="payload_mass",
                value_type="number",
                display_name="Полезная нагрузка",
                description="Масса целевой нагрузки.",
                unit="kg",
                required=True,
                default=520.0,
                min_value=0.0,
                group="general",
            ),
        ),
    )

    # Укажите правильные пути до ваших файлов в проекте
    # STATS_FILE_PATH = Path("Статистика БЛА.xlsx")
    # WEIGHTS_FILE_PATH = Path("Весовые коэффициенты.xlsx")

    # Индексы столбцов (относительно начала блока группы масс)
    COL_NAME = 1
    COL_RANGE = 4
    COL_DURATION = 5
    COL_SPEED = 6
    COL_CEILING = 7
    COL_PAYLOAD = 14

    def validate(self, state: CalculationState) -> None:
        super().validate(state)
        section_data = state.project_input.feasibility
        raw_data = section_data if isinstance(section_data, dict) else section_data.model_dump()

        try:
            FeasibilityInput.model_validate(raw_data)
        except Exception as e:
            raise InputValidationError(f"Ошибка валидации входных данных реализуемости: {e}")

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        section_data = state.project_input.feasibility
        raw_data = section_data if isinstance(section_data, dict) else section_data.model_dump()
        inputs = FeasibilityInput.model_validate(raw_data)

        # Динамическое построение путей к папке inputs/tables
        stats_file_path = get_resource_path("inputs/tables/Статистика БЛА.xlsx")
        weights_file_path = get_resource_path("inputs/tables/Весовые коэффициенты.xlsx")

        row_start, row_end = self._get_row_bounds(inputs.powerplant_type)
        col_offset = self._get_col_offset(inputs.target_takeoff_mass)

        # 2. Загрузка данных
        try:
            df_stats = pd.read_excel(stats_file_path, header=None)
            df_weights = pd.read_excel(weights_file_path)
        except FileNotFoundError as e:
            raise InputValidationError(f"Отсутствует файл статистики или весов: {e}")

        # Считываем веса
        try:
            # Предполагается, что веса идут сверху вниз по 5 параметрам
            weights = df_weights.iloc[0:5, 1].astype(float).values
        except Exception:
            # Фолбэк, если структура файла весов немного отличается
            weights = [0.2, 0.2, 0.2, 0.2, 0.2]

        w_range, w_duration, w_speed, w_ceiling, w_payload = weights

        # 3. Извлечение аналогов
        analogs = []
        for i in range(row_start, row_end + 1):
            if i >= len(df_stats):
                break

            # Проверяем, есть ли номер или имя
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
            # Фильтруем пустые/невалидные строки
            if any(v > 0 for k, v in analog.items() if k != "name"):
                analogs.append(analog)

        if not analogs:
            raise InputValidationError("Не найдено аналогов в базе для выбранной категории массы и типа СУ.")

        # 4. Поиск максимальных значений (M_kj)
        max_range = max(a["range"] for a in analogs) or 1.0
        max_duration = max(a["duration"] for a in analogs) or 1.0
        max_speed = max(a["speed"] for a in analogs) or 1.0
        max_ceiling = max(a["ceiling"] for a in analogs) or 1.0
        max_payload = max(a["payload"] for a in analogs) or 1.0

        # 5. Расчет показателя I_ki для аналогов
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

        # 6. Расчет показателя I_проект
        norm_proj_range = inputs.design_range / max_range
        norm_proj_duration = inputs.flight_duration_h / max_duration
        norm_proj_speed = inputs.max_speed / max_speed
        norm_proj_ceiling = inputs.practical_ceiling_m / max_ceiling
        norm_proj_payload = inputs.payload_mass / max_payload

        project_score = (
                norm_proj_range * w_range +
                norm_proj_duration * w_duration +
                norm_proj_speed * w_speed +
                norm_proj_ceiling * w_ceiling +
                norm_proj_payload * w_payload
        )

        # 7. Запись данных в следы (Trace) для отладчика / отчетов
        state.add_trace(
            block_name=self.name,
            value_name="I_max_stat",
            formula=r"I_{k_{max}} = \max_{1 \le i \le N_k} \sum_{j=1}^m w_j \cdot X_{kij}'",
            values={"best_analog": best_analog_name},
            result=float(max_stat_score),
            description="Максимальный комплексный показатель среди аналогов в группе.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="I_project",
            formula=r"I_{proj} = \sum_{j=1}^m w_j \cdot \frac{x_{proj, j}}{M_{kj}}",
            values={
                "range": inputs.design_range,
                "duration": inputs.flight_duration_h,
                "speed": inputs.max_speed,
                "ceiling": inputs.practical_ceiling_m,
                "payload": inputs.payload_mass
            },
            result=float(project_score),
            description="Комплексный показатель проектируемого БЛА.",
        )

        # 8. Проверка реализуемости (Превышение более чем на 10%)
        is_feasible = project_score <= (max_stat_score * 1.10)

        result_data = {
            "max_values": {
                "range": max_range,
                "duration": max_duration,
                "speed": max_speed,
                "ceiling": max_ceiling,
                "payload": max_payload,
            },
            "project_normalized": {
                "range": norm_proj_range,
                "duration": norm_proj_duration,
                "speed": norm_proj_speed,
                "ceiling": norm_proj_ceiling,
                "payload": norm_proj_payload,
            },
            "project_score": float(project_score),
            "max_stat_score": float(max_stat_score),
            "best_analog_name": best_analog_name,
            "is_feasible": is_feasible,
            "chart_data": {
                "analogs_table": analogs,  # Готовый массив словарей для QTableWidget
            }
        }

        # Если нереализуемо - прерываем дальнейший расчет
        if not is_feasible:
            logger.warning(
                f"Проект нереализуем! I_проект ({project_score:.3f}) > "
                f"I_стат ({max_stat_score:.3f}) более чем на 10%."
            )
            # В зависимости от архитектуры, можно либо выбросить исключение:
            raise FeasibilityError(
                f"Заданные ТТТ нереализуемы. Комплексный показатель проекта ({project_score:.3f}) "
                f"превышает лучший аналог '{best_analog_name}' ({max_stat_score:.3f}) более чем на 10%."
            )
            # Либо просто вернуть результат, а UI сам решит останавливать ли (раскомментируй return)
            # return result_data

        return result_data

    @staticmethod
    def _get_row_bounds(powerplant_type: str) -> tuple[int, int]:
        """Возвращает примерные диапазоны строк в Excel для типов СУ."""
        if powerplant_type == "electric":
            return 5, 27
        elif powerplant_type == "ice":
            return 33, 82
        elif powerplant_type == "hybrid":
            return 88, 150
        else:
            raise InputValidationError(f"Неизвестный тип СУ: {powerplant_type}")

    @staticmethod
    def _get_col_offset(mass: float) -> int:
        """Возвращает смещение столбцов в зависимости от массы (кг)."""
        if mass <= 30.0:
            return 0
        elif 30.0 < mass <= 100.0:
            return 17
        else:  # > 100.0
            return 34