from __future__ import annotations

import logging
import math

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError

logger = logging.getLogger(__name__)


class GeometryBlock(BaseBlock):
    """
    Блок расчета геометрии крыла, фюзеляжа и оперения.
    Использует данные из блоков предварительного расчета и оценки масс.
    """
    name = "geometry"
    display_name = "Геометрия"

    def calculate(self, project: 'ProjectState') -> None:
        geom = project.geometry
        mass = project.mass
        prelim = project.preliminary

        S_wing = mass.S_W
        if S_wing is None or S_wing <= 0:
            raise InputValidationError(
                "Для расчета геометрии площадь крыла (S_W) должна быть больше нуля. Блок mass_estimation отработал некорректно.")

        lambda_wing = prelim.Lambda
        if lambda_wing is None or lambda_wing <= 0:
            raise InputValidationError("Для расчета геометрии удлинение крыла (Lambda) должно быть больше нуля.")

        # === Крыло (Wing) ===
        l_wing = math.sqrt(S_wing * lambda_wing)
        project.add_trace(
            value_name="wing_span",
            formula=r"l_{wing} = \sqrt{S_{wing} \cdot \lambda_{wing}}",
            values={"S_wing": S_wing, "lambda_wing": lambda_wing},
            result=float(l_wing), unit="m", description="Размах крыла."
        )

        b0_wing = (2.0 * S_wing) / (l_wing * (1.0 + 1.0 / geom.eta_wing))
        bk_wing = b0_wing / geom.eta_wing
        project.add_trace(
            value_name="wing_root_chord",
            formula=r"b_{0,wing} = \frac{2S_{wing}}{l_{wing}\left(1 + \frac{1}{\eta_{wing}}\right)}",
            values={"S_wing": S_wing, "l_wing": l_wing, "eta_wing": geom.eta_wing},
            result=float(b0_wing), unit="m", description="Корневая хорда крыла."
        )
        project.add_trace(
            value_name="wing_tip_chord",
            formula=r"b_{k,wing} = \frac{b_{0,wing}}{\eta_{wing}}",
            values={"b0_wing": b0_wing, "eta_wing": geom.eta_wing},
            result=float(bk_wing), unit="m", description="Концевая хорда крыла."
        )

        sweep_wing_LE = self._calc_le_sweep(geom.sweep_wing_quarter, b0_wing, bk_wing, l_wing)
        project.add_trace(
            value_name="wing_le_sweep",
            formula=r"\chi_{LE} = \arctan\left(\tan(\chi_{1/4}) + \frac{b_0 - b_k}{2l}\right)",
            values={"sweep_wing_quarter": geom.sweep_wing_quarter, "b0_wing": b0_wing, "bk_wing": bk_wing,
                    "l_wing": l_wing},
            result=float(sweep_wing_LE), unit="deg", description="Стреловидность крыла по передней кромке."
        )

        # === Фюзеляж (Fuselage) ===
        L_fuselage = geom.k_fuselage * l_wing
        d_fuselage = L_fuselage / geom.lambda_fuselage
        r_fuselage = d_fuselage / 2.0

        project.add_trace(value_name="fuselage_length", formula=r"L_f = k_f \cdot l_{wing}",
                          values={"k_fuselage": geom.k_fuselage, "l_wing": l_wing}, result=float(L_fuselage), unit="m")
        project.add_trace(value_name="fuselage_diameter", formula=r"d_f = \frac{L_f}{\lambda_f}",
                          values={"L_fuselage": L_fuselage, "lambda_fuselage": geom.lambda_fuselage},
                          result=float(d_fuselage), unit="m")

        if geom.wing_scheme == "high":
            y_wing, wing_scheme_ru = d_fuselage / 2.0, "высокоплан"
        elif geom.wing_scheme == "mid":
            y_wing, wing_scheme_ru = 0.0, "среднеплан"
        else:
            y_wing, wing_scheme_ru = -d_fuselage / 2.0, "низкоплан"

        project.add_trace(
            value_name="wing_vertical_position",
            formula=r"y_{wing} = \begin{cases}\frac{d_f}{2}, & \text{high} \\ 0, & \text{mid} \\ -\frac{d_f}{2}, & \text{low}\end{cases}",
            values={"wing_scheme": geom.wing_scheme, "d_fuselage": d_fuselage},
            result=float(y_wing), unit="m"
        )

        x_fuselage = -7.0

        # === Горизонтальное оперение (Horizontal Tail) ===
        S_ht = geom.k_horizontal_tail * S_wing
        l_ht = math.sqrt(S_ht * geom.lambda_horizontal_tail)
        b0_ht = (2.0 * S_ht) / (l_ht * (1.0 + 1.0 / geom.eta_horizontal_tail))
        bk_ht = b0_ht / geom.eta_horizontal_tail

        project.add_trace(value_name="horizontal_tail_area", formula=r"S_{ht} = k_{ht} \cdot S_{wing}",
                          values={"k_horizontal_tail": geom.k_horizontal_tail, "S_wing": S_wing}, result=float(S_ht),
                          unit="m²")
        project.add_trace(value_name="horizontal_tail_span", formula=r"l_{ht} = \sqrt{S_{ht} \cdot \lambda_{ht}}",
                          values={"S_ht": S_ht, "lambda_horizontal_tail": geom.lambda_horizontal_tail},
                          result=float(l_ht), unit="m")

        sweep_ht_LE = self._calc_le_sweep(geom.sweep_horizontal_tail_quarter, b0_ht, bk_ht, l_ht)

        x_ht = x_fuselage + 0.75 * L_fuselage
        y_ht = 0.0

        # === Вертикальное оперение (Vertical Tail) ===
        S_vt = geom.k_vertical_tail * S_wing
        l_vt = math.sqrt(S_vt * geom.lambda_vertical_tail)
        b0_vt = (2.0 * S_vt) / (l_vt * (1.0 + 1.0 / geom.eta_vertical_tail))
        bk_vt = b0_vt / geom.eta_vertical_tail

        project.add_trace(value_name="vertical_tail_area", formula=r"S_{vt} = k_{vt} \cdot S_{wing}",
                          values={"k_vertical_tail": geom.k_vertical_tail, "S_wing": S_wing}, result=float(S_vt),
                          unit="m²")
        project.add_trace(value_name="vertical_tail_span", formula=r"l_{vt} = \sqrt{S_{vt} \cdot \lambda_{vt}}",
                          values={"S_vt": S_vt, "lambda_vertical_tail": geom.lambda_vertical_tail}, result=float(l_vt),
                          unit="m")

        sweep_vt_LE = self._calc_le_sweep(geom.sweep_vertical_tail_quarter, b0_vt, bk_vt, l_vt)

        x_vt = x_fuselage + 0.75 * L_fuselage

        # === Запись результатов обратно в проект ===
        geom.l_wing = float(l_wing)
        geom.b0_wing = float(b0_wing)
        geom.bk_wing = float(bk_wing)
        geom.sweep_wing_LE = float(sweep_wing_LE)
        geom.wing_scheme_ru = wing_scheme_ru
        geom.y_wing = float(y_wing)

        geom.L_fuselage = float(L_fuselage)
        geom.d_fuselage = float(d_fuselage)
        geom.r_fuselage = float(r_fuselage)
        geom.x_fuselage = float(x_fuselage)

        geom.S_ht = float(S_ht)
        geom.l_ht = float(l_ht)
        geom.b0_ht = float(b0_ht)
        geom.bk_ht = float(bk_ht)
        geom.sweep_ht_LE = float(sweep_ht_LE)
        geom.x_ht = float(x_ht)
        geom.y_ht = float(y_ht)

        geom.S_vt = float(S_vt)
        geom.l_vt = float(l_vt)
        geom.b0_vt = float(b0_vt)
        geom.bk_vt = float(bk_vt)
        geom.sweep_vt_LE = float(sweep_vt_LE)
        geom.x_vt = float(x_vt)

    @staticmethod
    def _calc_le_sweep(sweep_quarter_deg: float, root_chord: float, tip_chord: float, span: float) -> float:
        """Переводит стреловидность по 1/4 хорды в стреловидность по передней кромке."""
        sweep_quarter_rad = math.radians(sweep_quarter_deg)
        sweep_le_rad = math.atan(
            math.tan(sweep_quarter_rad) + (root_chord - tip_chord) / (2.0 * span)
        )
        return math.degrees(sweep_le_rad)