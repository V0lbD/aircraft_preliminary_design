from __future__ import annotations

import logging
from typing import Any

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.mass_components import (
    ENGINE_CHOICES,
    ENGINE_PISTON,
    GEAR_FAIRING_CHOICES,
    GEAR_FAIRING_NONE,
    GEAR_MATERIAL_CHOICES,
    GEAR_MATERIAL_MEDIUM_STEEL,
    GEAR_TYPE_CHOICES,
    GEAR_TYPE_WHEELED,
    POWERPLANT_CHOICES,
    POWERPLANT_ELECTRIC,
    WING_POSITION_CHOICES,
    WING_POSITION_HIGH,
    calculate_mass_estimation,
)
from aircraft_design.core.models import BlockInputSchema, CalculationState, ParameterSpec

logger = logging.getLogger(__name__)

STANDARD_GRAVITY = 9.80665


class MassEstimationBlock(BaseBlock):
    """Mass estimation block based on the new flowchart formulas."""

    name = "mass_estimation"
    required_input_sections = ("mass_estimation",)

    input_schema = BlockInputSchema(
        section_name="mass_estimation",
        block_name="mass_estimation",
        display_name="Оценка масс",
        description=(
            "Исходные параметры для оценки взлётной массы по новой методике: "
            "электрическая ветка по Духновскому / ДВС-ветка по Бреге, Чумаку "
            "и Бадягину-Мухамедову."
        ),
        parameters=(
            ParameterSpec(
                name="powerplant_type",
                value_type="string",
                display_name="Тип силовой установки",
                description="Выбор основной ветки расчёта масс.",
                required=True,
                default=POWERPLANT_ELECTRIC,
                choices=POWERPLANT_CHOICES,
                group="general",
            ),
            ParameterSpec(
                name="payload_mass",
                value_type="number",
                display_name="mцн",
                description="Масса целевой / полезной нагрузки.",
                unit="kg",
                required=True,
                default=1.0,
                min_value=0,
                group="general",
            ),
            ParameterSpec(
                name="service_load_mass",
                value_type="number",
                display_name="mсл",
                description="Масса служебной нагрузки. Используется в ДВС-ветке.",
                unit="kg",
                required=True,
                default=0.0,
                min_value=0,
                group="general",
            ),
            ParameterSpec(
                name="battery_equipment_mass",
                value_type="number",
                display_name="mакб.обор",
                description="Масса АКБ оборудования. Используется в электрической ветке.",
                unit="kg",
                required=True,
                default=0.0,
                min_value=0,
                group="electric",
            ),
            ParameterSpec(
                name="control_equipment_mass",
                value_type="number",
                display_name="mоб.упр",
                description="Масса оборудования управления. Используется в электрической ветке.",
                unit="kg",
                required=True,
                default=0.0,
                min_value=0,
                group="electric",
            ),
            ParameterSpec(
                name="design_range",
                value_type="number",
                display_name="L",
                description="Расчётная дальность полёта.",
                unit="km",
                required=True,
                default=10.0,
                min_value=0,
                group="mission",
            ),
            ParameterSpec(
                name="cruise_speed",
                value_type="number",
                display_name="Vкр",
                description="Крейсерская скорость.",
                unit="m/s",
                required=True,
                default=20.0,
                min_value=0,
                group="mission",
            ),
            ParameterSpec(
                name="cruise_L_D_ratio",
                value_type="number",
                display_name="K",
                description="Аэродинамическое качество.",
                required=True,
                default=10.0,
                min_value=0,
                group="aerodynamics",
            ),
            ParameterSpec(
                name="is_maneuverable",
                value_type="boolean",
                display_name="Маневренный самолёт",
                description="Влияет на первое приближение массы конструкции / сумму по Чумаку.",
                required=True,
                default=False,
                group="general",
            ),
            ParameterSpec(
                name="is_under_2_5kg",
                value_type="boolean",
                display_name="m < 2.5 kg",
                description="Выбор коэффициента массы электрической силовой установки.",
                required=True,
                default=False,
                group="electric",
            ),
            ParameterSpec(
                name="battery_specific_energy_wh_kg",
                value_type="number",
                display_name="q",
                description="Удельная энергия АКБ.",
                unit="Wh/kg",
                required=True,
                default=250.0,
                min_value=0,
                group="electric",
            ),
            ParameterSpec(
                name="electric_powertrain_efficiency",
                value_type="number",
                display_name="ηсу",
                description="КПД электрической силовой установки.",
                required=True,
                default=0.8,
                min_value=0,
                max_value=1,
                group="electric",
            ),
            ParameterSpec(
                name="cruise_altitude_m",
                value_type="number",
                display_name="H",
                description="Высота набора / крейсерская высота для формулы АКБ.",
                unit="m",
                required=True,
                default=0.0,
                min_value=0,
                group="electric",
            ),
            ParameterSpec(
                name="power_loading_N0_kw_kg",
                value_type="number",
                display_name="N0",
                description="Энерговооружённость для электрической силовой установки.",
                unit="kW/kg",
                required=True,
                default=0.05,
                min_value=0,
                group="electric",
            ),
            ParameterSpec(
                name="cruise_sfc_power",
                value_type="number",
                display_name="Ce",
                description="Удельный расход топлива для формулы Бреге.",
                unit="kg/(hp*h)",
                required=True,
                default=0.26,
                min_value=0,
                group="ice",
            ),
            ParameterSpec(
                name="propeller_efficiency",
                value_type="number",
                display_name="ηв",
                description="КПД винта для ДВС-ветки.",
                required=True,
                default=0.8,
                min_value=0,
                max_value=1,
                group="ice",
            ),
            ParameterSpec(
                name="engine_count",
                value_type="integer",
                display_name="nдв",
                description="Количество двигателей.",
                required=True,
                default=1,
                min_value=1,
                group="ice",
            ),
            ParameterSpec(
                name="engine_type",
                value_type="string",
                display_name="Тип двигателя",
                description="Тип ДВС для расчёта массы силовой установки.",
                required=True,
                default=ENGINE_PISTON,
                choices=ENGINE_CHOICES,
                group="ice",
            ),
            ParameterSpec(
                name="takeoff_power_hp",
                value_type="number",
                display_name="Ne взл",
                description="Взлётная мощность одного двигателя.",
                unit="hp",
                required=True,
                default=1.0,
                min_value=0,
                group="ice",
            ),
            ParameterSpec(
                name="wing_area_m2",
                value_type="number",
                display_name="Sкр",
                description="Площадь крыла для итерационного расчёта масс.",
                unit="m²",
                required=True,
                default=0.5,
                min_value=0,
                group="structure_wing",
            ),
            ParameterSpec(
                name="horizontal_tail_area_m2",
                value_type="number",
                display_name="Sго",
                description="Площадь горизонтального оперения.",
                unit="m²",
                required=True,
                default=0.05,
                min_value=0,
                group="structure_tail",
            ),
            ParameterSpec(
                name="vertical_tail_area_m2",
                value_type="number",
                display_name="Sво",
                description="Площадь вертикального оперения.",
                unit="m²",
                required=True,
                default=0.03,
                min_value=0,
                group="structure_tail",
            ),
            ParameterSpec(
                name="wing_aspect_ratio",
                value_type="number",
                display_name="λ",
                description="Удлинение крыла.",
                required=True,
                default=8.0,
                min_value=0,
                group="structure_wing",
            ),
            ParameterSpec(
                name="wing_taper_ratio",
                value_type="number",
                display_name="η",
                description="Сужение крыла.",
                required=True,
                default=2.0,
                min_value=0,
                group="structure_wing",
            ),
            ParameterSpec(
                name="wing_relative_thickness",
                value_type="number",
                display_name="ε",
                description="Относительная толщина крыла.",
                required=True,
                default=0.12,
                min_value=0.02,
                max_value=0.2,
                group="structure_wing",
            ),
            ParameterSpec(
                name="ultimate_load_factor",
                value_type="number",
                display_name="ny",
                description="Расчётная перегрузка.",
                required=True,
                default=3.0,
                min_value=0,
                group="structure_wing",
            ),
            ParameterSpec(
                name="f_factor",
                value_type="number",
                display_name="f",
                description="Коэффициент f из формулы массы крыла.",
                required=True,
                default=2.0,
                min_value=1.5,
                max_value=3.0,
                group="structure_wing",
            ),
            ParameterSpec(
                name="wing_material_factor",
                value_type="number",
                display_name="km",
                description="Коэффициент материала крыла.",
                required=True,
                default=1.0,
                min_value=0,
                group="structure_wing",
            ),
            ParameterSpec(
                name="wing_position",
                value_type="string",
                display_name="Положение крыла",
                description="Высокоплан или низкоплан.",
                required=True,
                default=WING_POSITION_HIGH,
                choices=WING_POSITION_CHOICES,
                group="structure_fuselage",
            ),
            ParameterSpec(
                name="has_landing_gear",
                value_type="boolean",
                display_name="Есть ли шасси",
                description="Если нет, относительная масса шасси равна нулю.",
                required=True,
                default=True,
                group="structure_landing_gear",
            ),
            ParameterSpec(
                name="landing_gear_material",
                value_type="string",
                display_name="Материал шасси",
                description="Материал шасси для коэффициента kкон.",
                required=True,
                default=GEAR_MATERIAL_MEDIUM_STEEL,
                choices=GEAR_MATERIAL_CHOICES,
                group="structure_landing_gear",
            ),
            ParameterSpec(
                name="landing_gear_fairing",
                value_type="string",
                display_name="Обтекатель шасси",
                description="Нет / на колёса / убираемое шасси.",
                required=True,
                default=GEAR_FAIRING_NONE,
                choices=GEAR_FAIRING_CHOICES,
                group="structure_landing_gear",
            ),
            ParameterSpec(
                name="landing_gear_type",
                value_type="string",
                display_name="Тип шасси",
                description="Лыжное или колёсное.",
                required=True,
                default=GEAR_TYPE_WHEELED,
                choices=GEAR_TYPE_CHOICES,
                group="structure_landing_gear",
            ),
            ParameterSpec(
                name="has_brakes",
                value_type="boolean",
                display_name="Есть ли тормоза",
                description="Используется для колёсного шасси.",
                required=True,
                default=True,
                group="structure_landing_gear",
            ),
            ParameterSpec(
                name="landing_gear_strut_length_m",
                value_type="number",
                display_name="Hош",
                description="Высота основной стойки шасси.",
                unit="m",
                required=True,
                default=0.2,
                min_value=0,
                group="structure_landing_gear",
            ),
            ParameterSpec(
                name="wing_loading_tolerance",
                value_type="number",
                display_name="Допуск изменения p0",
                description="Критерий завершения итераций по изменению нагрузки на крыло.",
                required=True,
                default=0.10,
                min_value=0,
                group="iteration",
            ),
            ParameterSpec(
                name="max_iterations",
                value_type="integer",
                display_name="Максимум итераций",
                description="Защита от бесконечного цикла уточнения массы.",
                required=True,
                default=30,
                min_value=1,
                group="iteration",
            ),
        ),
    )

    def validate(self, state: CalculationState) -> None:
        super().validate(state)
        section = state.project_input.mass_estimation
        if section["powerplant_type"] not in POWERPLANT_CHOICES:
            raise InputValidationError(
                "mass_estimation.powerplant_type must be one of "
                f"{POWERPLANT_CHOICES}. Got {section['powerplant_type']!r}."
            )

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        section = state.project_input.mass_estimation
        iteration_result = calculate_mass_estimation(
            section,
            trace=state.trace,
            block_name=self.name,
        )
        breakdown = iteration_result.breakdown
        final_m0 = iteration_result.final_m0
        final_wing_area = iteration_result.final_wing_area
        m_fuel = breakdown.fuel
        m_operating_empty = breakdown.operating_empty_mass
        m_oe_ratio = m_operating_empty / final_m0
        m_f_ratio = m_fuel / final_m0
        useful_load_ratio = (breakdown.payload + breakdown.service_load + m_fuel) / final_m0

        preliminary_outputs = state.data.get("preliminary_sizing", {})
        p0_optimal = _optional_number(preliminary_outputs, "p0_optimal")
        P0_optimal = _optional_number(preliminary_outputs, "P0_optimal")
        if P0_optimal is not None and P0_optimal > 0:
            t_to = final_m0 * STANDARD_GRAVITY * P0_optimal
            state.add_trace(
                block_name=self.name,
                value_name="T_TO",
                formula=r"T_{TO}=m_0gP_{0,opt}",
                values={
                    "m0": final_m0,
                    "g": STANDARD_GRAVITY,
                    "P0_optimal": P0_optimal,
                },
                result=float(t_to),
                unit="N",
                description="Взлётная тяга из блока предварительного расчёта.",
            )
        else:
            t_to = 0.0
            state.warnings.append(
                "preliminary_sizing.P0_optimal is missing or non-positive; T_TO was set to 0."
            )

        state.add_trace(
            block_name=self.name,
            value_name="S_W",
            formula=r"S_W=S_{кр,final}",
            values={"final_wing_area": final_wing_area},
            result=float(final_wing_area),
            unit="m²",
            description="Площадь крыла, сохранённая в старом выходном поле для блока геометрии.",
        )

        if not iteration_result.converged:
            state.warnings.append(
                "Mass iteration did not converge after "
                f"{iteration_result.max_iterations} iterations. "
                "The last calculated mass was returned."
            )

        return {
            "m_MTO": float(final_m0),
            "m_OE": float(m_operating_empty),
            "m_F": float(m_fuel),
            "T_TO": float(t_to),
            "S_W": float(final_wing_area),
            "m_OE_ratio": float(m_oe_ratio),
            "m_F_ratio": float(m_f_ratio),
            "useful_load_ratio": float(useful_load_ratio),
            "powerplant_type": iteration_result.powerplant_type,
            "converged": iteration_result.converged,
            "iterations": iteration_result.iterations,
            "wing_loading_relative_delta": float(
                iteration_result.relative_delta_wing_loading
            ),
            "structure_mass_ratio": float(iteration_result.structure_ratios.total),
            "component_masses": breakdown.to_dict(),
            "component_mass_iteration": iteration_result.to_dict(),
            "mass_ratios": {
                **iteration_result.final_ratios,
                "operating_empty_mass_ratio": float(m_oe_ratio),
                "fuel_mass_ratio": float(m_f_ratio),
            },
            "inputs_from_preliminary_sizing": {
                "p0_optimal": p0_optimal,
                "P0_optimal": P0_optimal,
            },
        }


def _optional_number(section: dict[str, Any], field_name: str) -> float | None:
    value = section.get(field_name)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
