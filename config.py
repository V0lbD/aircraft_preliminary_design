"""
Конфигурация приложения Matching Chart
Содержит пути и настройки
"""

import os
from pathlib import Path

# Определяем корневую папку проекта
PROJECT_ROOT = Path(__file__).parent

# Пути к папкам основного проекта
CORE_PATH = PROJECT_ROOT / "mca" / "core"
OUTPUTS_PATH = PROJECT_ROOT / "outputs"

# Убедимся, что папки существуют
OUTPUTS_PATH.mkdir(exist_ok=True)

# Путь к папке примеров в приложении
INPUTS_PATH = PROJECT_ROOT / "inputs"
INPUTS_PATH.mkdir(exist_ok=True)

# UI настройки
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_TITLE = "Диаграмма согласования (Matching Chart)"

# Таблицы
TABLE_ROW_HEIGHT = 30
TABLE_FONT_SIZE = 11

# График
CHART_DPI = 100
CHART_FIGURE_SIZE = (10, 8)

# Логирование
LOG_LEVEL = "INFO"
