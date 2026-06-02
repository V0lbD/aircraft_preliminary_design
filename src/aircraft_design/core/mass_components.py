from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field
from typing import Any

from aircraft_design.core.errors import InputValidationError

logger = logging.getLogger(__name__)

STANDARD_GRAVITY = 9.80665
DAN_TO_NEWTON = 10.0

ENGINE_ELECTRIC = "электрический"
ENGINE_PISTON_AIR = "ПД воздушного охлаждения"
ENGINE_PISTON_LIQUID = "ПД жидкостного охлаждения"
ENGINE_TURBOPROP = "турбовинтовой"

GEAR_NONE = "нет"
GEAR_SKI = "лыжное"
GEAR_WHEELED_BRAKED = "колёсное с тормозами"
GEAR_WHEELED_UNBRAKED = "колёсное без тормозов"

GEAR_MATERIAL_MEDIUM_STEEL = "сталь средней удельной прочности"
GEAR_MATERIAL_HIGH_STRENGTH = "металл высокой удельной прочности"

GEAR_FAIRING_NONE = "нет"
GEAR_FAIRING_WHEELS = "на колёса"
GEAR_FAIRING_RETRACTABLE = "убираемое шасси"


@dataclass(slots=True)
class ComponentMassSettings:
    enabled: bool = True
    tolerance: float = 0.05
    max_iterations: int = 30
    runaway_factor: float = 3.0
    max_reasonable_mass_kg: float = 1_000_000.0

    engine_type: str = ENGINE_PISTON_AIR
    propeller_efficiency: float = 0.8

    wing_material_factor: float = 1.0
    wing_relative_thickness: float = 0.12
    wing_taper_ratio: float = 2.5

    fuselage_engine_mount_factor: float = 1.0

    landing_gear_type: str = GEAR_WHEELED_BRAKED
    landing_gear_material: str = GEAR_MATERIAL_MEDIUM_STEEL
    landing_gear_fairing: str = GEAR_FAIRING_NONE
    landing_gear_strut_length_m: float = 1.0

    battery_specific_energy_wh_kg: float = 250.0
    battery_efficiency: float = 0.85
    cruise_altitude_m: float = 0.0

    additional_mass_ratio: float = 0.0


@dataclass(slots=True)
class ComponentMassBreakdown:
    payload: float
    fuel: float
    wing: float
    fuselage: float
    tail: float
    powerplant: float
    landing_gear: float
    battery: float
    equipment_and_control: float
    additional: float

    @property
    def operating_empty_mass(self) -> float:
        return (
            self.wing
            + self.fuselage
            + self.tail
            + self.powerplant
            + self.landing_gear
            + self.battery
            + self.equipment_and_control
            + self.additional
        )

    @property
    def total_mass(self) -> float:
        return self.payload + self.fuel + self.operating_empty_mass

    def to_dict(self) -> dict[str, float]:
        data = asdict(self)
        data["operating_empty_mass"] = self.operating_empty_mass
        data["total_mass"] = self.total_mass
        return data


@dataclass(slots=True)
class ComponentMassIterationResult:
    enabled: bool
    converged: bool
    iterations: int
    tolerance: float
    max_iterations: int
    initial_m0: float
    final_m0: float
    relative_delta: float
    history: list[dict[str, float]] = field(default_factory=list)
    component_masses: ComponentMassBreakdown | None = None
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "converged": self.converged,
            "iterations": self.iterations,
            "tolerance": self.tolerance,
            "max_iterations": self.max_iterations,
            "initial_m0": self.initial_m0,
            "final_m0": self.final_m0,
            "relative_delta": self.relative_delta,
            "history": self.history,
            "failure_reason": self.failure_reason,
            "component_masses": (
                self.component_masses.to_dict()
                if self.component_masses is not None
                else {}
            ),
        }


