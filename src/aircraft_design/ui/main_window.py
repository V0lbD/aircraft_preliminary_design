from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from aircraft_design.app import run_calculation_from_sections
from aircraft_design.core.errors import AircraftDesignError
from aircraft_design.core.models import ProjectInput, ProjectResult
from aircraft_design.io import load_project_input, write_json_result, write_txt_result
from aircraft_design.ui.adapter import (
    build_existence_chart_view,
    build_input_table_sections,
    build_output_table_rows,
)
from aircraft_design.ui.components import (
    ExistenceChartWidget,
    InputTableWidget,
    OutputTableWidget,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window for the new UI.

    Core UI principle:
    - editable input table;
    - existence/design-space chart;
    - non-editable output table.
    """

    def __init__(self) -> None:
        super().__init__()

        self._last_result: ProjectResult | None = None
        self._aircraft: dict[str, Any] = {
            "aircraft_type": "business_jet",
        }
        self._metadata: dict[str, Any] = {
            "source": "ui",
        }

        self.setWindowTitle("Aircraft Preliminary Design")
        self.resize(1400, 900)

        self._input_table = InputTableWidget(self)
        self._chart = ExistenceChartWidget(self)
        self._output_table = OutputTableWidget(self)

        self._status_label = QLabel("Готово", self)

        self._load_json_button = QPushButton("Загрузить JSON", self)
        self._calculate_button = QPushButton("Рассчитать", self)
        self._save_txt_button = QPushButton("Сохранить TXT", self)
        self._save_json_button = QPushButton("Сохранить JSON", self)
        self._clear_button = QPushButton("Очистить результаты", self)

        self._setup_layout()
        self._connect_signals()
        self._load_default_input_sections()

    def _setup_layout(self) -> None:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self._load_json_button)
        toolbar_layout.addWidget(self._calculate_button)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self._save_txt_button)
        toolbar_layout.addWidget(self._save_json_button)
        toolbar_layout.addWidget(self._clear_button)

        top_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        top_splitter.addWidget(self._input_table)
        top_splitter.addWidget(self._chart)
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 2)

        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self._output_table)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        root_layout.addLayout(toolbar_layout)
        root_layout.addWidget(main_splitter)

        self.setCentralWidget(central_widget)

        status_bar = QStatusBar(self)
        status_bar.addWidget(self._status_label)
        self.setStatusBar(status_bar)

    def _connect_signals(self) -> None:
        self._load_json_button.clicked.connect(self._on_load_json_clicked)
        self._calculate_button.clicked.connect(self._on_calculate_clicked)
        self._save_txt_button.clicked.connect(self._on_save_txt_clicked)
        self._save_json_button.clicked.connect(self._on_save_json_clicked)
        self._clear_button.clicked.connect(self._on_clear_clicked)

    def _load_default_input_sections(self) -> None:
        sections = build_input_table_sections()
        self._input_table.load_sections(sections)

    def _on_load_json_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить входной JSON",
            "examples/inputs",
            "JSON files (*.json);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            project_input = load_project_input(file_path)
            self._load_project_input_to_ui(project_input)
            self._metadata["source_file"] = str(file_path)
            self._set_status(f"Загружен файл: {file_path}")

        except Exception as exc:
            logger.exception("Failed to load JSON input")
            self._show_error(
                "Ошибка загрузки JSON",
                str(exc),
            )

    def _load_project_input_to_ui(self, project_input: ProjectInput) -> None:
        self._aircraft = dict(project_input.aircraft)
        self._metadata = dict(project_input.metadata)

        values = {
            "preliminary_sizing": project_input.preliminary_sizing,
            "mass_estimation": project_input.mass_estimation,
            "geometry": project_input.geometry,
        }

        sections = build_input_table_sections(values=values)
        self._input_table.load_sections(sections)

        self._last_result = None
        self._output_table.clear()
        self._chart.clear()

    def _on_calculate_clicked(self) -> None:
        try:
            section_values = self._input_table.get_section_values()

            result = run_calculation_from_sections(
                preliminary_sizing=section_values.get("preliminary_sizing", {}),
                mass_estimation=section_values.get("mass_estimation", {}),
                geometry=section_values.get("geometry", {}),
                aircraft=self._aircraft,
                metadata=self._metadata,
                trace_enabled=True,
            )

            self._last_result = result
            self._show_result(result)

            if result.success:
                self._set_status("Расчёт успешно завершён")
            else:
                self._set_status("Расчёт завершён с ошибками")
                self._show_warning(
                    "Расчёт завершён с ошибками",
                    "\n".join(result.errors) if result.errors else "Неизвестная ошибка",
                )

        except AircraftDesignError as exc:
            logger.warning("Calculation validation error: %s", exc)
            self._show_error("Ошибка входных данных", str(exc))
            self._set_status("Ошибка входных данных")

        except Exception as exc:
            logger.exception("Unexpected calculation error")
            self._show_error("Неожиданная ошибка расчёта", str(exc))
            self._set_status("Ошибка расчёта")

    def _show_result(self, result: ProjectResult) -> None:
        output_rows = build_output_table_rows(result)
        chart_view = build_existence_chart_view(result)

        self._output_table.load_rows(output_rows)
        self._chart.load_chart(chart_view)

    def _on_save_txt_clicked(self) -> None:
        if self._last_result is None:
            self._show_warning(
                "Нет результатов",
                "Сначала выполните расчёт.",
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результат TXT",
            "outputs/result.txt",
            "Text files (*.txt);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            write_txt_result(self._last_result, Path(file_path))
            self._set_status(f"TXT сохранён: {file_path}")

        except Exception as exc:
            logger.exception("Failed to save TXT result")
            self._show_error("Ошибка сохранения TXT", str(exc))

    def _on_save_json_clicked(self) -> None:
        if self._last_result is None:
            self._show_warning(
                "Нет результатов",
                "Сначала выполните расчёт.",
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить результат JSON",
            "outputs/result.json",
            "JSON files (*.json);;All files (*.*)",
        )

        if not file_path:
            return

        try:
            write_json_result(self._last_result, Path(file_path))
            self._set_status(f"JSON сохранён: {file_path}")

        except Exception as exc:
            logger.exception("Failed to save JSON result")
            self._show_error("Ошибка сохранения JSON", str(exc))

    def _on_clear_clicked(self) -> None:
        self._last_result = None
        self._output_table.clear()
        self._chart.clear()
        self._set_status("Результаты очищены")

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _show_error(self, title: str, text: str) -> None:
        QMessageBox.critical(
            self,
            title,
            text,
        )

    def _show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(
            self,
            title,
            text,
        )