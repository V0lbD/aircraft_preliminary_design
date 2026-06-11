from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import CalculationTrace

STANDARD_GRAVITY = 9.80665
HP_TO_WATT = 735.5

POWERPLANT_ELECTRIC = "electric"
POWERPLANT_ICE = "ice"
POWERPLANT_CHOICES = (POWERPLANT_ELECTRIC, POWERPLANT_ICE)

ENGINE_PISTON = "piston"
ENGINE_TURBOPROP = "turboprop"
ENGINE_CHOICES = (ENGINE_PISTON, ENGINE_TURBOPROP)

WING_POSITION_HIGH = "high"
WING_POSITION_LOW = "low"
WING_POSITION_CHOICES = (WING_POSITION_HIGH, WING_POSITION_LOW)

GEAR_TYPE_SKI = "ski"
GEAR_TYPE_WHEELED = "wheeled"
GEAR_TYPE_CHOICES = (GEAR_TYPE_SKI, GEAR_TYPE_WHEELED)

GEAR_MATERIAL_MEDIUM_STEEL = "medium_steel"
GEAR_MATERIAL_HIGH_STRENGTH = "high_strength_metal"
GEAR_MATERIAL_CHOICES = (GEAR_MATERIAL_MEDIUM_STEEL, GEAR_MATERIAL_HIGH_STRENGTH)

GEAR_FAIRING_NONE = "none"
GEAR_FAIRING_WHEELS = "wheel_fairings"
GEAR_FAIRING_RETRACTABLE = "retractable"
GEAR_FAIRING_CHOICES = (GEAR_FAIRING_NONE, GEAR_FAIRING_WHEELS, GEAR_FAIRING_RETRACTABLE)

# Compatibility names for old imports/tests. The new code uses POWERPLANT_* and ENGINE_*.
ENGINE_ELECTRIC = POWERPLANT_ELECTRIC
ENGINE_PISTON_AIR = ENGINE_PISTON
ENGINE_PISTON_LIQUID = ENGINE_PISTON
GEAR_NONE = "none"
GEAR_SKI = GEAR_TYPE_SKI
GEAR_WHEELED_BRAKED = "wheeled_braked"
GEAR_WHEELED_UNBRAKED = "wheeled_unbraked"


@dataclass(slots=True)
class StructureMassRatios:
    wing: float
    fuselage: float
    tail: float
    landing_gear: float

    @property
    def total(self) -> float:
        return self.wing + self.fuselage + self.tail + self.landing_gear

    def to_dict(self) -> dict[str, float]:
        data = asdict(self)
        data["total"] = self.total
        return data


@dataclass(slots=True)
class MassBreakdown:
    payload: float
    service_load: float
    fuel: float
    battery_energy: float
    battery_equipment: float
    control_equipment: float
    structure: float
    wing: float
    fuselage: float
    tail: float
    landing_gear: float
    powerplant: float
    special_equipment: float

    @property
    def operating_empty_mass(self) -> float:
        return (
            self.battery_energy
            + self.battery_equipment
            + self.control_equipment
            + self.structure
            + self.powerplant
            + self.special_equipment
        )

    @property
    def useful_load_mass(self) -> float:
        return self.payload + self.service_load

    @property
    def total_mass(self) -> float:
        return self.useful_load_mass + self.fuel + self.operating_empty_mass

    def to_dict(self) -> dict[str, float]:
        data = asdict(self)
        data["operating_empty_mass"] = self.operating_empty_mass
        data["useful_load_mass"] = self.useful_load_mass
        data["total_mass"] = self.total_mass
        return data


@dataclass(slots=True)
class MassIterationResult:
    powerplant_type: str
    converged: bool
    iterations: int
    tolerance: float
    max_iterations: int
    initial_m0: float
    final_m0: float
    initial_wing_area: float
    final_wing_area: float
    relative_delta_wing_loading: float
    initial_ratios: dict[str, float]
    final_ratios: dict[str, float]
    structure_ratios: StructureMassRatios
    breakdown: MassBreakdown
    history: list[dict[str, float]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "powerplant_type": self.powerplant_type,
            "converged": self.converged,
            "iterations": self.iterations,
            "tolerance": self.tolerance,
            "max_iterations": self.max_iterations,
            "initial_m0": self.initial_m0,
            "final_m0": self.final_m0,
            "initial_wing_area": self.initial_wing_area,
            "final_wing_area": self.final_wing_area,
            "relative_delta_wing_loading": self.relative_delta_wing_loading,
            "initial_ratios": self.initial_ratios,
            "final_ratios": self.final_ratios,
            "structure_ratios": self.structure_ratios.to_dict(),
            "breakdown": self.breakdown.to_dict(),
            "history": self.history,
        }