def calculate_component_mass_iteration(
    *,
    initial_m0: float,
    payload_mass: float,
    fuel_mass_ratio: float,
    p0_optimal: float,
    S_W: float,
    preliminary_input: dict[str, Any],
    mass_input: dict[str, Any],
    geometry_input: dict[str, Any],
) -> ComponentMassIterationResult:
    settings = build_component_mass_settings(mass_input)
    failure_reason: str | None = None

    if not settings.enabled:
        return ComponentMassIterationResult(
            enabled=False,
            converged=True,
            iterations=0,
            tolerance=settings.tolerance,
            max_iterations=settings.max_iterations,
            initial_m0=initial_m0,
            final_m0=initial_m0,
            relative_delta=0.0,
            component_masses=None,
            failure_reason=failure_reason,
        )

    _validate_iteration_inputs(
        initial_m0=initial_m0,
        payload_mass=payload_mass,
        fuel_mass_ratio=fuel_mass_ratio,
        p0_optimal=p0_optimal,
        settings=settings,
    )

    logger.info(
        "Starting component mass iteration: initial_m0=%.3f kg, tolerance=%.3f, max_iterations=%s",
        initial_m0,
        settings.tolerance,
        settings.max_iterations,
    )

    m0_old = initial_m0
    history: list[dict[str, float]] = []
    final_breakdown: ComponentMassBreakdown | None = None
    final_delta = math.inf
    converged = False

    for iteration in range(1, settings.max_iterations + 1):
        breakdown = calculate_component_masses_once(
            m0=m0_old,
            payload_mass=payload_mass,
            fuel_mass_ratio=fuel_mass_ratio,
            p0_optimal=p0_optimal,
            S_W=S_W,
            preliminary_input=preliminary_input,
            mass_input=mass_input,
            geometry_input=geometry_input,
            settings=settings,
        )

        m0_new = breakdown.total_mass
        relative_delta = abs(m0_new - m0_old) / m0_old

        failure_reason: str | None = None

        if not math.isfinite(m0_new):
            failure_reason = (
                f"Non-finite mass value during component iteration: m0_new={m0_new}"
            )

        elif not math.isfinite(relative_delta):
            failure_reason = (
                f"Non-finite relative delta during component iteration: "
                f"relative_delta={relative_delta}"
            )

        elif m0_new > settings.max_reasonable_mass_kg:
            failure_reason = (
                f"Mass exceeded max reasonable limit: "
                f"m0_new={m0_new:.3f} kg, "
                f"limit={settings.max_reasonable_mass_kg:.3f} kg"
            )

        elif m0_new > settings.runaway_factor * m0_old:
            failure_reason = (
                f"Runaway iteration detected: "
                f"m0_new={m0_new:.3f} kg is more than "
                f"{settings.runaway_factor:.2f} times m0_old={m0_old:.3f} kg"
            )

        history.append(
            {
                "iteration": float(iteration),
                "m0_old": float(m0_old),
                "m0_new": float(m0_new),
                "relative_delta": float(relative_delta),
                "operating_empty_mass": float(breakdown.operating_empty_mass),
                "fuel_mass": float(breakdown.fuel),
            }
        )

        logger.info(
            "Component mass iteration %s: m0_old=%.3f kg, m0_new=%.3f kg, delta=%.5f",
            iteration,
            m0_old,
            m0_new,
            relative_delta,
        )

        logger.debug(
            "Component masses at iteration %s: %s",
            iteration,
            breakdown.to_dict(),
        )

        if failure_reason is not None:
            logger.error(failure_reason)
            final_breakdown = breakdown
            final_delta = relative_delta
            break

        final_breakdown = breakdown
        final_delta = relative_delta

        if relative_delta <= settings.tolerance:
            converged = True
            logger.info(
                "Component mass iteration converged after %s iterations: final_m0=%.3f kg",
                iteration,
                m0_new,
            )
            break

        m0_old = m0_new

    if not converged:
        logger.warning(
            "Component mass iteration did not converge after %s iterations. "
            "Last m0=%.3f kg, last delta=%.5f",
            settings.max_iterations,
            m0_old,
            final_delta,
        )

    final_m0 = final_breakdown.total_mass if final_breakdown is not None else initial_m0

    return ComponentMassIterationResult(
        enabled=True,
        converged=converged,
        iterations=len(history),
        tolerance=settings.tolerance,
        max_iterations=settings.max_iterations,
        initial_m0=initial_m0,
        final_m0=final_m0,
        relative_delta=final_delta,
        history=history,
        component_masses=final_breakdown,
        failure_reason=failure_reason,
    )


