from __future__ import annotations


def test_ui_components_can_be_imported() -> None:
    from aircraft_design.ui.components import (  # noqa: PLC0415
        ExistenceChartWidget,
        InputTableWidget,
        OutputTableWidget,
    )

    assert ExistenceChartWidget is not None
    assert InputTableWidget is not None
    assert OutputTableWidget is not None