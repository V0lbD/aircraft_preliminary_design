from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from aircraft_design.ui.adapter import InputFieldView, InputSectionView


class InputTableWidget(QWidget):
    """
    Editable input table widget.

    It displays one input section at a time:
    - preliminary_sizing
    - mass_estimation
    - geometry

    The widget itself does not validate engineering data.
    It only collects values. Validation is done later by input_builder.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._sections: list[InputSectionView] = []
        self._current_section_index = -1
        self._updating_table = False

        self._section_combo = QComboBox(self)
        self._description_label = QLabel(self)
        self._description_label.setWordWrap(True)

        self._table = QTableWidget(self)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            [
                "Параметр",
                "Значение",
                "Ед.",
                "Описание",
            ]
        )

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)

        self._table.setColumnWidth(0, 230)  # параметр
        self._table.setColumnWidth(1, 120)  # значение
        self._table.setColumnWidth(2, 80)  # ед.
        self._table.setColumnWidth(3, 420)  # описание

        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self._section_combo)
        layout.addWidget(self._description_label)
        layout.addWidget(self._table)

        self._section_combo.currentIndexChanged.connect(self._on_section_changed)

    def load_sections(self, sections: list[InputSectionView]) -> None:
        """
        Load input sections into widget.
        """
        self._sync_current_section_from_table()

        self._sections = sections
        self._current_section_index = -1

        self._section_combo.blockSignals(True)
        self._section_combo.clear()

        for section in self._sections:
            self._section_combo.addItem(section.display_name, section.section_name)

        self._section_combo.blockSignals(False)

        if self._sections:
            self._section_combo.setCurrentIndex(0)
            self._on_section_changed(0)
        else:
            self._table.setRowCount(0)
            self._description_label.clear()

    def get_sections(self) -> list[InputSectionView]:
        """
        Return sections with current edited values.
        """
        self._sync_current_section_from_table()
        return self._sections

    def get_section_values(self) -> dict[str, dict[str, Any]]:
        """
        Return raw values grouped by section.

        This is suitable for create_project_input_from_sections(...)
        or run_calculation_from_sections(...).
        """
        self._sync_current_section_from_table()

        values: dict[str, dict[str, Any]] = {}

        for section in self._sections:
            values[section.section_name] = {
                field.name: field.value
                for field in section.fields
            }

        return values

    def set_current_section(self, section_name: str) -> None:
        for index, section in enumerate(self._sections):
            if section.section_name == section_name:
                self._section_combo.setCurrentIndex(index)
                return

    def _on_section_changed(self, index: int) -> None:
        if index < 0 or index >= len(self._sections):
            return

        if self._current_section_index != index:
            self._sync_current_section_from_table()

        self._current_section_index = index
        self._populate_table(self._sections[index])

    def _populate_table(self, section: InputSectionView) -> None:
        self._updating_table = True

        self._clear_table_cell_widgets()

        self._description_label.setText(section.description)
        self._table.clearContents()
        self._table.setRowCount(len(section.fields))

        for row, field in enumerate(section.fields):
            self._set_read_only_item(row, 0, field.display_name)
            self._set_value_cell(row, field)
            self._set_read_only_item(row, 2, field.unit or "")
            self._set_read_only_item(row, 3, field.description)

        self._updating_table = False

    def _set_value_cell(self, row: int, field: InputFieldView) -> None:
        old_widget = self._table.cellWidget(row, 1)

        if old_widget is not None:
            self._table.removeCellWidget(row, 1)
            old_widget.deleteLater()

        if field.choices:
            combo = QComboBox(self._table)

            for choice in field.choices:
                combo.addItem(self._choice_to_text(field, choice), choice)

            self._set_combo_value(combo, field.value)
            self._table.setCellWidget(row, 1, combo)
            return

        if field.value_type == "boolean":
            combo = QComboBox(self._table)
            combo.addItem("Нет", False)
            combo.addItem("Да", True)
            self._set_combo_value(combo, bool(field.value))
            self._table.setCellWidget(row, 1, combo)
            return

        item = QTableWidgetItem(self._value_to_text(field.value))
        item.setFlags(
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )
        self._table.setItem(row, 1, item)

    def _clear_table_cell_widgets(self) -> None:
        """
        Remove widgets from all table cells before repopulating the table.

        QTableWidget does not always remove old cell widgets when setItem(...)
        is called later for the same cell. Without this cleanup, combo boxes from
        one input section can visually remain in another section.
        """
        for row in range(self._table.rowCount()):
            for column in range(self._table.columnCount()):
                cell_widget = self._table.cellWidget(row, column)

                if cell_widget is not None:
                    self._table.removeCellWidget(row, column)
                    cell_widget.deleteLater()

    def _set_read_only_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row, column, item)

    def _sync_current_section_from_table(self) -> None:
        if self._updating_table:
            return

        if self._current_section_index < 0:
            return

        if self._current_section_index >= len(self._sections):
            return

        section = self._sections[self._current_section_index]

        for row, field in enumerate(section.fields):
            field.value = self._read_field_value(row, field)

    def _read_field_value(self, row: int, field: InputFieldView) -> Any:
        cell_widget = self._table.cellWidget(row, 1)

        if isinstance(cell_widget, QComboBox):
            return cell_widget.currentData()

        item = self._table.item(row, 1)

        if item is None:
            return None

        text = item.text().strip()

        if text == "":
            return None

        return self._parse_text_value(text, field)

    @staticmethod
    def _parse_text_value(text: str, field: InputFieldView) -> Any:
        """
        Best-effort UI parsing.

        Invalid values are intentionally returned as raw strings so that
        the input validation layer can produce a proper validation error.
        """
        if field.value_type == "number":
            try:
                return float(text)
            except ValueError:
                return text

        if field.value_type == "integer":
            try:
                value = float(text)
            except ValueError:
                return text

            if value.is_integer():
                return int(value)

            return text

        return text

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: Any) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    @staticmethod
    def _choice_to_text(field: InputFieldView, choice: Any) -> str:
        if field.choice_display_names and choice in field.choice_display_names:
            return field.choice_display_names[choice]

        return str(choice)

    @staticmethod
    def _value_to_text(value: Any) -> str:
        if value is None:
            return ""

        return str(value)