def calculate_component_masses_once(
    *,
    m0: float,
    payload_mass: float,
    fuel_mass_ratio: float,
    p0_optimal: float,
    S_W: float,
    preliminary_input: dict[str, Any],
    mass_input: dict[str, Any],
    geometry_input: dict[str, Any],
    settings: ComponentMassSettings,
) -> ComponentMassBreakdown:
    fuel_mass = m0 * fuel_mass_ratio

    wing_mass = calculate_wing_mass(
        m0=m0,
        p0_optimal=p0_optimal,
        S_W = S_W,
        preliminary_input=preliminary_input,
        geometry_input=geometry_input,
        settings=settings,
    )

    fuselage_mass = calculate_fuselage_mass(
        m0=m0,
        settings=settings,
    )

    tail_mass = calculate_tail_mass(
        m0=m0,
        p0_optimal=p0_optimal,
        preliminary_input=preliminary_input,
        geometry_input=geometry_input,
    )

    powerplant_mass = calculate_powerplant_mass(
        m0=m0,
        p0_optimal=p0_optimal,
        preliminary_input=preliminary_input,
        settings=settings,
    )

    landing_gear_mass = calculate_landing_gear_mass(
        m0=m0,
        settings=settings,
    )

    battery_mass = calculate_battery_mass(
        m0=m0,
        preliminary_input=preliminary_input,
        mass_input=mass_input,
        settings=settings,
    )

    equipment_and_control_mass = calculate_equipment_and_control_mass(m0=m0)

    additional_mass = m0 * settings.additional_mass_ratio

    return ComponentMassBreakdown(
        payload=payload_mass,
        fuel=fuel_mass,
        wing=wing_mass,
        fuselage=fuselage_mass,
        tail=tail_mass,
        powerplant=powerplant_mass,
        landing_gear=landing_gear_mass,
        battery=battery_mass,
        equipment_and_control=equipment_and_control_mass,
        additional=additional_mass,
    )


def calculate_wing_mass(
    *,
    m0: float,
    p0_optimal: float,
    S_W: float,
    preliminary_input: dict[str, Any],
    geometry_input: dict[str, Any],
    settings: ComponentMassSettings,
) -> float:
    lambda_wing = _get_number(preliminary_input, "Lambda")
    n_p = _get_number(preliminary_input, "n_max")

    eta = _get_optional_number(
        geometry_input,
        "eta_wing",
        settings.wing_taper_ratio,
    )

    # размах крыла
    wing_span = math.sqrt(S_W * lambda_wing)

    k_m = settings.wing_material_factor
    c_bar = settings.wing_relative_thickness

    m_wing_1 = (
        0.002
        * k_m
        * m0
        * n_p
        * (0.6 * (wing_span / 2.0) ** 2 + 1.0)
        + 3.0 * S_W
    )

    m_wing_2 = (
        0.001
        * k_m
        * m0
        * n_p
        * lambda_wing
        * (eta + 3.0)
        * math.sqrt(S_W / eta)
        * math.sqrt(c_bar)
    )

    wing_mass = (m_wing_1 + m_wing_2) / 2.0

    logger.debug(
        "Wing mass formulas: m1=%.3f kg, m2=%.3f kg, mean=%.3f kg",
        m_wing_1,
        m_wing_2,
        wing_mass,
    )

    return wing_mass


def calculate_fuselage_mass(
    *,
    m0: float,
    settings: ComponentMassSettings,
) -> float:
    g0_daN = m0 * STANDARD_GRAVITY


    g_fuselage_daN = (
        0.584
        * settings.fuselage_engine_mount_factor
        * g0_daN**0.771
    )

    fuselage_mass = g_fuselage_daN / STANDARD_GRAVITY

    logger.debug(
        "Fuselage mass formula: G_f=0.584*k_cx*G0^0.771 = %.3f daN = %.3f kg",
        g_fuselage_daN,
        fuselage_mass,
    )

    return fuselage_mass


