from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from aircraft_design.ui.main_window import MainWindow


def run_gui_application(argv: list[str] | None = None) -> int:
    """
    Run Qt GUI application.
    """
    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv if argv is None else argv)

    window = MainWindow()
    window.show()

    return app.exec()