def calculate_mass_estimation(
    mass_input: dict[str, Any],
    *,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
) -> MassIterationResult:
    """Run the new mass estimation algorithm reconstructed from the flowchart."""

    powerplant_type = str(mass_input["powerplant_type"])
    if powerplant_type == POWERPLANT_ELECTRIC:
        return calculate_electric_mass_estimation(
            mass_input, trace=trace, block_name=block_name
        )
    if powerplant_type == POWERPLANT_ICE:
        return calculate_ice_mass_estimation(mass_input, trace=trace, block_name=block_name)
    raise InputValidationError(
        f"Unknown mass_estimation.powerplant_type: {powerplant_type!r}"
    )


def calculate_electric_mass_estimation(
    mass_input: dict[str, Any],
    *,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
) -> MassIterationResult:
    payload_mass = _positive(mass_input, "payload_mass")
    battery_equipment_mass = _non_negative(mass_input, "battery_equipment_mass")
    control_equipment_mass = _non_negative(mass_input, "control_equipment_mass")
    numerator = payload_mass + battery_equipment_mass + control_equipment_mass

    battery_ratio = calculate_battery_mass_ratio(
        design_range_km=_non_negative(mass_input, "design_range"),
        cruise_l_d_ratio=_positive(mass_input, "cruise_L_D_ratio"),
        cruise_altitude_m=_non_negative(mass_input, "cruise_altitude_m"),
        cruise_speed_m_s=_positive(mass_input, "cruise_speed"),
        battery_specific_energy_wh_kg=_positive(
            mass_input, "battery_specific_energy_wh_kg"
        ),
        electric_powertrain_efficiency=_positive(
            mass_input, "electric_powertrain_efficiency"
        ),
        trace=trace,
        block_name=block_name,
    )
    powerplant_ratio = calculate_electric_powerplant_mass_ratio(
        power_loading_n0_kw_kg=_non_negative(mass_input, "power_loading_N0_kw_kg"),
        is_under_2_5kg=bool(mass_input["is_under_2_5kg"]),
        trace=trace,
        block_name=block_name,
    )
    initial_structure_ratio = 0.33 if bool(mass_input["is_maneuverable"]) else 0.30
    _add_trace(
        trace,
        block_name=block_name,
        value_name="initial_structure_mass_ratio",
        formula=(
            r"\bar{m}_{кон,0}=0.33 \quad \text{для маневренного,} "
            r"\quad \bar{m}_{кон,0}=0.30 \quad \text{для неманевренного}"
        ),
        values={"is_maneuverable": bool(mass_input["is_maneuverable"])},
        result=float(initial_structure_ratio),
        description="Первое приближение относительной массы конструкции.",
    )
    initial_denominator = 1.0 - initial_structure_ratio - battery_ratio - powerplant_ratio
    initial_m0 = calculate_takeoff_mass_from_ratios(
        numerator=numerator,
        denominator=initial_denominator,
        trace=trace,
        block_name=block_name,
        value_name="electric_initial_m0",
        formula=(
            r"m_{0,1}=\frac{m_{цн}+m_{акб.обор}+m_{об.упр}}"
            r"{1-\bar{m}_{кон,0}-\bar{m}_{акб}-\bar{m}_{с.у}}"
        ),
        values={
            "payload_mass": payload_mass,
            "battery_equipment_mass": battery_equipment_mass,
            "control_equipment_mass": control_equipment_mass,
            "initial_structure_ratio": initial_structure_ratio,
            "battery_ratio": battery_ratio,
            "powerplant_ratio": powerplant_ratio,
            "denominator": initial_denominator,
        },
    )
    return _iterate_structure_and_mass(
        mass_input=mass_input,
        powerplant_type=POWERPLANT_ELECTRIC,
        initial_m0=initial_m0,
        numerator=numerator,
        fixed_ratios={
            "battery_mass_ratio": battery_ratio,
            "powerplant_mass_ratio": powerplant_ratio,
        },
        trace=trace,
        block_name=block_name,
        initial_ratios={
            "initial_structure_mass_ratio": initial_structure_ratio,
            "battery_mass_ratio": battery_ratio,
            "powerplant_mass_ratio": powerplant_ratio,
        },
    )


