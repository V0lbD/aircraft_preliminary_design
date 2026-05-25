from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from aircraft_design.ui.adapter import OutputRowView


class OutputTableWidget(QWidget):
    """
    Non-editable output table widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._table = QTableWidget(self)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            [
                "Раздел",
                "Параметр",
                "Значение",
                "Ед.",
            ]
        )

        self._table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)

    def load_rows(self, rows: list[OutputRowView]) -> None:
        self._table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            self._set_item(row_index, 0, row.section)
            self._set_item(row_index, 1, row.display_name)
            self._set_item(row_index, 2, self._format_value(row.value))
            self._set_item(row_index, 3, row.unit or "")

    def clear(self) -> None:
        self._table.setRowCount(0)

    def _set_item(self, row: int, column: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self._table.setItem(row, column, item)

    @staticmethod
    def _format_value(value: Any) -> str:
        if value is None:
            return "-"

        if isinstance(value, bool):
            return str(value)

        if isinstance(value, int):
            return str(value)

        if isinstance(value, float):
            abs_value = abs(value)

            if value != 0 and (abs_value >= 1e6 or abs_value < 1e-3):
                return f"{value:.4e}"

            return f"{value:.4f}".rstrip("0").rstrip(".")

        return str(value)