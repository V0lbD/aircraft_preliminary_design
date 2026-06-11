from __future__ import annotations

import pytest


def test_main_window_can_be_imported() -> None:
    pytest.importorskip("PySide6")
    from aircraft_design.ui.main_window import MainWindow  # noqa: PLC0415
    from aircraft_design.ui.run import run_gui_application  # noqa: PLC0415

    assert MainWindow is not None
    assert run_gui_application is not None