def calculate_ice_mass_estimation(
    mass_input: dict[str, Any],
    *,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
) -> MassIterationResult:
    payload_mass = _positive(mass_input, "payload_mass")
    service_load_mass = _non_negative(mass_input, "service_load_mass")
    numerator = payload_mass + service_load_mass

    fuel_ratio = calculate_breguet_fuel_mass_ratio(
        design_range_km=_non_negative(mass_input, "design_range"),
        cruise_sfc_power=_positive(mass_input, "cruise_sfc_power"),
        cruise_l_d_ratio=_positive(mass_input, "cruise_L_D_ratio"),
        propeller_efficiency=_positive(mass_input, "propeller_efficiency"),
        trace=trace,
        block_name=block_name,
    )
    chumak_total_ratio = 0.60 if bool(mass_input["is_maneuverable"]) else 0.61
    _add_trace(
        trace,
        block_name=block_name,
        value_name="chumak_initial_mass_ratio_sum",
        formula=(
            r"\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН}=0.60 "
            r"\; \text{или} \; 0.61"
        ),
        values={"is_maneuverable": bool(mass_input["is_maneuverable"])},
        result=float(chumak_total_ratio),
        description="Первое приближение суммы относительных масс по Чумаку.",
    )
    initial_denominator = 1.0 - chumak_total_ratio - fuel_ratio
    initial_m0 = calculate_takeoff_mass_from_ratios(
        numerator=numerator,
        denominator=initial_denominator,
        trace=trace,
        block_name=block_name,
        value_name="ice_initial_m0",
        formula=(
            r"m_{0,1}=\frac{m_{цн}+m_{сл}}"
            r"{1-(\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН}+\bar{m}_{т})}"
        ),
        values={
            "payload_mass": payload_mass,
            "service_load_mass": service_load_mass,
            "chumak_total_ratio": chumak_total_ratio,
            "fuel_ratio": fuel_ratio,
            "denominator": initial_denominator,
        },
    )
    special_equipment_ratio = calculate_special_equipment_mass_ratio(
        engine_count=_positive_int(mass_input, "engine_count"),
        trace=trace,
        block_name=block_name,
    )
    return _iterate_structure_and_mass(
        mass_input=mass_input,
        powerplant_type=POWERPLANT_ICE,
        initial_m0=initial_m0,
        numerator=numerator,
        fixed_ratios={
            "fuel_mass_ratio": fuel_ratio,
            "special_equipment_mass_ratio": special_equipment_ratio,
        },
        trace=trace,
        block_name=block_name,
        initial_ratios={
            "fuel_mass_ratio": fuel_ratio,
            "chumak_total_ratio": chumak_total_ratio,
            "special_equipment_mass_ratio": special_equipment_ratio,
        },
    )


def calculate_battery_mass_ratio(
    *,
    design_range_km: float,
    cruise_l_d_ratio: float,
    cruise_altitude_m: float,
    cruise_speed_m_s: float,
    battery_specific_energy_wh_kg: float,
    electric_powertrain_efficiency: float,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
) -> float:
    design_range_m = design_range_km * 1000.0
    numerator = STANDARD_GRAVITY * (
        cruise_altitude_m
        + (0.5 * cruise_speed_m_s**2) / STANDARD_GRAVITY
        + design_range_m / cruise_l_d_ratio
    )
    denominator = 3600.0 * battery_specific_energy_wh_kg * electric_powertrain_efficiency
    ratio = numerator / denominator
    _add_trace(
        trace,
        block_name=block_name,
        value_name="battery_mass_ratio",
        formula=(
            r"\bar{m}_{акб}=\frac{g\left(H+\frac{0.5V_{кр}^{2}}{g}+\frac{L}{K}\right)}"
            r"{3600q\eta_{су}}"
        ),
        values={
            "g": STANDARD_GRAVITY,
            "H": cruise_altitude_m,
            "V_cruise": cruise_speed_m_s,
            "L_m": design_range_m,
            "K": cruise_l_d_ratio,
            "q": battery_specific_energy_wh_kg,
            "eta_su": electric_powertrain_efficiency,
        },
        result=float(ratio),
        description="Относительная масса АКБ по Духновскому.",
    )
    return ratio


def calculate_electric_powerplant_mass_ratio(
    *,
    power_loading_n0_kw_kg: float,
    is_under_2_5kg: bool,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
) -> float:
    coefficient = 0.3491 if is_under_2_5kg else 0.4695
    ratio = coefficient * power_loading_n0_kw_kg
    _add_trace(
        trace,
        block_name=block_name,
        value_name="electric_powerplant_mass_ratio",
        formula=r"\bar{m}_{с.у}=C_{с.у}\bar{N}_{0}",
        values={
            "is_under_2_5kg": is_under_2_5kg,
            "coefficient": coefficient,
            "N0_kw_kg": power_loading_n0_kw_kg,
        },
        result=float(ratio),
        description="Относительная масса электрической силовой установки.",
    )
    return ratio