def calculate_tail_mass(
    *,
    m0: float,
    p0_optimal: float,
    preliminary_input: dict[str, Any],
    geometry_input: dict[str, Any],
) -> float:
    v_cruise_mps = _get_number(preliminary_input, "V_cruise")
    v_cruise_kmh = v_cruise_mps * 3.6

    wing_area = m0 * STANDARD_GRAVITY / p0_optimal

    k_horizontal_tail = _get_optional_number(
        geometry_input,
        "k_horizontal_tail",
        0.25,
    )
    k_vertical_tail = _get_optional_number(
        geometry_input,
        "k_vertical_tail",
        0.15,
    )

    s_ht = k_horizontal_tail * wing_area
    s_vt = k_vertical_tail * wing_area

    m_ht = 7.2 * s_ht**1.2 * (0.4 + (v_cruise_kmh + 113.0) / 935.0)
    m_vt = 6.8 * s_vt**1.2 * (0.4 + 7.0 * (v_cruise_kmh + 113.0) / 1100.0)

    tail_mass = m_ht + m_vt

    logger.debug(
        "Tail mass formulas: m_ht=%.3f kg, m_vt=%.3f kg, total=%.3f kg",
        m_ht,
        m_vt,
        tail_mass,
    )

    return tail_mass


def calculate_powerplant_mass(
    *,
    m0: float,
    p0_optimal: float,
    preliminary_input: dict[str, Any],
    settings: ComponentMassSettings,
) -> float:
    specific_power = calculate_specific_power(
        p0_optimal=p0_optimal,
        preliminary_input=preliminary_input,
        propeller_efficiency=settings.propeller_efficiency,
    )

    total_power = specific_power * m0

    if settings.engine_type == ENGINE_ELECTRIC:
        powerplant_mass = 0.4695 * specific_power * m0

        logger.debug(
            "Electric powerplant mass: m_su=0.4695*Nbar*m0 = %.3f kg",
            powerplant_mass,
        )

        return powerplant_mass

    if settings.engine_type == ENGINE_PISTON_AIR:
        gamma_engine = 0.9 - 0.012 * math.sqrt(max(total_power, 0.0))
        k_su = 0.55

    elif settings.engine_type == ENGINE_PISTON_LIQUID:
        gamma_engine = 1.0 - 0.012 * math.sqrt(max(total_power, 0.0))
        k_su = 0.55

    elif settings.engine_type == ENGINE_TURBOPROP:
        gamma_engine = 0.2
        k_su = 0.23

    else:
        raise InputValidationError(f"Unknown engine_type: {settings.engine_type!r}")

    if gamma_engine < 0:
        logger.warning(
            "Calculated gamma_engine is negative: %.5f. Clamped to 0.",
            gamma_engine,
        )
        gamma_engine = 0.0

    powerplant_mass = total_power * (gamma_engine + k_su)

    logger.debug(
        "Powerplant mass: total_power=%.5f, gamma=%.5f, k_su=%.5f, mass=%.3f kg",
        total_power,
        gamma_engine,
        k_su,
        powerplant_mass,
    )

    return powerplant_mass


def calculate_specific_power(
    *,
    p0_optimal: float,
    preliminary_input: dict[str, Any],
    propeller_efficiency: float,
) -> float:
    rho = _get_number(preliminary_input, "pho_V_cruise")
    v_cruise = _get_number(preliminary_input, "V_cruise")
    c_x0 = _get_number(preliminary_input, "C_x0")
    lambda_wing = _get_number(preliminary_input, "Lambda")
    e = _get_number(preliminary_input, "e")

    q_dynamic = rho * v_cruise**2 / 2.0
    k_ind = 1.0 / (math.pi * e * lambda_wing)

    specific_power = (
        1.0
        / propeller_efficiency
        * (
            q_dynamic * c_x0 / (p0_optimal * v_cruise)
            + p0_optimal * k_ind / (q_dynamic * v_cruise)
        )
    )

    logger.debug(
        "Specific power formula: Nbar=1/eta*(q*Cx0/(p0*V)+p0*k_ind/(q*V)) = %.8f",
        specific_power,
    )

    return specific_power


