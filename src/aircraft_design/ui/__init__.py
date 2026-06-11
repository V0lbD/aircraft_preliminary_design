from aircraft_design.ui.adapter import (
    ChartSeriesView,
    ExistenceChartView,
    InputFieldView,
    InputSectionView,
    OutputRowView,
    build_existence_chart_view,
    build_input_table_sections,
    build_output_table_rows,
    collect_input_sections_from_field_views,
)

try:
    from aircraft_design.ui.main_window import MainWindow
    from aircraft_design.ui.run import run_gui_application
except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional PySide6
    if exc.name != "PySide6":
        raise
    MainWindow = None  # type: ignore[assignment]
    run_gui_application = None  # type: ignore[assignment]

__all__ = [
    "ChartSeriesView",
    "ExistenceChartView",
    "InputFieldView",
    "InputSectionView",
    "MainWindow",
    "OutputRowView",
    "build_existence_chart_view",
    "build_input_table_sections",
    "build_output_table_rows",
    "collect_input_sections_from_field_views",
    "run_gui_application",
]
