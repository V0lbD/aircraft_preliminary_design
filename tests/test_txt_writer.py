from __future__ import annotations

from aircraft_design.core.models import BlockResult, ProjectResult
from aircraft_design.io.txt_writer import format_txt_report, write_txt_result


def test_format_txt_report_is_human_readable() -> None:
    result = ProjectResult(
        schema_version="1.0",
        success=True,
        block_results=[
            BlockResult(
                block_name="preliminary_sizing",
                success=True,
                outputs={
                    "p0_optimal": 1234.5678,
                    "P0_optimal": 0.42,
                    "p0_by_V_s": 2500.0,
                    "P0_by_theta": 0.25,
                    "active_constraints": [
                        {
                            "id": 16,
                            "name": "Ограничение по градиенту набора высоты",
                        }
                    ],
                    "aerodynamics": {
                        "C_x_for_max_K": 0.031,
                        "C_y_for_max_K": 0.8,
                        "K_max": 25.8,
                    },
                    "chart_data": {
                        "large_array_that_should_not_be_in_report": [1, 2, 3],
                    },
                },
            ),
            BlockResult(
                block_name="mass_estimation",
                success=True,
                outputs={
                    "m_MTO": 8000.0,
                    "m_OE": 4500.0,
                    "m_F": 1200.0,
                    "m_ML": 7000.0,
                    "T_TO": 30000.0,
                    "S_W": 32.5,
                    "m_OE_ratio": 0.56,
                    "m_F_ratio": 0.15,
                    "m_ML_ratio": 0.88,
                    "useful_load_ratio": 0.28,
                    "mission": {
                        "M_ff_non_cruise": 0.94,
                        "M_ff_cruise": 0.87,
                        "M_ff_total": 0.82,
                        "breguet_range_factor": 8000000.0,
                    },
                },
            ),
            BlockResult(
                block_name="geometry",
                success=True,
                outputs={
                    "wing": {
                        "S_wing": 32.5,
                        "l_wing": 17.3,
                        "lambda_wing": 9.2,
                        "eta_wing": 2.5,
                        "b0_wing": 2.7,
                        "bk_wing": 1.1,
                        "sweep_wing_quarter": 25.0,
                        "sweep_wing_LE": 27.0,
                        "wing_scheme_ru": "среднеплан",
                    },
                    "fuselage": {
                        "L_fuselage": 20.5,
                        "d_fuselage": 2.3,
                        "r_fuselage": 1.15,
                        "lambda_fuselage": 9.0,
                    },
                    "horizontal_tail": {
                        "S_ht": 8.1,
                        "l_ht": 5.7,
                        "b0_ht": 1.8,
                        "bk_ht": 0.6,
                        "sweep_horizontal_tail_quarter": 30.0,
                        "sweep_ht_LE": 32.0,
                    },
                    "vertical_tail": {
                        "S_vt": 4.9,
                        "l_vt": 2.7,
                        "b0_vt": 2.4,
                        "bk_vt": 1.2,
                        "sweep_vertical_tail_quarter": 35.0,
                        "sweep_vt_LE": 37.0,
                    },
                },
            ),
        ],
    )

    report = format_txt_report(result)

    assert "Aircraft preliminary design report" in report
    assert "1. Предварительные характеристики" in report
    assert "2. Оценка масс" in report
    assert "3. Геометрия" in report
    assert "4. Статус расчётных блоков" in report
    assert "5. Предупреждения и ошибки" in report

    assert "Оптимальная нагрузка на крыло p0" in report
    assert "Максимальная взлётная масса m_MTO" in report
    assert "Крыло:" in report
    assert "Фюзеляж:" in report

    assert "chart_data" not in report
    assert "large_array_that_should_not_be_in_report" not in report


def test_write_txt_result_creates_file(tmp_path) -> None:
    result = ProjectResult(
        schema_version="1.0",
        success=True,
        block_results=[],
    )

    output_path = tmp_path / "result.txt"

    write_txt_result(result, output_path)

    assert output_path.exists()
    assert "Aircraft preliminary design report" in output_path.read_text(
        encoding="utf-8"
    )