def calculate_landing_gear_mass(
    *,
    m0: float,
    settings: ComponentMassSettings,
) -> float:
    if settings.landing_gear_type == GEAR_NONE:
        logger.debug("Landing gear type is 'нет': landing gear mass = 0 kg")
        return 0.0

    g0_daN = kg_to_daN(m0)

    k_material = {
        GEAR_MATERIAL_MEDIUM_STEEL: 1.0,
        GEAR_MATERIAL_HIGH_STRENGTH: 0.65,
    }[settings.landing_gear_material]

    k_fairing = {
        GEAR_FAIRING_NONE: 1.0,
        GEAR_FAIRING_WHEELS: 1.05,
        GEAR_FAIRING_RETRACTABLE: 1.2,
    }[settings.landing_gear_fairing]

    h = settings.landing_gear_strut_length_m

    g_gear_base_daN = k_material * k_fairing * (11.7 + 6.0 * h) * 1e-3 * g0_daN

    if settings.landing_gear_type == GEAR_SKI:
        g_gear_total_daN = g_gear_base_daN + 0.032 * g0_daN

    elif settings.landing_gear_type == GEAR_WHEELED_BRAKED:
        g_wheels_daN = 0.0625 * 0.93 * 0.385 * g0_daN
        g_gear_total_daN = g_gear_base_daN + g_wheels_daN

    elif settings.landing_gear_type == GEAR_WHEELED_UNBRAKED:
        g_wheels_daN = 0.0625 * 0.90 * 0.46 * g0_daN
        g_gear_total_daN = g_gear_base_daN + g_wheels_daN

    else:
        raise InputValidationError(
            f"Unknown landing_gear_type: {settings.landing_gear_type!r}"
        )

    landing_gear_mass = daN_to_kg(g_gear_total_daN)

    logger.debug(
        "Landing gear mass: G_base=%.3f daN, G_total=%.3f daN, mass=%.3f kg",
        g_gear_base_daN,
        g_gear_total_daN,
        landing_gear_mass,
    )

    return landing_gear_mass


def calculate_battery_mass(
    *,
    m0: float,
    preliminary_input: dict[str, Any],
    mass_input: dict[str, Any],
    settings: ComponentMassSettings,
) -> float:
    if settings.engine_type != ENGINE_ELECTRIC:
        return 0.0

    h_cruise = settings.cruise_altitude_m
    v_cruise = _get_number(preliminary_input, "V_cruise")
    design_range_m = _get_number(mass_input, "design_range") * 1000.0
    aerodynamic_quality = _get_number(mass_input, "cruise_L_D_ratio")
    q_battery = settings.battery_specific_energy_wh_kg
    eta_su = settings.battery_efficiency

    battery_mass_ratio = (
        STANDARD_GRAVITY
        * (
            h_cruise
            + 0.5 * v_cruise**2 / STANDARD_GRAVITY
            + design_range_m / aerodynamic_quality
        )
        / (3600.0 * q_battery * eta_su)
    )

    battery_mass = battery_mass_ratio * m0

    logger.debug(
        "Battery mass: mbar=%.5f, m_battery=%.3f kg",
        battery_mass_ratio,
        battery_mass,
    )

    return battery_mass


def calculate_equipment_and_control_mass(*, m0: float) -> float:
    g0_daN = kg_to_daN(m0)
    g_equipment_daN = 0.00635 * g0_daN**1.37
    equipment_mass = daN_to_kg(g_equipment_daN)

    logger.debug(
        "Equipment and control mass: G=0.00635*G0^1.37 = %.3f daN = %.3f kg",
        g_equipment_daN,
        equipment_mass,
    )

    return equipment_mass