def calculate_breguet_fuel_mass_ratio(
    *,
    design_range_km: float,
    cruise_sfc_power: float,
    cruise_l_d_ratio: float,
    propeller_efficiency: float,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
) -> float:
    exponent = -(
        design_range_km
        * cruise_sfc_power
        * STANDARD_GRAVITY
        / (cruise_l_d_ratio * propeller_efficiency * HP_TO_WATT * 3.6)
    )
    ratio = 1.0 - math.exp(exponent)
    _add_trace(
        trace,
        block_name=block_name,
        value_name="fuel_mass_ratio_breguet",
        formula=(
            r"\bar{m}_{т}=1-\exp\left(-\frac{LC_{e}g}"
            r"{K\eta_{в}\cdot735.5\cdot3.6}\right)"
        ),
        values={
            "L_km": design_range_km,
            "C_e": cruise_sfc_power,
            "g": STANDARD_GRAVITY,
            "K": cruise_l_d_ratio,
            "eta_v": propeller_efficiency,
            "hp_to_watt": HP_TO_WATT,
        },
        result=float(ratio),
        description="Относительная масса топлива по Бреге.",
    )
    return ratio


def calculate_special_equipment_mass_ratio(
    *,
    engine_count: int,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
) -> float:
    ratio = 0.08 if engine_count == 1 else 0.11
    _add_trace(
        trace,
        block_name=block_name,
        value_name="special_equipment_mass_ratio",
        formula=(
            r"\bar{m}_{об.СН}=0.08 \; (n_{дв}=1), \quad "
            r"\bar{m}_{об.СН}=0.11 \; (n_{дв}>1)"
        ),
        values={"engine_count": engine_count},
        result=float(ratio),
        description="Относительная масса оборудования СН.",
    )
    return ratio


def calculate_ice_powerplant_mass_ratio(
    *,
    m0: float,
    engine_count: int,
    engine_type: str,
    takeoff_power_hp: float,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
    iteration: int | None = None,
) -> float:
    if engine_type == ENGINE_PISTON:
        k_n = 0.55
        gamma_engine = 1.0 - 0.012 * math.sqrt(takeoff_power_hp)
    elif engine_type == ENGINE_TURBOPROP:
        k_n = 0.23
        gamma_engine = 0.20
    else:
        raise InputValidationError(f"Unknown engine_type: {engine_type!r}")
    gamma_engine = max(gamma_engine, 0.0)
    powerplant_mass = engine_count * takeoff_power_hp * (gamma_engine + k_n)
    ratio = powerplant_mass / m0
    _add_trace(
        trace,
        block_name=block_name,
        value_name=_iter_name("ice_powerplant_mass_ratio", iteration),
        formula=r"G_{с.у}=N_{дв}N_{e,взл}(\gamma_{дв}+k_N), \quad \bar{m}_{с.у}=G_{с.у}/m_0",
        values={
            "iteration": iteration,
            "m0": m0,
            "engine_count": engine_count,
            "engine_type": engine_type,
            "takeoff_power_hp": takeoff_power_hp,
            "gamma_engine": gamma_engine,
            "k_N": k_n,
            "powerplant_mass": powerplant_mass,
        },
        result=float(ratio),
        description="Относительная масса ДВС-силовой установки по Бадягину и Мухамедову.",
    )
    return ratio


def calculate_takeoff_mass_from_ratios(
    *,
    numerator: float,
    denominator: float,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
    value_name: str,
    formula: str,
    values: dict[str, Any],
) -> float:
    if denominator <= 0:
        raise InputValidationError(
            f"Mass balance denominator must be positive. Got {denominator:.6g}."
        )
    m0 = numerator / denominator
    _add_trace(
        trace,
        block_name=block_name,
        value_name=value_name,
        formula=formula,
        values={**values, "numerator": numerator},
        result=float(m0),
        unit="kg",
        description="Расчёт взлётной массы из баланса относительных масс.",
    )
    return m0


