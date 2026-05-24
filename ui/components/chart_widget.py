"""
Виджет для отображения диаграммы согласования (Matching Chart)
Интегрирует matplotlib с PySide6
"""

import sys
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.block_preliminary_sizing import BlockPreliminarySizing

# Добавляем пути для импортов
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.data_models import ProjectData
from core import block_preliminary_sizing


class ChartWidget(QWidget):
    """
    Виджет для отображения диаграммы согласования
    Использует matplotlib для рисования графика
    """
    
    def __init__(self, parent=None):
        """Инициализирует виджет графика"""
        super().__init__(parent)
        
        # Создаём matplotlib figure
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        # Инициализируем блок 8
        self.block = BlockPreliminarySizing()
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        title_label = QLabel("Область существования самолёта")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Canvas
        layout.addWidget(self.canvas)
        
        # Инициализация пустого графика
        self._init_empty_chart()
    
    def _init_empty_chart(self):
        """Инициализирует пустой график"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        ax.set_xlabel('Удельная нагрузка на крыло (Н/м²)', fontsize=11)
        ax.set_ylabel('Тяговооружённость', fontsize=11)
        ax.set_title('Область существования самолёта\n(Ожидание данных)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.text(0.5, 0.5, 'Данные не готовы\nВведите данные в таблицу\nи нажмите "Рассчитать"',
               transform=ax.transAxes, ha='center', va='center',
               fontsize=12, alpha=0.5)
        
        self.canvas.draw()
    
    def update_chart(self, data: ProjectData) -> bool:
        """
        Обновляет график на основе данных ProjectData
        
        Args:
            data: объект ProjectData с результатами расчётов
            
        Returns:
            True если график успешно обновлён
        """
        try:
            # Получаем данные для рисования
            chart_data = self.block.get_chart_data_for_plotting(data)

            # Очищаем предыдущий график
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            
            # Рисуем кривые ограничений
            self._draw_curves(ax, chart_data)

            # Рисуем оптимальную точку
            self._draw_optimal_point(ax, chart_data)

            # Рисуем допустимую область
            # self._draw_feasible_region(ax, chart_data)

            # Настройки осей и сетки
            ax.set_xlabel('Удельная нагрузка на крыло (Н/м²)', fontsize=11)
            ax.set_ylabel('Тяговооружённость', fontsize=11)
            ax.set_title('Область существования самолёта', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right', fontsize=10)
            
            # Установка диапазонов
            if chart_data['p0_range']:
                ax.set_xlim(chart_data['p0_range'])
            if chart_data['P0_range']:
                ax.set_ylim(chart_data['P0_range'])
            
            # Перерисовываем
            self.canvas.draw()
            return True
            
        except Exception as e:
            print(f"Ошибка при обновлении графика: {e}")
            self._init_empty_chart()
            return False
    
    def _draw_curves(self, ax, chart_data):
        """Рисует кривые ограничений"""

        # По градиенту набора высоты
        if chart_data['P0_by_theta_points']:
            p0, P0 = zip(*chart_data['P0_by_theta_points'])
            ax.plot(p0, P0, 'b--', linewidth=2.5, label='По градиенту набора высоты')
        
        # По эксплуатационной перегрузке
        if chart_data['P0_by_n_max_points']:
            p0, P0 = zip(*chart_data['P0_by_n_max_points'])
            ax.plot(p0, P0, 'g-', linewidth=2.5, label='По эксплуатационной перегрузке')
        
        # По взлётной дистанции
        if chart_data.get('P0_by_L_TODA_points'):
            p0, P0 = zip(*chart_data['P0_by_L_TODA_points'])
            ax.plot(p0, P0, 'orange', linewidth=2,
                   linestyle='-', label='По взлётной дистанции', alpha=0.7)
        
        # По скороподъёмности
        if chart_data['P0_by_V_y_points']:
            p0, P0 = zip(*chart_data['P0_by_V_y_points'])
            ax.plot(p0, P0, 'b-', linewidth=2.5, label='По скороподъёмности')

        # По крейсерскому полёту на заданной высоте и скорости
        if chart_data['P0_by_V_cruise_points']:
            p0, P0 = zip(*chart_data['P0_by_V_cruise_points'])
            ax.plot(p0, P0, 'm-', linewidth=2.5, label='По крейсерскому полёту')
        
        # По скорости сваливания (вертикальная линия)
        if chart_data['p0_by_V_s']:
            ax.axvline(x=chart_data['p0_by_V_s'], color='r', linestyle='--',
                      linewidth=2.5, label=f'По скорости сваливания (p0 = {chart_data["p0_by_V_s"]:.0f})')
    
    def _draw_optimal_point(self, ax, chart_data):
        """Рисует оптимальную точку"""
        if chart_data['optimal_point']:
            opt_wl, opt_tw = chart_data['optimal_point']
            
            # Маркер оптимальной точки
            ax.plot(opt_wl, opt_tw, 'ro', markersize=12, markerfacecolor='red',
                   markeredgecolor='darkred', markeredgewidth=2.5, 
                   label='Оптимальная точка', zorder=5)
            
            # Аннотация
            ax.annotate(f'WL={opt_wl:.0f}\nT/W={opt_tw:.4f}',
                       xy=(opt_wl, opt_tw), xytext=(15, 15),
                       textcoords='offset points', fontsize=10,
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', 
                                alpha=0.8, edgecolor='orange', linewidth=2),
                       arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.3',
                                      color='darkred', lw=2))
    
    def _draw_feasible_region(self, ax, chart_data):
        """Рисует допустимую область"""
        if (chart_data['p0_by_V_s'] and
            chart_data['p0_range'] and
            chart_data['P0_range']):
            
            wl_min = chart_data['p0_range'][0]
            wl_max = chart_data['p0_range'][1]
            tw_min = chart_data['P0_range'][0]
            tw_max = chart_data['P0_range'][1]
            
            # Допустимая область (светло-зелёная заливка)
            ax.fill_between([wl_min, wl_max], tw_min, tw_max,
                           alpha=0.1, color='green', label='Допустимая область', zorder=1)
    
    def clear(self):
        """Очищает график и показывает пустую диаграмму"""
        self._init_empty_chart()
