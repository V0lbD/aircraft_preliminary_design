from __future__ import annotations

import logging
from pathlib import Path
import sys
import pandas as pd

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

from aircraft_design.app import run_calculation
from aircraft_design.core.errors import AircraftDesignError
from aircraft_design.core.models.project import ProjectState
from aircraft_design.io.json_io import load_project_from_json, save_project_to_json
from aircraft_design.io.txt_writer import write_txt_result
from aircraft_design.io.tech_db_loader import load_technology_database_into_project

from aircraft_design.ui.adapter import (
    build_existence_chart_view,
    build_input_table_sections,
    build_output_table_rows,
    update_project_from_ui,
)
from aircraft_design.ui.components import (
    ExistenceChartWidget,
    InputTableWidget,
    OutputTableWidget,
)

logger = logging.getLogger(__name__)


def get_resource_path(relative_path: str) -> Path:
    """Возвращает абсолютный путь к ресурсу."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Если запущено как скомпилированный .exe, ищем папку РЯДОМ с .exe
        base_path = Path(sys.executable).parent
    else:
        # Если запущено из IDE
        base_path = Path.cwd()
    return base_path / relative_path


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        # Всё состояние приложения живет в одном объекте!
        self._project = ProjectState()

        self.setWindowTitle("Aircraft Preliminary Design")
        self.resize(1400, 900)

        self._input_table = InputTableWidget(self)
        self._chart = ExistenceChartWidget(self)
        self._output_table = OutputTableWidget(self)

        self._status_label = QLabel("Готово", self)

        self._load_json_button = QPushButton("Загрузить JSON", self)
        self._save_input_json_button = QPushButton("Сохранить входной JSON", self)
        self._calculate_button = QPushButton("Рассчитать", self)
        self._save_txt_button = QPushButton("Сохранить TXT", self)
        self._save_json_button = QPushButton("Сохранить JSON", self)
        self._save_dat_button = QPushButton("Экспорт 3D (.dat)", self)
        self._save_trace_button = QPushButton("Отчет с формулами (.md)", self)
        self._clear_button = QPushButton("Очистить результаты", self)

        self._setup_layout()
        self._connect_signals()

        # Сразу загружаем дефолтные значения из дескрипторов в UI
        self._load_project_to_ui()

    def _setup_layout(self) -> None:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self._load_json_button)
        toolbar_layout.addWidget(self._save_input_json_button)
        toolbar_layout.addWidget(self._calculate_button)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self._save_txt_button)
        toolbar_layout.addWidget(self._save_json_button)
        toolbar_layout.addWidget(self._save_dat_button)
        toolbar_layout.addWidget(self._save_trace_button)
        toolbar_layout.addWidget(self._clear_button)

        top_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        top_splitter.addWidget(self._input_table)
        top_splitter.addWidget(self._chart)
        top_splitter.setStretchFactor(0, 2)
        top_splitter.setStretchFactor(1, 1)
        top_splitter.setSizes([850, 450])

        main_splitter = QSplitter(Qt.Orientation.Vertical, self)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self._output_table)
        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([600, 300])

        root_layout.addLayout(toolbar_layout)
        root_layout.addWidget(main_splitter)
        self.setCentralWidget(central_widget)

        status_bar = QStatusBar(self)
        status_bar.addWidget(self._status_label)
        self.setStatusBar(status_bar)

    def _connect_signals(self) -> None:
        self._load_json_button.clicked.connect(self._on_load_json_clicked)
        self._save_input_json_button.clicked.connect(self._on_save_input_json_clicked)
        self._calculate_button.clicked.connect(self._on_calculate_clicked)
        self._save_txt_button.clicked.connect(self._on_save_txt_clicked)
        self._save_json_button.clicked.connect(self._on_save_json_clicked)
        self._save_dat_button.clicked.connect(self._on_save_dat_clicked)
        self._save_trace_button.clicked.connect(self._on_save_trace_clicked)
        self._clear_button.clicked.connect(self._on_clear_clicked)

    def _load_project_to_ui(self) -> None:
        """Синхронизирует данные из объекта ProjectState в UI таблицы."""
        sections = build_input_table_sections(self._project)
        self._input_table.load_sections(sections)
        self._output_table.clear()
        self._chart.clear()

    def _update_project_from_ui(self) -> None:
        """Забирает данные из редактируемой таблицы и обновляет ProjectState."""
        ui_data = self._input_table.get_section_values()
        update_project_from_ui(self._project, ui_data)

    def _on_load_json_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить входной JSON", "inputs/projects", "JSON files (*.json);;All files (*.*)"
        )
        if not file_path: return

        try:
            # Создаем чистый проект и загружаем в него данные
            self._project = ProjectState()
            load_project_from_json(self._project, file_path)

            self._load_project_to_ui()
            self._set_status(f"Загружен файл: {file_path}")
        except Exception as exc:
            logger.exception("Failed to load JSON input")
            self._show_error("Ошибка загрузки JSON", str(exc))

    def _on_save_dat_clicked(self) -> None:
        if not self._project.trace_records and not self._project.errors:
            self._show_warning("Нет результатов", "Сначала выполните расчёт.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт 3D (.dat)", "outputs/model.dat", "DAT files (*.dat);;All files (*.*)"
        )
        if not file_path: return

        try:
            from aircraft_design.io.dat_writer import write_3d_dat
            write_3d_dat(self._project, Path(file_path))
            self._set_status(f"Файл 3D-модели сохранён: {file_path}")
        except Exception as exc:
            logger.exception("Failed to export DAT result")
            self._show_error("Ошибка экспорта", str(exc))

    def _on_save_trace_clicked(self) -> None:
        if not self._project.trace_records:
            self._show_warning("Нет результатов", "Сначала выполните расчёт.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет (Trace)", "outputs/trace.md", "Markdown files (*.md);;All files (*.*)"
        )
        if not file_path: return

        try:
            from aircraft_design.io.trace_writer import write_trace_markdown
            write_trace_markdown(self._project, Path(file_path))
            self._set_status(f"Отчет сохранён: {file_path}")
        except Exception as exc:
            logger.exception("Failed to export trace")
            self._show_error("Ошибка экспорта", str(exc))

    def _on_save_input_json_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить входной JSON", "inputs/projects/input_from_ui.json", "JSON files (*.json);;All files (*.*)"
        )
        if not file_path: return

        try:
            self._update_project_from_ui()
            save_project_to_json(self._project, Path(file_path))
            self._set_status(f"Входной JSON сохранён: {file_path}")
        except Exception as exc:
            logger.exception("Failed to save input JSON")
            self._show_error("Ошибка сохранения входного JSON", str(exc))

    def _load_technology_database(self) -> None:
        """Загружает таблицы Excel, используя общий загрузчик."""
        load_technology_database_into_project(self._project)

    def _on_calculate_clicked(self) -> None:
        try:
            # 1. Очищаем старые ошибки и логи перед новым расчетом
            self._project.errors.clear()
            self._project.warnings.clear()
            self._project.trace_records.clear()

            # 2. Забираем изменения из UI
            self._update_project_from_ui()

            # 3. Подгружаем таблицы (Excel) "на лету" перед расчетом
            self._load_technology_database()

            # 4. Запускаем конвейер
            success = run_calculation(self._project, stop_on_error=True)

            # 5. Выводим результаты на экран
            self._show_result()

            if success:
                self._set_status("Расчёт успешно завершён")
            else:
                self._set_status("Расчёт завершён с ошибками")
                self._show_warning("Расчёт завершён с ошибками", "\n".join(self._project.errors))

        except AircraftDesignError as exc:
            logger.warning("Calculation error: %s", exc)
            self._show_error("Ошибка расчёта", str(exc))
            self._set_status("Ошибка расчёта")
        except Exception as exc:
            logger.exception("Unexpected calculation error")
            self._show_error("Неожиданная ошибка", str(exc))
            self._set_status("Критическая ошибка")

    def _show_result(self) -> None:
        output_rows = build_output_table_rows(self._project)
        chart_view = build_existence_chart_view(self._project)

        self._output_table.load_rows(output_rows)
        self._chart.load_chart(chart_view)

    def _on_save_txt_clicked(self) -> None:
        if not self._project.trace_records and not self._project.errors:
            self._show_warning("Нет результатов", "Сначала выполните расчёт.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить TXT", "outputs/result.txt",
                                                   "Text files (*.txt);;All files (*.*)")
        if not file_path: return

        try:
            write_txt_result(self._project, Path(file_path))
            self._set_status(f"TXT сохранён: {file_path}")
        except Exception as exc:
            logger.exception("Failed to save TXT result")
            self._show_error("Ошибка сохранения TXT", str(exc))

    def _on_save_json_clicked(self) -> None:
        if not self._project.trace_records and not self._project.errors:
            self._show_warning("Нет результатов", "Сначала выполните расчёт.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить JSON", "outputs/result.json",
                                                   "JSON files (*.json);;All files (*.*)")
        if not file_path: return

        try:
            save_project_to_json(self._project, Path(file_path))
            self._set_status(f"JSON сохранён: {file_path}")
        except Exception as exc:
            logger.exception("Failed to save JSON result")
            self._show_error("Ошибка сохранения JSON", str(exc))

    def _on_clear_clicked(self) -> None:
        self._project = ProjectState()  # Сброс состояния до дефолтного
        self._load_project_to_ui()
        self._set_status("Результаты очищены")

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _show_error(self, title: str, text: str) -> None:
        QMessageBox.critical(self, title, text)

    def _show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)