def calculate_structure_mass_ratios(
    *,
    m0: float,
    wing_area_m2: float,
    mass_input: dict[str, Any],
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
    iteration: int | None = None,
) -> StructureMassRatios:
    wing_ratio = calculate_wing_mass_ratio(
        m0=m0,
        wing_area_m2=wing_area_m2,
        wing_aspect_ratio=_positive(mass_input, "wing_aspect_ratio"),
        wing_taper_ratio=_positive(mass_input, "wing_taper_ratio"),
        wing_relative_thickness=_positive(mass_input, "wing_relative_thickness"),
        wing_material_factor=_positive(mass_input, "wing_material_factor"),
        ultimate_load_factor=_positive(mass_input, "ultimate_load_factor"),
        f_factor=_positive(mass_input, "f_factor"),
        trace=trace,
        block_name=block_name,
        iteration=iteration,
    )
    fuselage_ratio = calculate_fuselage_mass_ratio(
        m0=m0,
        wing_position=str(mass_input["wing_position"]),
        trace=trace,
        block_name=block_name,
        iteration=iteration,
    )
    tail_ratio = calculate_tail_mass_ratio(
        m0=m0,
        cruise_speed_m_s=_positive(mass_input, "cruise_speed"),
        horizontal_tail_area_m2=_non_negative(mass_input, "horizontal_tail_area_m2"),
        vertical_tail_area_m2=_non_negative(mass_input, "vertical_tail_area_m2"),
        trace=trace,
        block_name=block_name,
        iteration=iteration,
    )
    gear_ratio = calculate_landing_gear_mass_ratio(
        has_landing_gear=bool(mass_input["has_landing_gear"]),
        landing_gear_material=str(mass_input["landing_gear_material"]),
        landing_gear_fairing=str(mass_input["landing_gear_fairing"]),
        landing_gear_type=str(mass_input["landing_gear_type"]),
        has_brakes=bool(mass_input["has_brakes"]),
        landing_gear_strut_length_m=_non_negative(
            mass_input, "landing_gear_strut_length_m"
        ),
        trace=trace,
        block_name=block_name,
        iteration=iteration,
    )
    ratios = StructureMassRatios(
        wing=wing_ratio,
        fuselage=fuselage_ratio,
        tail=tail_ratio,
        landing_gear=gear_ratio,
    )
    _add_trace(
        trace,
        block_name=block_name,
        value_name=_iter_name("structure_mass_ratio", iteration),
        formula=r"\bar{m}_{к}=\bar{m}_{кр}+\bar{m}_{ф}+\bar{m}_{оп}+\bar{m}_{ш}",
        values={
            "iteration": iteration,
            "wing_ratio": wing_ratio,
            "fuselage_ratio": fuselage_ratio,
            "tail_ratio": tail_ratio,
            "landing_gear_ratio": gear_ratio,
        },
        result=float(ratios.total),
        description="Суммарная относительная масса конструкции.",
    )
    return ratios


def calculate_wing_mass_ratio(
    *,
    m0: float,
    wing_area_m2: float,
    wing_aspect_ratio: float,
    wing_taper_ratio: float,
    wing_relative_thickness: float,
    wing_material_factor: float,
    ultimate_load_factor: float,
    f_factor: float,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
    iteration: int | None = None,
) -> float:
    m_wing_1 = (
        0.002
        * wing_material_factor
        * m0
        * ultimate_load_factor
        * f_factor
        * (0.6 * ((math.sqrt(wing_area_m2 * wing_aspect_ratio) / 2.0) ** 2) + 1.0)
        + 3.0 * wing_area_m2
    )
    m_wing_2 = (
        0.0001
        * wing_material_factor
        * m0
        * ultimate_load_factor
        * f_factor
        * (
            wing_aspect_ratio
            * (wing_taper_ratio + 3.0)
            * math.sqrt(wing_area_m2 / wing_taper_ratio)
            * math.sqrt(wing_relative_thickness)
        )
    )
    ratio = (m_wing_1 + m_wing_2) / (2.0 * m0)
    _add_trace(
        trace,
        block_name=block_name,
        value_name=_iter_name("wing_mass_ratio", iteration),
        formula=(
            r"m_{кр1}=0.002k_{м}m_0n_yf\left(0.6\left(\frac{\sqrt{S\lambda}}{2}\right)^2+1\right)+3S; "
            r"m_{кр2}=0.0001k_{м}m_0n_yf\lambda(\eta+3)\sqrt{S/\eta}\sqrt{\varepsilon}; "
            r"\bar{m}_{кр}=\frac{m_{кр1}+m_{кр2}}{2m_0}"
        ),
        values={
            "iteration": iteration,
            "m0": m0,
            "S": wing_area_m2,
            "lambda": wing_aspect_ratio,
            "eta": wing_taper_ratio,
            "epsilon": wing_relative_thickness,
            "k_m": wing_material_factor,
            "n_y": ultimate_load_factor,
            "f": f_factor,
            "m_wing_1": m_wing_1,
            "m_wing_2": m_wing_2,
        },
        result=float(ratio),
        description="Относительная масса крыла как среднее двух формул.",
    )
    return ratio


def calculate_fuselage_mass_ratio(
    *,
    m0: float,
    wing_position: str,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
    iteration: int | None = None,
) -> float:
    if wing_position == WING_POSITION_HIGH:
        k_sx = 1.0
    elif wing_position == WING_POSITION_LOW:
        k_sx = 0.85
    else:
        raise InputValidationError(f"Unknown wing_position: {wing_position!r}")
    fuselage_mass = 0.584 * k_sx * (m0**0.771)
    ratio = fuselage_mass / m0
    _add_trace(
        trace,
        block_name=block_name,
        value_name=_iter_name("fuselage_mass_ratio", iteration),
        formula=r"G_{ф}=0.584k_{сх}G_0^{0.771}, \quad \bar{m}_{ф}=G_{ф}/m_0",
        values={
            "iteration": iteration,
            "m0": m0,
            "wing_position": wing_position,
            "k_sx": k_sx,
            "G_f": fuselage_mass,
        },
        result=float(ratio),
        description="Относительная масса фюзеляжа.",
    )
    return ratio


