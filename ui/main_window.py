"""
Главное окно приложения Matching Chart
Интегрирует INPUT таблицу, OUTPUT таблицу, график и кнопки управления
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QPushButton, QSplitter, QLabel, QTextEdit,
                              QFileDialog, QMessageBox, QProgressBar,
                              QGroupBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

# Добавляем пути для импортов
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import OUTPUTS_PATH, INPUTS_PATH
from core.data_models import ProjectData, PreliminarySizingData
from core.file_io import FileIO
from core.calculation_engine import CalculationEngine
from core.block_preliminary_sizing import BlockPreliminarySizing
from core.block_mass_estimation import BlockMassEstimation
from core.constants import INPUT_FIELDS, OUTPUT_FIELDS

from .components.dynamic_table import DynamicTable
from .components.chart_widget import ChartWidget


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        """Инициализирует главное окно"""
        super().__init__()
        
        self.setWindowTitle("Главное окно")
        self.resize(1400, 900)
        
        # Данные проекта
        self.project_data = ProjectData()
        
        # Движок расчётов
        self.calculation_engine = CalculationEngine()
        
        # Создаём UI
        self._create_ui()
        
        # Таймер для обновления UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._on_calculation_progress)
    
    def _create_ui(self):
        """Создаёт интерфейс приложения"""
        # Главный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== Верхняя часть: INPUT + CHART =====
        top_layout = QHBoxLayout()
        
        # Левая часть: INPUT таблица
        left_layout = QVBoxLayout()
        
        # Заголовок INPUT
        input_title = QLabel("ВХОДНЫЕ ДАННЫЕ (INPUT)")
        input_title_font = QFont()
        input_title_font.setBold(True)
        input_title_font.setPointSize(12)
        input_title.setFont(input_title_font)
        left_layout.addWidget(input_title)
        
        # INPUT таблица
        self.input_table = DynamicTable(read_only=False)
        self.input_table.populate_from_data(self.project_data, INPUT_FIELDS)
        left_layout.addWidget(self.input_table)
        
        # Кнопки управления для INPUT
        input_buttons_layout = QHBoxLayout()
        
        load_button = QPushButton("📂 Загрузить из файла")
        load_button.clicked.connect(self._on_load_file)
        input_buttons_layout.addWidget(load_button)
        
        calculate_button = QPushButton("🔧 Рассчитать")
        calculate_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        calculate_button.clicked.connect(self._on_calculate)
        self.calculate_button = calculate_button
        input_buttons_layout.addWidget(calculate_button)
        
        left_layout.addLayout(input_buttons_layout)
        
        # Добавляем левую часть в top_layout
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setMinimumWidth(350)
        left_widget.setMaximumWidth(500)
        top_layout.addWidget(left_widget)
        
        # Правая часть: График
        right_layout = QVBoxLayout()
        
        chart_title = QLabel("Предварительное определение параметров")
        chart_title_font = QFont()
        chart_title_font.setBold(True)
        chart_title_font.setPointSize(12)
        chart_title.setFont(chart_title_font)
        right_layout.addWidget(chart_title)
        
        self.chart_widget = ChartWidget()
        right_layout.addWidget(self.chart_widget)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        top_layout.addWidget(right_widget, 1)
        
        main_layout.addLayout(top_layout, 2)
        
        # ===== Нижняя часть: OUTPUT таблица =====
        bottom_layout = QVBoxLayout()
        
        output_title = QLabel("РЕЗУЛЬТАТЫ (OUTPUT)")
        output_title_font = QFont()
        output_title_font.setBold(True)
        output_title_font.setPointSize(12)
        output_title.setFont(output_title_font)
        bottom_layout.addWidget(output_title)
        
        # OUTPUT таблица (только для чтения)
        self.output_table = DynamicTable(read_only=True, min_width=1300)
        self.output_table.populate_from_data(self.project_data, OUTPUT_FIELDS)
        self.output_table.setMaximumHeight(200)
        bottom_layout.addWidget(self.output_table)
        
        # Кнопки управления для OUTPUT
        output_buttons_layout = QHBoxLayout()
        
        save_button = QPushButton("💾 Сохранить результаты")
        save_button.clicked.connect(self._on_save_results)
        output_buttons_layout.addWidget(save_button)

        # Геометрия
        save_geometry_button = QPushButton("📐 Сохранить геометрию")
        save_geometry_button.clicked.connect(self._on_save_geometry)
        output_buttons_layout.addWidget(save_geometry_button)

        clear_button = QPushButton("🗑️ Очистить")
        clear_button.clicked.connect(self._on_clear_all)
        output_buttons_layout.addWidget(clear_button)
        
        output_buttons_layout.addStretch()
        
        bottom_layout.addLayout(output_buttons_layout)
        
        main_layout.addLayout(bottom_layout, 1)
        
        # ===== Статус-бар =====
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готово")
    
    def _on_load_file(self):
        """Загружает данные из файла"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Загрузить входные данные",
            str(INPUTS_PATH),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                self.project_data = FileIO.parse_input_file(Path(file_path))
                self.input_table.populate_from_data(self.project_data, INPUT_FIELDS)
                self.status_bar.showMessage(f"✓ Файл загружен: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка при загрузке", str(e))
                self.status_bar.showMessage("✗ Ошибка при загрузке файла")
    
    def _on_calculate(self):
        """Запускает расчёты"""
        try:
            # Извлекаем данные из INPUT таблицы
            self.project_data = self.input_table.extract_data_to_object(self.project_data)
            
            self.status_bar.showMessage("⏳ Выполняю расчёты...")
            self.calculate_button.setEnabled(False)
            
            # Запускаем расчёты в отдельном потоке (для простоты синхронно)
            success = self.calculation_engine.calculate(self.project_data)
            
            # Выводим лог
            log = self.calculation_engine.get_log()
            print(log)
            
            if success:
                # Обновляем OUTPUT таблицу
                self.output_table.populate_from_data(self.project_data, OUTPUT_FIELDS)
                
                # Обновляем график
                self.chart_widget.update_chart(self.project_data)
                
                self.status_bar.showMessage("✓ Расчёты завершены успешно")
                QMessageBox.information(self, "Успех", "Расчёты успешно завершены!")
            else:
                errors = self.calculation_engine.get_errors()
                error_msg = "\n".join(errors)
                QMessageBox.warning(self, "Ошибка расчётов", f"Ошибки:\n{error_msg}")
                self.status_bar.showMessage("✗ Ошибка при расчётах")
        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Непредвиденная ошибка:\n{str(e)}")
            self.status_bar.showMessage("✗ Ошибка")
        
        finally:
            self.calculate_button.setEnabled(True)
    
    def _on_save_results(self):
        """Сохраняет результаты в файл"""
        if self.project_data.preliminary_sizing.p0_optimal is None:
            QMessageBox.warning(self, "Внимание", 
                              "Сначала выполните расчёты перед сохранением")
            return
        
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self,
            "Сохранить результаты",
            str(OUTPUTS_PATH / "результаты.txt"),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                FileIO.save_output_file(Path(file_path), self.project_data)
                self.status_bar.showMessage(f"✓ Результаты сохранены: {Path(file_path).name}")
                QMessageBox.information(self, "Успех", f"Результаты сохранены в:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка при сохранении", str(e))
    
    def _on_clear_all(self):
        """Очищает все данные"""
        reply = QMessageBox.question(self, "Подтверждение", 
                                     "Вы уверены? Это удалит все данные.",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.project_data = ProjectData()
            self.input_table.populate_from_data(self.project_data, INPUT_FIELDS)
            self.output_table.populate_from_data(self.project_data, OUTPUT_FIELDS)
            self.chart_widget.clear()
            self.status_bar.showMessage("✓ Данные очищены")
    
    def _on_calculation_progress(self):
        """Callback для прогресса расчётов (зарезервировано для будущего)"""
        pass

    def _on_save_geometry(self):
        """Сохраняет геометрические параметры в файл"""
        # Проверяем, есть ли рассчитанные геометрические параметры
        if (self.project_data.geometry_data.l_wing is None or
                self.project_data.geometry_data.L_fuselage is None):
            QMessageBox.warning(
                self,
                "Внимание",
                "Сначала выполните расчёты геометрии перед сохранением"
            )
            return

        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self,
            "Сохранить геометрические параметры",
            str(OUTPUTS_PATH / "геометрия.txt"),
            "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            try:
                FileIO.save_geometry_file(Path(file_path), self.project_data)
                self.status_bar.showMessage(f"✓ Геометрия сохранена: {Path(file_path).name}")
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Геометрические параметры сохранены в:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Ошибка при сохранении геометрии", str(e))
                self.status_bar.showMessage("✗ Ошибка при сохранении геометрии")