def build_component_mass_settings(mass_input: dict[str, Any]) -> ComponentMassSettings:
    return ComponentMassSettings(
        enabled=bool(mass_input.get("component_iteration_enabled", True)),
        tolerance=float(mass_input.get("component_tolerance", 0.05)),
        max_iterations=int(mass_input.get("component_max_iterations", 30)),
        engine_type=str(mass_input.get("engine_type", ENGINE_PISTON_AIR)),
        propeller_efficiency=float(mass_input.get("propeller_efficiency", 0.8)),
        wing_material_factor=float(mass_input.get("wing_material_factor", 1.0)),
        wing_relative_thickness=float(mass_input.get("wing_relative_thickness", 0.12)),
        wing_taper_ratio=float(mass_input.get("wing_taper_ratio", 2.5)),
        fuselage_engine_mount_factor=float(
            mass_input.get("fuselage_engine_mount_factor", 1.0)
        ),
        landing_gear_type=str(mass_input.get("landing_gear_type", GEAR_WHEELED_BRAKED)),
        landing_gear_material=str(
            mass_input.get("landing_gear_material", GEAR_MATERIAL_MEDIUM_STEEL)
        ),
        landing_gear_fairing=str(
            mass_input.get("landing_gear_fairing", GEAR_FAIRING_NONE)
        ),
        landing_gear_strut_length_m=float(
            mass_input.get("landing_gear_strut_length_m", 1.0)
        ),
        battery_specific_energy_wh_kg=float(
            mass_input.get("battery_specific_energy_wh_kg", 250.0)
        ),
        battery_efficiency=float(mass_input.get("battery_efficiency", 0.85)),
        cruise_altitude_m=float(mass_input.get("cruise_altitude_m", 0.0)),
        additional_mass_ratio=float(mass_input.get("additional_mass_ratio", 0.0)),
        runaway_factor=float(mass_input.get("component_runaway_factor", 3.0)),
        max_reasonable_mass_kg=float(mass_input.get("component_max_reasonable_mass_kg", 1_000_000.0)),
    )


def kg_to_daN(mass_kg: float) -> float:
    return mass_kg * STANDARD_GRAVITY / DAN_TO_NEWTON


def daN_to_kg(weight_daN: float) -> float:
    return weight_daN * DAN_TO_NEWTON / STANDARD_GRAVITY


def _validate_iteration_inputs(
    *,
    initial_m0: float,
    payload_mass: float,
    fuel_mass_ratio: float,
    p0_optimal: float,
    settings: ComponentMassSettings,
) -> None:
    if initial_m0 <= 0:
        raise InputValidationError(f"initial_m0 must be positive. Got: {initial_m0}")

    if payload_mass < 0:
        raise InputValidationError(f"payload_mass must be non-negative. Got: {payload_mass}")

    if fuel_mass_ratio < 0:
        raise InputValidationError(
            f"fuel_mass_ratio must be non-negative. Got: {fuel_mass_ratio}"
        )

    if p0_optimal <= 0:
        raise InputValidationError(f"p0_optimal must be positive. Got: {p0_optimal}")

    if settings.tolerance <= 0:
        raise InputValidationError(
            f"component_tolerance must be positive. Got: {settings.tolerance}"
        )

    if settings.max_iterations <= 0:
        raise InputValidationError(
            f"component_max_iterations must be positive. Got: {settings.max_iterations}"
        )


def _get_number(section: dict[str, Any], field_name: str) -> float:
    try:
        value = section[field_name]
    except KeyError as exc:
        raise InputValidationError(f"Missing required field: {field_name}") from exc

    return _to_float(value, field_name)


def _get_optional_number(
    section: dict[str, Any],
    field_name: str,
    default: float,
) -> float:
    if field_name not in section or section[field_name] is None:
        return default

    return _to_float(section[field_name], field_name)


def _to_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise InputValidationError(f"{field_name} must be a number, not bool.")

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(
            f"{field_name} must be a number. Got: {value!r}"
        ) from exc