def calculate_tail_mass_ratio(
    *,
    m0: float,
    cruise_speed_m_s: float,
    horizontal_tail_area_m2: float,
    vertical_tail_area_m2: float,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
    iteration: int | None = None,
) -> float:
    cruise_speed_km_h = 3.6 * cruise_speed_m_s
    horizontal_tail_mass = 7.2 * (horizontal_tail_area_m2**1.2) * (
        0.4 + (cruise_speed_km_h + 113.0) / 935.0
    )
    vertical_tail_mass = 6.8 * (vertical_tail_area_m2**1.2) * (
        0.4 + (cruise_speed_km_h + 113.0) / 1100.0
    )
    ratio = (horizontal_tail_mass + vertical_tail_mass) / m0
    _add_trace(
        trace,
        block_name=block_name,
        value_name=_iter_name("tail_mass_ratio", iteration),
        formula=(
            r"m_{г.о}=7.2S_{г.о}^{1.2}\left(0.4+\frac{3.6V_{кр}+113}{935}\right); "
            r"m_{в.о}=6.8S_{в.о}^{1.2}\left(0.4+\frac{3.6V_{кр}+113}{1100}\right); "
            r"\bar{m}_{оп}=\frac{m_{г.о}+m_{в.о}}{m_0}"
        ),
        values={
            "iteration": iteration,
            "m0": m0,
            "V_cruise_m_s": cruise_speed_m_s,
            "V_cruise_km_h": cruise_speed_km_h,
            "S_go": horizontal_tail_area_m2,
            "S_vo": vertical_tail_area_m2,
            "m_go": horizontal_tail_mass,
            "m_vo": vertical_tail_mass,
        },
        result=float(ratio),
        description="Относительная масса оперения по формуле Хоуви.",
    )
    return ratio


def calculate_landing_gear_mass_ratio(
    *,
    has_landing_gear: bool,
    landing_gear_material: str,
    landing_gear_fairing: str,
    landing_gear_type: str,
    has_brakes: bool,
    landing_gear_strut_length_m: float,
    trace: CalculationTrace | None = None,
    block_name: str = "mass_estimation",
    iteration: int | None = None,
) -> float:
    if not has_landing_gear:
        _add_trace(
            trace,
            block_name=block_name,
            value_name=_iter_name("landing_gear_mass_ratio", iteration),
            formula=r"\bar{m}_{ш}=0",
            values={"iteration": iteration, "has_landing_gear": False},
            result=0.0,
            description="Шасси отсутствует.",
        )
        return 0.0

    if landing_gear_material == GEAR_MATERIAL_MEDIUM_STEEL:
        k_con = 1.0
    elif landing_gear_material == GEAR_MATERIAL_HIGH_STRENGTH:
        k_con = 0.65
    else:
        raise InputValidationError(
            f"Unknown landing_gear_material: {landing_gear_material!r}"
        )

    if landing_gear_fairing == GEAR_FAIRING_NONE:
        k_obt = 1.0
    elif landing_gear_fairing == GEAR_FAIRING_WHEELS:
        k_obt = 1.05
    elif landing_gear_fairing == GEAR_FAIRING_RETRACTABLE:
        k_obt = 1.2
    else:
        raise InputValidationError(
            f"Unknown landing_gear_fairing: {landing_gear_fairing!r}"
        )

    base_ratio = k_con * k_obt * (11.3 + 6.0 * landing_gear_strut_length_m) * 1e-3 + 0.005

    if landing_gear_type == GEAR_TYPE_SKI:
        ratio = base_ratio + 0.032
    elif landing_gear_type == GEAR_TYPE_WHEELED:
        ratio = base_ratio + (0.022 if has_brakes else 0.024)
    else:
        raise InputValidationError(f"Unknown landing_gear_type: {landing_gear_type!r}")

    _add_trace(
        trace,
        block_name=block_name,
        value_name=_iter_name("landing_gear_mass_ratio", iteration),
        formula=(
            r"\bar{m}_{ш,base}=k_{кон}k_{обт}(11.3+6H_{ош})10^{-3}+0.005; "
            r"\bar{m}_{ш}=\bar{m}_{ш,base}+\Delta\bar{m}_{тип}"
        ),
        values={
            "iteration": iteration,
            "landing_gear_material": landing_gear_material,
            "landing_gear_fairing": landing_gear_fairing,
            "landing_gear_type": landing_gear_type,
            "has_brakes": has_brakes,
            "H_osh": landing_gear_strut_length_m,
            "k_con": k_con,
            "k_obt": k_obt,
            "base_ratio": base_ratio,
        },
        result=float(ratio),
        description="Относительная масса шасси.",
    )
    return ratio


