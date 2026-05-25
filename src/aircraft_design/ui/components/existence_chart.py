from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from aircraft_design.ui.adapter import ExistenceChartView


class ExistenceChartWidget(QWidget):
    """
    Existence/design-space chart widget.

    Shows preliminary sizing constraints:
    x-axis: wing loading p0
    y-axis: thrust-to-weight ratio P0
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._figure = Figure(figsize=(6, 4))
        self._canvas = FigureCanvas(self._figure)
        self._axes = self._figure.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.addWidget(self._canvas)

        self.clear()

    def load_chart(self, chart_view: ExistenceChartView) -> None:
        self._axes.clear()

        if not chart_view.series:
            self._draw_empty_message()
            self._canvas.draw()
            return

        for series in chart_view.series:
            x_values = [point[0] for point in series.points]
            y_values = [point[1] for point in series.points]
            self._axes.plot(x_values, y_values, label=series.name)

        if chart_view.p0_by_v_s is not None:
            self._axes.axvline(
                chart_view.p0_by_v_s,
                linestyle="--",
                label="Скорость сваливания",
            )

        if chart_view.optimal_point is not None:
            x_optimal, y_optimal = chart_view.optimal_point
            self._axes.scatter(
                [x_optimal],
                [y_optimal],
                marker="o",
                s=60,
                label="Оптимальная точка",
            )

        self._axes.set_title("Область существования самолёта")
        self._axes.set_xlabel("p0, Н/м²")
        self._axes.set_ylabel("P0")
        self._axes.grid(True)
        self._axes.legend(loc="best")
        self._figure.tight_layout()
        self._canvas.draw()

    def clear(self) -> None:
        self._axes.clear()
        self._draw_empty_message()
        self._canvas.draw()

    def _draw_empty_message(self) -> None:
        self._axes.set_title("Область существования самолёта")
        self._axes.set_xlabel("p0, Н/м²")
        self._axes.set_ylabel("P0")
        self._axes.grid(True)
        self._axes.text(
            0.5,
            0.5,
            "Нет данных для графика",
            ha="center",
            va="center",
            transform=self._axes.transAxes,
        )
        self._figure.tight_layout()