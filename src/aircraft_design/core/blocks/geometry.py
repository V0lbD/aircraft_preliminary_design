from __future__ import annotations

import logging
import math
from typing import Any

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import BlockInputSchema, CalculationState, ParameterSpec

logger = logging.getLogger(__name__)


class GeometryBlock(BaseBlock):
    """
    Geometry calculation block.

    Ported from old core/block_geometry.py.

    The block uses:
    - mass_estimation.S_W
    - preliminary_sizing.Lambda

    Formula cleanup and geometry model improvements should be done later
    in separate commits.
    """

    name = "geometry"
    required_input_sections = ("geometry",)

    input_schema = BlockInputSchema(
        section_name="geometry",
        block_name="geometry",
        display_name="Геометрия",
        description="Исходные параметры для расчёта геометрии крыла, фюзеляжа и оперения.",
        parameters=(
            ParameterSpec(
                name="eta_wing",
                value_type="number",
                display_name="Сужение крыла",
                description="Отношение корневой хорды крыла к концевой.",
                required=False,
                default=2.5,
                min_value=0,
                group="wing",
            ),
            ParameterSpec(
                name="sweep_wing_quarter",
                value_type="number",
                display_name="Стреловидность крыла по 1/4 хорды",
                description="Угол стреловидности крыла по линии 1/4 хорды.",
                unit="deg",
                required=False,
                default=25.0,
                group="wing",
            ),
            ParameterSpec(
                name="wing_scheme",
                value_type="string",
                display_name="Схема крыла",
                description="Положение крыла относительно фюзеляжа.",
                required=False,
                default="mid",
                choices=("low", "mid", "high"),
                group="wing",
            ),
            ParameterSpec(
                name="k_horizontal_tail",
                value_type="number",
                display_name="Коэффициент площади ГО",
                description="Отношение площади горизонтального оперения к площади крыла.",
                required=False,
                default=0.25,
                min_value=0,
                group="horizontal_tail",
            ),
            ParameterSpec(
                name="lambda_horizontal_tail",
                value_type="number",
                display_name="Удлинение ГО",
                description="Удлинение горизонтального оперения.",
                required=False,
                default=4.0,
                min_value=0,
                group="horizontal_tail",
            ),
            ParameterSpec(
                name="eta_horizontal_tail",
                value_type="number",
                display_name="Сужение ГО",
                description="Сужение горизонтального оперения.",
                required=False,
                default=3.0,
                min_value=0,
                group="horizontal_tail",
            ),
            ParameterSpec(
                name="sweep_horizontal_tail_quarter",
                value_type="number",
                display_name="Стреловидность ГО по 1/4 хорды",
                description="Угол стреловидности горизонтального оперения по 1/4 хорды.",
                unit="deg",
                required=False,
                default=30.0,
                group="horizontal_tail",
            ),
            ParameterSpec(
                name="k_vertical_tail",
                value_type="number",
                display_name="Коэффициент площади ВО",
                description="Отношение площади вертикального оперения к площади крыла.",
                required=False,
                default=0.15,
                min_value=0,
                group="vertical_tail",
            ),
            ParameterSpec(
                name="lambda_vertical_tail",
                value_type="number",
                display_name="Удлинение ВО",
                description="Удлинение вертикального оперения.",
                required=False,
                default=1.5,
                min_value=0,
                group="vertical_tail",
            ),
            ParameterSpec(
                name="eta_vertical_tail",
                value_type="number",
                display_name="Сужение ВО",
                description="Сужение вертикального оперения.",
                required=False,
                default=2.0,
                min_value=0,
                group="vertical_tail",
            ),
            ParameterSpec(
                name="sweep_vertical_tail_quarter",
                value_type="number",
                display_name="Стреловидность ВО по 1/4 хорды",
                description="Угол стреловидности вертикального оперения по 1/4 хорды.",
                unit="deg",
                required=False,
                default=35.0,
                group="vertical_tail",
            ),
            ParameterSpec(
                name="k_fuselage",
                value_type="number",
                display_name="Коэффициент длины фюзеляжа",
                description="Коэффициент для оценки длины фюзеляжа через размах крыла.",
                required=False,
                default=1.2,
                min_value=0,
                group="fuselage",
            ),
            ParameterSpec(
                name="lambda_fuselage",
                value_type="number",
                display_name="Удлинение фюзеляжа",
                description="Отношение длины фюзеляжа к диаметру.",
                required=False,
                default=9.0,
                min_value=0,
                group="fuselage",
            ),
        ),
    )

    default_values: dict[str, Any] = {
        # Wing
        "eta_wing": 2.5,
        "sweep_wing_quarter": 25.0,
        "wing_scheme": "low",

        # Horizontal tail
        "k_horizontal_tail": 0.25,
        "lambda_horizontal_tail": 4.0,
        "eta_horizontal_tail": 3.0,
        "sweep_horizontal_tail_quarter": 30.0,

        # Vertical tail
        "k_vertical_tail": 0.15,
        "lambda_vertical_tail": 1.5,
        "eta_vertical_tail": 2.0,
        "sweep_vertical_tail_quarter": 35.0,

        # Fuselage
        "k_fuselage": 1.2,
        "lambda_fuselage": 9.0,
    }

    positive_fields: tuple[str, ...] = (
        "eta_wing",
        "k_horizontal_tail",
        "lambda_horizontal_tail",
        "eta_horizontal_tail",
        "k_vertical_tail",
        "lambda_vertical_tail",
        "eta_vertical_tail",
        "k_fuselage",
        "lambda_fuselage",
    )

    allowed_wing_schemes: tuple[str, ...] = ("low", "mid", "high")

    def validate(self, state: CalculationState) -> None:
        super().validate(state)

        if "mass_estimation" not in state.data:
            raise InputValidationError(
                "Geometry block requires mass_estimation block results."
            )

        mass_outputs = state.data["mass_estimation"]

        if "S_W" not in mass_outputs:
            raise InputValidationError(
                "Geometry block requires mass_estimation.S_W."
            )

        S_wing = mass_outputs["S_W"]

        if not isinstance(S_wing, int | float) or S_wing <= 0:
            raise InputValidationError(
                f"mass_estimation.S_W must be positive. Got: {S_wing}"
            )

        preliminary_input = state.project_input.preliminary_sizing

        if "Lambda" not in preliminary_input:
            raise InputValidationError(
                "Geometry block requires preliminary_sizing.Lambda."
            )

        lambda_wing = self._get_number(preliminary_input, "Lambda")

        if lambda_wing <= 0:
            raise InputValidationError(
                f"preliminary_sizing.Lambda must be positive. Got: {lambda_wing}"
            )

        geometry_input = state.project_input.geometry

        values = self._build_values(geometry_input)

        for field_name in self.positive_fields:
            value = self._get_number(values, field_name)
            if value <= 0:
                raise InputValidationError(
                    f"geometry.{field_name} must be positive. Got: {value}"
                )

        wing_scheme = values["wing_scheme"]

        if wing_scheme not in self.allowed_wing_schemes:
            raise InputValidationError(
                "geometry.wing_scheme must be one of "
                f"{self.allowed_wing_schemes}. Got: {wing_scheme!r}"
            )

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        mass_outputs = state.data["mass_estimation"]
        preliminary_input = state.project_input.preliminary_sizing
        geometry_input = state.project_input.geometry

        values = self._build_values(geometry_input)

        S_wing = float(mass_outputs["S_W"])
        lambda_wing = self._get_number(preliminary_input, "Lambda")

        logger.debug("S_wing: %s", S_wing)
        logger.debug("lambda_wing: %s", lambda_wing)

        # === Wing ===
        l_wing = math.sqrt(S_wing * lambda_wing)
        state.add_trace(
            block_name=self.name,
            value_name="l_wing",
            formula="l_wing = sqrt(S_wing * lambda_wing)",
            values={
                "S_wing": S_wing,
                "lambda_wing": lambda_wing,
            },
            result=float(l_wing),
            unit="m",
            description="Wing span from wing area and aspect ratio.",
        )

        eta_wing = self._get_number(values, "eta_wing")
        b0_wing = (2.0 * S_wing) / (l_wing * (1.0 + 1.0 / eta_wing))
        bk_wing = b0_wing / eta_wing
        state.add_trace(
            block_name=self.name,
            value_name="b0_wing",
            formula="b0_wing = 2 * S_wing / (l_wing * (1 + 1 / eta_wing))",
            values={
                "S_wing": S_wing,
                "l_wing": l_wing,
                "eta_wing": eta_wing,
            },
            result=float(b0_wing),
            unit="m",
            description="Wing root chord.",
        )

        state.add_trace(
            block_name=self.name,
            value_name="bk_wing",
            formula="bk_wing = b0_wing / eta_wing",
            values={
                "b0_wing": b0_wing,
                "eta_wing": eta_wing,
            },
            result=float(bk_wing),
            unit="m",
            description="Wing tip chord.",
        )

        sweep_wing_quarter = self._get_number(values, "sweep_wing_quarter")
        sweep_wing_LE = self._calculate_le_sweep_angle(
            sweep_quarter_deg=sweep_wing_quarter,
            root_chord=b0_wing,
            tip_chord=bk_wing,
            span=l_wing,
        )

        # === Fuselage ===
        k_fuselage = self._get_number(values, "k_fuselage")
        lambda_fuselage = self._get_number(values, "lambda_fuselage")

        L_fuselage = k_fuselage * l_wing
        state.add_trace(
            block_name=self.name,
            value_name="L_fuselage",
            formula="L_fuselage = k_fuselage * l_wing",
            values={
                "k_fuselage": k_fuselage,
                "l_wing": l_wing,
            },
            result=float(L_fuselage),
            unit="m",
            description="Fuselage length estimate.",
        )

        d_fuselage = L_fuselage / lambda_fuselage
        r_fuselage = d_fuselage / 2.0

        wing_scheme = values["wing_scheme"]

        if wing_scheme == "high":
            y_wing = d_fuselage / 2.0
            wing_scheme_ru = "высокоплан"
        elif wing_scheme == "mid":
            y_wing = 0.0
            wing_scheme_ru = "среднеплан"
        else:
            y_wing = -d_fuselage / 2.0
            wing_scheme_ru = "низкоплан"

        x_fuselage = -7.0

        # === Horizontal tail ===
        k_horizontal_tail = self._get_number(values, "k_horizontal_tail")
        lambda_horizontal_tail = self._get_number(values, "lambda_horizontal_tail")
        eta_horizontal_tail = self._get_number(values, "eta_horizontal_tail")
        sweep_horizontal_tail_quarter = self._get_number(
            values,
            "sweep_horizontal_tail_quarter",
        )

        S_ht = k_horizontal_tail * S_wing
        l_ht = math.sqrt(S_ht * lambda_horizontal_tail)
        b0_ht = (2.0 * S_ht) / (l_ht * (1.0 + 1.0 / eta_horizontal_tail))
        bk_ht = b0_ht / eta_horizontal_tail

        sweep_ht_LE = self._calculate_le_sweep_angle(
            sweep_quarter_deg=sweep_horizontal_tail_quarter,
            root_chord=b0_ht,
            tip_chord=bk_ht,
            span=l_ht,
        )

        x_ht = x_fuselage + 0.75 * L_fuselage
        y_ht = 0.0

        # === Vertical tail ===
        k_vertical_tail = self._get_number(values, "k_vertical_tail")
        lambda_vertical_tail = self._get_number(values, "lambda_vertical_tail")
        eta_vertical_tail = self._get_number(values, "eta_vertical_tail")
        sweep_vertical_tail_quarter = self._get_number(
            values,
            "sweep_vertical_tail_quarter",
        )

        S_vt = k_vertical_tail * S_wing
        l_vt = math.sqrt(S_vt * lambda_vertical_tail)
        b0_vt = (2.0 * S_vt) / (l_vt * (1.0 + 1.0 / eta_vertical_tail))
        bk_vt = b0_vt / eta_vertical_tail

        sweep_vt_LE = self._calculate_le_sweep_angle(
            sweep_quarter_deg=sweep_vertical_tail_quarter,
            root_chord=b0_vt,
            tip_chord=bk_vt,
            span=l_vt,
        )

        x_vt = x_fuselage + 0.75 * L_fuselage

        return {
            "wing": {
                "S_wing": float(S_wing),
                "lambda_wing": float(lambda_wing),
                "eta_wing": float(eta_wing),
                "l_wing": float(l_wing),
                "b0_wing": float(b0_wing),
                "bk_wing": float(bk_wing),
                "sweep_wing_quarter": float(sweep_wing_quarter),
                "sweep_wing_LE": float(sweep_wing_LE),
                "wing_scheme": wing_scheme,
                "wing_scheme_ru": wing_scheme_ru,
                "y_wing": float(y_wing),
            },
            "fuselage": {
                "L_fuselage": float(L_fuselage),
                "d_fuselage": float(d_fuselage),
                "r_fuselage": float(r_fuselage),
                "x_fuselage": float(x_fuselage),
                "k_fuselage": float(k_fuselage),
                "lambda_fuselage": float(lambda_fuselage),
            },
            "horizontal_tail": {
                "S_ht": float(S_ht),
                "lambda_horizontal_tail": float(lambda_horizontal_tail),
                "eta_horizontal_tail": float(eta_horizontal_tail),
                "l_ht": float(l_ht),
                "b0_ht": float(b0_ht),
                "bk_ht": float(bk_ht),
                "sweep_horizontal_tail_quarter": float(sweep_horizontal_tail_quarter),
                "sweep_ht_LE": float(sweep_ht_LE),
                "x_ht": float(x_ht),
                "y_ht": float(y_ht),
            },
            "vertical_tail": {
                "S_vt": float(S_vt),
                "lambda_vertical_tail": float(lambda_vertical_tail),
                "eta_vertical_tail": float(eta_vertical_tail),
                "l_vt": float(l_vt),
                "b0_vt": float(b0_vt),
                "bk_vt": float(bk_vt),
                "sweep_vertical_tail_quarter": float(sweep_vertical_tail_quarter),
                "sweep_vt_LE": float(sweep_vt_LE),
                "x_vt": float(x_vt),
            },
            "inputs_from_mass_estimation": {
                "S_W": float(S_wing),
            },
            "inputs_from_preliminary_sizing": {
                "Lambda": float(lambda_wing),
            },
        }

    def _build_values(self, geometry_input: dict[str, Any]) -> dict[str, Any]:
        values = dict(self.default_values)

        for key in values:
            if key in geometry_input and geometry_input[key] is not None:
                values[key] = geometry_input[key]

        return values

    @staticmethod
    def _calculate_le_sweep_angle(
        sweep_quarter_deg: float,
        root_chord: float,
        tip_chord: float,
        span: float,
    ) -> float:
        sweep_quarter_rad = math.radians(sweep_quarter_deg)

        sweep_le_rad = math.atan(
            math.tan(sweep_quarter_rad)
            + (root_chord - tip_chord) / (2.0 * span)
        )

        return math.degrees(sweep_le_rad)

    @staticmethod
    def _get_number(section: dict[str, Any], field_name: str) -> float:
        value = section[field_name]

        if isinstance(value, bool):
            raise InputValidationError(
                f"{field_name} must be a number, not bool."
            )

        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(
                f"{field_name} must be a number. Got: {value!r}"
            ) from exc