def _iterate_structure_and_mass(
    *,
    mass_input: dict[str, Any],
    powerplant_type: str,
    initial_m0: float,
    numerator: float,
    fixed_ratios: dict[str, float],
    trace: CalculationTrace | None,
    block_name: str,
    initial_ratios: dict[str, float],
) -> MassIterationResult:
    tolerance = _positive(mass_input, "wing_loading_tolerance")
    max_iterations = _positive_int(mass_input, "max_iterations")
    current_m0 = initial_m0
    current_wing_area = _positive(mass_input, "wing_area_m2")
    initial_wing_area = current_wing_area
    history: list[dict[str, float]] = []
    converged = False
    relative_delta = math.inf
    last_structure = StructureMassRatios(0.0, 0.0, 0.0, 0.0)
    final_ratios: dict[str, float] = {}

    for iteration in range(1, max_iterations + 1):
        structure_ratios = calculate_structure_mass_ratios(
            m0=current_m0,
            wing_area_m2=current_wing_area,
            mass_input=mass_input,
            trace=trace,
            block_name=block_name,
            iteration=iteration,
        )
        last_structure = structure_ratios

        if powerplant_type == POWERPLANT_ELECTRIC:
            battery_ratio = fixed_ratios["battery_mass_ratio"]
            powerplant_ratio = fixed_ratios["powerplant_mass_ratio"]
            denominator = 1.0 - structure_ratios.total - battery_ratio - powerplant_ratio
            final_ratios = {
                "structure_mass_ratio": structure_ratios.total,
                "battery_mass_ratio": battery_ratio,
                "powerplant_mass_ratio": powerplant_ratio,
            }
            formula = (
                r"m_{0,2}=\frac{m_{цн}+m_{акб.обор}+m_{об.упр}}"
                r"{1-\bar{m}_{кон}-\bar{m}_{акб}-\bar{m}_{с.у}}"
            )
            values = {
                **final_ratios,
                "denominator": denominator,
                "iteration": iteration,
            }
        else:
            fuel_ratio = fixed_ratios["fuel_mass_ratio"]
            special_equipment_ratio = fixed_ratios["special_equipment_mass_ratio"]
            powerplant_ratio = calculate_ice_powerplant_mass_ratio(
                m0=current_m0,
                engine_count=_positive_int(mass_input, "engine_count"),
                engine_type=str(mass_input["engine_type"]),
                takeoff_power_hp=_positive(mass_input, "takeoff_power_hp"),
                trace=trace,
                block_name=block_name,
                iteration=iteration,
            )
            denominator = (
                1.0
                - structure_ratios.total
                - powerplant_ratio
                - special_equipment_ratio
                - fuel_ratio
            )
            final_ratios = {
                "structure_mass_ratio": structure_ratios.total,
                "powerplant_mass_ratio": powerplant_ratio,
                "special_equipment_mass_ratio": special_equipment_ratio,
                "fuel_mass_ratio": fuel_ratio,
            }
            formula = (
                r"m_{0,2}=\frac{m_{цн}+m_{сл}}"
                r"{1-(\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН}+\bar{m}_{т})}"
            )
            values = {
                **final_ratios,
                "denominator": denominator,
                "iteration": iteration,
            }

        next_m0 = calculate_takeoff_mass_from_ratios(
            numerator=numerator,
            denominator=denominator,
            trace=trace,
            block_name=block_name,
            value_name=_iter_name("updated_m0", iteration),
            formula=formula,
            values=values,
        )

        old_wing_loading = current_m0 / current_wing_area
        new_wing_loading = next_m0 / current_wing_area
        relative_delta = abs(new_wing_loading - old_wing_loading) / old_wing_loading

        history.append(
            {
                "iteration": float(iteration),
                "m0_old": float(current_m0),
                "m0_new": float(next_m0),
                "wing_area": float(current_wing_area),
                "old_wing_loading": float(old_wing_loading),
                "new_wing_loading": float(new_wing_loading),
                "relative_delta_wing_loading": float(relative_delta),
                "structure_mass_ratio": float(structure_ratios.total),
                **{key: float(value) for key, value in final_ratios.items()},
            }
        )
        _add_trace(
            trace,
            block_name=block_name,
            value_name=_iter_name("wing_loading_check", iteration),
            formula=r"\Delta p_0=\left|\frac{p_{0,new}-p_{0,old}}{p_{0,old}}\right|",
            values={
                "iteration": iteration,
                "p0_old": old_wing_loading,
                "p0_new": new_wing_loading,
                "tolerance": tolerance,
            },
            result=float(relative_delta),
            description="Проверка изменения нагрузки на крыло.",
        )

        if relative_delta <= tolerance:
            converged = True
            current_m0 = next_m0
            break

        updated_wing_area = current_m0 * current_wing_area / next_m0
        _add_trace(
            trace,
            block_name=block_name,
            value_name=_iter_name("updated_wing_area", iteration),
            formula=r"S_{кр,2}=\frac{m_{0,old}S_{кр}}{m_{0,new}}",
            values={
                "iteration": iteration,
                "m0_old": current_m0,
                "m0_new": next_m0,
                "S_kr": current_wing_area,
            },
            result=float(updated_wing_area),
            unit="m²",
            description="Обновление площади крыла при несходимости нагрузки на крыло.",
        )
        current_m0 = next_m0
        current_wing_area = updated_wing_area

    breakdown = _build_breakdown(
        mass_input=mass_input,
        powerplant_type=powerplant_type,
        final_m0=current_m0,
        final_ratios=final_ratios,
        structure_ratios=last_structure,
    )
    return MassIterationResult(
        powerplant_type=powerplant_type,
        converged=converged,
        iterations=len(history),
        tolerance=tolerance,
        max_iterations=max_iterations,
        initial_m0=initial_m0,
        final_m0=current_m0,
        initial_wing_area=initial_wing_area,
        final_wing_area=current_wing_area,
        relative_delta_wing_loading=relative_delta,
        initial_ratios=initial_ratios,
        final_ratios=final_ratios,
        structure_ratios=last_structure,
        breakdown=breakdown,
        history=history,
    )


