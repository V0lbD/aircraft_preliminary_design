"""
Динамическая таблица для ввода/отображения данных ProjectData
Автоматически создаёт строки на основе полей ProjectData
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import fields

from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView, 
                              QAbstractItemView, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

# Добавляем пути для импортов
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.data_models import ProjectData
from core.constants import FIELD_LABELS, FIELD_UNITS, FIELD_CATEGORIES


class DynamicTable(QTableWidget):
    """
    Динамическая таблица для отображения и редактирования ProjectData
    Автоматически парсит структуру ProjectData и создаёт строки
    """
    
    def __init__(self, parent=None, read_only: bool = False, min_width: int = 300, min_height: int = 400):
        """
        Args:
            parent: родительский виджет
            read_only: если True, таблица только для чтения
        """
        super().__init__(parent)
        self.read_only = read_only
        self.field_mapping: Dict[int, str] = {}  # row_index -> field_name
        
        # Настройка таблицы
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Параметр", "Значение", "Единица"])
        
        # Стиль заголовка
        # self.setMinimumSize(600, 400)
        # self.setMaximumSize(1200, 800)

        # Растягивание на всё доступное пространство
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Вариант 2: Настраиваемые размеры по умолчанию (рекомендуется)
        self.setColumnWidth(0, min_width * 0.4)  # 40% для параметров
        self.setColumnWidth(1, min_width * 0.4)  # 45% для значений
        self.setColumnWidth(2, min_width * 0.2)  # 15% для единиц

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        
        # Установки таблицы
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)

        self.setWordWrap(True)
        self.setTextElideMode(Qt.TextElideMode.ElideRight)
        
        # Высота строк
        self.verticalHeader().setDefaultSectionSize(30)

        # Скрываем номера строк
        self.verticalHeader().setVisible(False)

        if read_only:
            self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            self.setEditTriggers(QAbstractItemView.DoubleClicked | 
                               QAbstractItemView.EditKeyPressed)
    
    def populate_from_data(self, data: ProjectData, fields_to_show: List[str] = None):
        """
        Заполняет таблицу данными из ProjectData
        
        Args:
            data: объект ProjectData
            fields_to_show: список полей для отображения (если None, показывает все)
        """
        self.setRowCount(0)
        self.field_mapping.clear()
        
        row = 0
        
        # Если не указаны поля, используем все доступные
        if fields_to_show is None:
            fields_to_show = self._get_all_available_fields(data)
        
        # Группируем по категориям для красоты
        for category, category_fields in FIELD_CATEGORIES.items():
            # Добавляем строку категории (заголовок)
            if any(f in fields_to_show for f in category_fields):
                self._add_category_row(category, row)
                row += 1
                
                # Добавляем поля в этой категории
                for field_name in category_fields:
                    if field_name in fields_to_show:
                        value = self._get_field_value(data, field_name)
                        self._add_data_row(row, field_name, value)
                        self.field_mapping[row] = field_name
                        row += 1
        
        # Добавляем оставшиеся поля (не в категориях)
        for field_name in fields_to_show:
            if not any(field_name in cat_fields 
                      for cat_fields in FIELD_CATEGORIES.values()):
                value = self._get_field_value(data, field_name)
                self._add_data_row(row, field_name, value)
                self.field_mapping[row] = field_name
                row += 1
        
        # Автоматическое выравнивание высоты
        self.resizeRowsToContents()
    
    def extract_data_to_object(self, data: ProjectData) -> ProjectData:
        """
        Извлекает данные из таблицы и обновляет ProjectData
        
        Args:
            data: объект ProjectData для обновления
            
        Returns:
            обновлённый ProjectData
        """
        for row, field_name in self.field_mapping.items():
            # Получаем значение из таблицы (колонка 1)
            item = self.item(row, 1)
            if item is not None:
                value_str = item.text().strip()
                
                if value_str:
                    try:
                        # Пробуем преобразовать в число
                        if '.' in value_str:
                            value = float(value_str)
                        else:
                            value = int(value_str)
                        
                        # Устанавливаем значение в ProjectData
                        self._set_field_value(data, field_name, value)
                    except ValueError:
                        # Если не число, оставляем как строка
                        self._set_field_value(data, field_name, value_str)
        
        return data
    
    def _add_category_row(self, category_name: str, row: int):
        """Добавляет строку категории (заголовок)"""
        self.insertRow(row)
        
        item = QTableWidgetItem(category_name)
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        item.setFont(font)
        item.setBackground(QColor(230, 240, 250))

        # Центрируем
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        
        self.setItem(row, 0, item)

        # Объединяем ячейки столбцов

        self.setSpan(row, 0, 1, 3)
        # Объединяем ячейки категории
        for col in range(1, 3):
            empty_item = QTableWidgetItem()
            empty_item.setBackground(QColor(230, 240, 250))
            self.setItem(row, col, empty_item)
    
    def _add_data_row(self, row: int, field_name: str, value: Any):
        """Добавляет строку данных"""
        self.insertRow(row)
        
        # Колонка 1: название параметра
        label = FIELD_LABELS.get(field_name, field_name)
        label_item = QTableWidgetItem(label)
        label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 0, label_item)

        # Колонка 2: значение
        # if isinstance(value, float):
        #     value_str = f"{value:.6f}"
        # else:
        #     value_str = str(value) if value is not None else ""
        value_str = str(value) if value is not None else ""

        # Заполнение схемы расположения крыла
        # if value_str == 'low':
        #     value_str = 'низкоплан'
        # elif value_str == 'mid':
        #     value_str = 'среднеплан'
        # elif value_str == 'high':
        #     value_str = 'высокоплан'

        value_item = QTableWidgetItem(value_str)
        if self.read_only:
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 1, value_item)
        
        # Колонка 3: единица измерения
        unit = FIELD_UNITS.get(field_name, "")
        unit_item = QTableWidgetItem(unit)
        unit_item.setFlags(unit_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 2, unit_item)
    
    def _get_all_available_fields(self, data: ProjectData) -> List[str]:
        """Получает все доступные поля из ProjectData"""
        available = []
        
        # Проверяем основные поля
        for field in FIELD_LABELS.keys():
            if hasattr(data, field):
                available.append(field)
        
        # Проверяем подструктуры
        sub_objects = [
            data.landing_data, data.takeoff_data, data.climb_data,
            data.cruise_data, data.missed_approach_data,
            data.aero_analysis_data, data.missed_approach_tw_data,
            data.matching_chart_data
        ]
        
        for sub_obj in sub_objects:
            if sub_obj:
                for field in FIELD_LABELS.keys():
                    if hasattr(sub_obj, field) and field not in available:
                        available.append(field)
        
        return available
    
    def _get_field_value(self, data: ProjectData, field_name: str) -> Any:
        """Получает значение поля из ProjectData"""
        # Проверяем основные поля
        if hasattr(data, field_name):
            value = getattr(data, field_name)
            if value is not None:
                return value
        
        # Проверяем подструктуры
        sub_objects = [
            data.preliminary_sizing, data.mass_estimation, data.geometry_data
        ]
        
        for sub_obj in sub_objects:
            if sub_obj and hasattr(sub_obj, field_name):
                value = getattr(sub_obj, field_name)
                if value is not None:
                    return value
        
        return None
    
    def _set_field_value(self, data: ProjectData, field_name: str, value: Any) -> None:
        """Устанавливает значение поля в ProjectData"""
        # Пробуем основные поля
        if hasattr(data, field_name):
            setattr(data, field_name, value)
            return
        
        # Пробуем подструктуры
        sub_objects = [
            data.preliminary_sizing, data.mass_estimation, data.geometry_data
        ]
        
        for sub_obj in sub_objects:
            if sub_obj and hasattr(sub_obj, field_name):
                setattr(sub_obj, field_name, value)
                return