def _build_breakdown(
    *,
    mass_input: dict[str, Any],
    powerplant_type: str,
    final_m0: float,
    final_ratios: dict[str, float],
    structure_ratios: StructureMassRatios,
) -> MassBreakdown:
    payload = _non_negative(mass_input, "payload_mass")
    service_load = _non_negative(mass_input, "service_load_mass") if powerplant_type == POWERPLANT_ICE else 0.0
    fuel = final_m0 * final_ratios.get("fuel_mass_ratio", 0.0)
    battery_energy = final_m0 * final_ratios.get("battery_mass_ratio", 0.0)
    battery_equipment = (
        _non_negative(mass_input, "battery_equipment_mass")
        if powerplant_type == POWERPLANT_ELECTRIC
        else 0.0
    )
    control_equipment = (
        _non_negative(mass_input, "control_equipment_mass")
        if powerplant_type == POWERPLANT_ELECTRIC
        else 0.0
    )
    wing = final_m0 * structure_ratios.wing
    fuselage = final_m0 * structure_ratios.fuselage
    tail = final_m0 * structure_ratios.tail
    landing_gear = final_m0 * structure_ratios.landing_gear
    structure = wing + fuselage + tail + landing_gear
    powerplant = final_m0 * final_ratios.get("powerplant_mass_ratio", 0.0)
    special_equipment = final_m0 * final_ratios.get("special_equipment_mass_ratio", 0.0)
    return MassBreakdown(
        payload=payload,
        service_load=service_load,
        fuel=fuel,
        battery_energy=battery_energy,
        battery_equipment=battery_equipment,
        control_equipment=control_equipment,
        structure=structure,
        wing=wing,
        fuselage=fuselage,
        tail=tail,
        landing_gear=landing_gear,
        powerplant=powerplant,
        special_equipment=special_equipment,
    )


def _add_trace(
    trace: CalculationTrace | None,
    *,
    block_name: str,
    value_name: str,
    formula: str,
    values: dict[str, Any],
    result: Any,
    unit: str | None = None,
    description: str | None = None,
) -> None:
    if trace is None:
        return
    trace.add(
        block_name=block_name,
        value_name=value_name,
        formula=formula,
        values=values,
        result=result,
        unit=unit,
        description=description,
    )


def _iter_name(value_name: str, iteration: int | None) -> str:
    if iteration is None:
        return value_name
    return f"iteration_{iteration}.{value_name}"


def _positive(section: dict[str, Any], field_name: str) -> float:
    value = _number(section, field_name)
    if value <= 0:
        raise InputValidationError(f"mass_estimation.{field_name} must be > 0. Got {value}.")
    return value


def _non_negative(section: dict[str, Any], field_name: str) -> float:
    value = _number(section, field_name)
    if value < 0:
        raise InputValidationError(f"mass_estimation.{field_name} must be >= 0. Got {value}.")
    return value


def _positive_int(section: dict[str, Any], field_name: str) -> int:
    value = section[field_name]
    if isinstance(value, bool):
        raise InputValidationError(f"mass_estimation.{field_name} must be integer, not bool.")
    try:
        int_value = int(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"mass_estimation.{field_name} must be integer. Got {value!r}."
        ) from exc
    if int_value <= 0:
        raise InputValidationError(
            f"mass_estimation.{field_name} must be > 0. Got {int_value}."
        )
    return int_value


def _number(section: dict[str, Any], field_name: str) -> float:
    value = section[field_name]
    if isinstance(value, bool):
        raise InputValidationError(f"mass_estimation.{field_name} must be number, not bool.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"mass_estimation.{field_name} must be number. Got {value!r}."
        ) from exc
