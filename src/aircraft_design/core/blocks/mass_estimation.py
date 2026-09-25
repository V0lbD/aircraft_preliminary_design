from __future__ import annotations

import logging
import math

from aircraft_design.core.blocks.base import BaseBlock

logger = logging.getLogger(__name__)

STANDARD_GRAVITY = 9.80665
HP_TO_WATT = 735.5


class MassEstimationBlock(BaseBlock):
    """Блок оценки масс на основе новых итерационных алгоритмов."""
    name = "mass_estimation"
    display_name = "Оценка масс"

    def calculate(self, project: 'ProjectState') -> None:
        mass = project.mass

        # Запускаем соответствующую ветку расчёта
        if project.feasibility.powerplant_type == "electric":
            self._calculate_electric(project)
        elif project.feasibility.powerplant_type == "ice":
            self._calculate_ice(project)
        else:
            raise ValueError(f"Неизвестный тип СУ: {project.feasibility.powerplant_type}")

        # Постобработка: расчёт взлётной тяги и финальной площади крыла
        p0_opt = project.preliminary.p0_optimal
        P0_opt = project.preliminary.P0_optimal

        if P0_opt is not None and P0_opt > 0:
            mass.T_TO = mass.m_MTO * STANDARD_GRAVITY * P0_opt
        else:
            mass.T_TO = 0.0

        if p0_opt is not None and p0_opt > 0:
            mass.S_W = mass.m_MTO * STANDARD_GRAVITY / p0_opt
            project.add_trace(
                value_name="S_W",
                formula=r"S_W=\frac{m_0 g}{p_0}",
                values={"m0": mass.m_MTO, "p0": p0_opt},
                result=float(mass.S_W),
                unit="м²",
                description="Итоговая площадь крыла.",
            )
        else:
            mass.S_W = 0.0

    def _calculate_ice(self, project: 'ProjectState') -> None:
        mass = project.mass
        prelim = project.preliminary

        numerator = project.feasibility.payload_mass + mass.service_load_mass

        fuel_ratio = self._calc_breguet_fuel_ratio(project)

        chumak_total_ratio = mass.empty_equipped_mass_ratio

        project.add_trace(
            value_name="chumak_initial_mass_ratio_sum",
            formula=r"\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН} = \bar{m}_{пуст.снаряж}",
            values={"empty_equipped_mass_ratio": chumak_total_ratio},
            result=float(chumak_total_ratio),
            unit="",
            description="Первое приближение суммы относительных масс (задается пользователем).",
        )

        initial_denominator = 1.0 - chumak_total_ratio - fuel_ratio
        if initial_denominator <= 0:
            raise ValueError(f"Знаменатель баланса масс <= 0: {initial_denominator}")

        initial_m0 = numerator / initial_denominator
        project.add_trace(
            value_name="ice_initial_m0",
            formula=r"m_{0,1}=\frac{m_{цн}+m_{сл}}{1-(\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{об.СН}+\bar{m}_{т})}",
            values={
                "payload_mass": project.feasibility.payload_mass,
                "service_load_mass": mass.service_load_mass,
                "chumak_total_ratio": chumak_total_ratio,
                "fuel_ratio": fuel_ratio,
                "denominator": initial_denominator,
            },
            result=float(initial_m0),
            unit="кг",
            description="Стартовое значение массы для начала итерационного процесса."
        )

        special_equip_ratio = 0.08 if prelim.N == 1 else 0.11
        project.add_trace(
            value_name="special_equipment_mass_ratio",
            formula=r"\bar{m}_{об.СН}=0.08 \; (n_{дв}=1), \quad \bar{m}_{об.СН}=0.11 \; (n_{дв}>1)",
            values={"engine_count": prelim.N},
            result=float(special_equip_ratio),
            unit="",
            description="Относительная масса целевого и навигационного оборудования."
        )

        project.add_trace(
            value_name="Формулы массы крыла (Чумак)",
            formula=(
                r"m_{кр1} = 0.002 k_{мат} m_0 n_{max} f \left[ 0.6 \left(\frac{\sqrt{S \lambda}}{2}\right)^2 + 1 \right] + 3S \\ "
                r"m_{кр2} = 0.0001 k_{мат} m_0 n_{max} f \lambda (\eta + 3) \sqrt{\frac{S}{\eta}} \sqrt{\bar{c}}"
            ),
            values={
                "k_mat": mass.wing_material_factor,
                "n_max": prelim.n_max,
                "f": mass.f_factor,
                "Lambda": prelim.Lambda,
                "eta": project.geometry.eta_wing,
                "c_rel": mass.wing_relative_thickness
            },
            result="Используются внутри итераций",
            unit="",
            description="Эмпирические зависимости для расчета массы крыла."
        )

        project.add_trace(
            value_name="Итерационные уравнения масс (ДВС)",
            formula=(
                r"\bar{m}_{кр} = \frac{m_{кр1} + m_{кр2}}{2m_0} \\ "
                r"\bar{m}_{ф} = \frac{0.584 \cdot k_{сх} \cdot (m_0 g)^{0.771}}{m_0} \\ "
                r"\bar{m}_{оп} = \frac{m_{го} + m_{во}}{m_0} \\ "
                r"\bar{m}_{ш} = \bar{m}_{ш,base} + \Delta \bar{m}_{тип} \\ "
                r"\bar{m}_{с.у} = \frac{N_{дв} N_{взл} (\gamma_{дв} + k_N)}{m_0}"
            ),
            values={"max_iterations": mass.max_iterations, "tolerance": mass.wing_loading_tolerance},
            result="Запуск цикла",
            unit="",
            description="Система формул для уточнения массы конструкции и силовой установки на каждом шаге итерации."
        )

        # --- ИТЕРАЦИОННЫЙ ЦИКЛ ---
        current_m0 = initial_m0
        converged = False
        relative_delta = float('inf')
        history = []

        structure_ratio = 0.0
        powerplant_ratio = 0.0

        for iteration in range(1, int(mass.max_iterations) + 1):
            wing_area = current_m0 / prelim.p0_optimal

            # Конструкция
            w_ratio = self._calc_wing_ratio(project, current_m0, wing_area, iteration)
            f_ratio = self._calc_fuselage_ratio(project, current_m0, iteration)
            t_ratio = self._calc_tail_ratio(project, current_m0, wing_area, iteration)
            g_ratio = self._calc_landing_gear_ratio(project, iteration)

            structure_ratio = w_ratio + f_ratio + t_ratio + g_ratio

            # Силовая установка
            powerplant_ratio = self._calc_ice_powerplant_ratio(project, current_m0, iteration)

            denominator = 1.0 - structure_ratio - powerplant_ratio - special_equip_ratio - fuel_ratio
            if denominator <= 0:
                raise ValueError(f"Знаменатель итерации <= 0: {denominator}")

            next_m0 = numerator / denominator

            relative_delta = abs(next_m0 - current_m0) / current_m0
            history.append({"iteration": iteration, "m0_old": current_m0, "m0_new": next_m0, "delta": relative_delta})

            if relative_delta <= mass.wing_loading_tolerance:
                converged = True
                current_m0 = next_m0
                break

            current_m0 = next_m0

        # --- СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ---
        self._finalize_results(
            project, current_m0, w_ratio, f_ratio, t_ratio, g_ratio,
            powerplant_ratio, fuel_ratio, special_equip_ratio, 0.0, 0.0,
            converged, len(history), relative_delta, history
        )

    def _calculate_electric(self, project: 'ProjectState') -> None:
        mass = project.mass
        prelim = project.preliminary

        numerator = project.feasibility.payload_mass + mass.battery_equipment_mass + mass.control_equipment_mass

        battery_ratio = self._calc_battery_ratio(project)
        powerplant_ratio = self._calc_electric_powerplant_ratio(project)
        
        # Для электролета также берем стартовое приближение от пользователя
        initial_structure_ratio = mass.empty_equipped_mass_ratio

        project.add_trace(
            value_name="initial_structure_mass_ratio",
            formula=r"\bar{m}_{кон,0} = \bar{m}_{пуст.снаряж}",
            values={"empty_equipped_mass_ratio": initial_structure_ratio},
            result=float(initial_structure_ratio),
            unit="",
            description="Начальное приближение относительной массы для электролёта (задается пользователем)."
        )

        initial_denominator = 1.0 - initial_structure_ratio - battery_ratio - powerplant_ratio
        if initial_denominator <= 0:
            raise ValueError(f"Знаменатель баланса масс <= 0: {initial_denominator}")

        initial_m0 = numerator / initial_denominator
        project.add_trace(
            value_name="electric_initial_m0",
            formula=r"m_{0,1}=\frac{m_{цн}+m_{сл}}{1-(\bar{m}_{к}+\bar{m}_{с.у}+\bar{m}_{акб})}",
            values={"numerator": numerator, "denominator": initial_denominator},
            result=float(initial_m0),
            unit="кг",
            description="Стартовое значение массы для начала итерационного процесса."
        )

        project.add_trace(
            value_name="Формулы массы крыла (Чумак)",
            formula=(
                r"m_{кр1} = 0.002 k_{мат} m_0 n_{max} f \left[ 0.6 \left(\frac{\sqrt{S \lambda}}{2}\right)^2 + 1 \right] + 3S \\ "
                r"m_{кр2} = 0.0001 k_{мат} m_0 n_{max} f \lambda (\eta + 3) \sqrt{\frac{S}{\eta}} \sqrt{\bar{c}}"
            ),
            values={
                "k_mat": mass.wing_material_factor,
                "n_max": prelim.n_max,
                "f": mass.f_factor,
                "Lambda": prelim.Lambda,
                "eta": project.geometry.eta_wing,
                "c_rel": mass.wing_relative_thickness
            },
            result="Используются внутри итераций",
            unit="",
            description="Эмпирические зависимости для расчета массы крыла."
        )

        project.add_trace(
            value_name="Итерационные уравнения масс конструкции",
            formula=(
                r"\bar{m}_{кр} = \frac{m_{кр1} + m_{кр2}}{2m_0} \\ "
                r"\bar{m}_{ф} = \frac{0.584 \cdot k_{сх} \cdot (m_0 g)^{0.771}}{m_0} \\ "
                r"\bar{m}_{оп} = \frac{m_{го} + m_{во}}{m_0} \\ "
                r"\bar{m}_{ш} = \bar{m}_{ш,base} + \Delta \bar{m}_{тип}"
            ),
            values={"max_iterations": mass.max_iterations, "tolerance": mass.wing_loading_tolerance},
            result="Запуск цикла",
            unit="",
            description="Система формул для уточнения массы конструкции на каждом шаге итерации."
        )

        # --- ИТЕРАЦИОННЫЙ ЦИКЛ ---
        current_m0 = initial_m0
        converged = False
        relative_delta = float('inf')
        history = []
        structure_ratio = 0.0

        for iteration in range(1, int(mass.max_iterations) + 1):
            wing_area = current_m0 / prelim.p0_optimal

            w_ratio = self._calc_wing_ratio(project, current_m0, wing_area, iteration)
            f_ratio = self._calc_fuselage_ratio(project, current_m0, iteration)
            t_ratio = self._calc_tail_ratio(project, current_m0, wing_area, iteration)
            g_ratio = self._calc_landing_gear_ratio(project, iteration)

            structure_ratio = w_ratio + f_ratio + t_ratio + g_ratio

            denominator = 1.0 - structure_ratio - battery_ratio - powerplant_ratio
            if denominator <= 0:
                raise ValueError(f"Знаменатель итерации <= 0: {denominator}")

            next_m0 = numerator / denominator

            relative_delta = abs(next_m0 - current_m0) / current_m0
            history.append({"iteration": iteration, "m0_old": current_m0, "m0_new": next_m0, "delta": relative_delta})

            if relative_delta <= mass.wing_loading_tolerance:
                converged = True
                current_m0 = next_m0
                break

            current_m0 = next_m0

        # --- СОХРАНЕНИЕ РЕЗУЛЬТАТОВ ---
        self._finalize_results(
            project, current_m0, w_ratio, f_ratio, t_ratio, g_ratio,
            powerplant_ratio, 0.0, 0.0, battery_ratio, mass.battery_equipment_mass,
            converged, len(history), relative_delta, history
        )

    # --- ВСПОМОГАТЕЛЬНЫЕ РАСЧЕТЫ ---

    def _finalize_results(self, project, m0, w_ratio, f_ratio, t_ratio, g_ratio, pp_ratio, fuel_ratio,
                          spec_equip_ratio, bat_ratio, bat_equip, converged, iters, delta, history):
        mass = project.mass

        # Суммарная масса конструкции
        struct_ratio = w_ratio + f_ratio + t_ratio + g_ratio

        m_F = m0 * (fuel_ratio + bat_ratio)
        m_OE = m0 * (struct_ratio + pp_ratio + spec_equip_ratio) + bat_equip
        useful_load = project.feasibility.payload_mass + mass.service_load_mass

        mass.m_MTO = float(m0)
        mass.m_OE = float(m_OE)
        mass.m_F = float(m_F)
        mass.m_OE_ratio = float(m_OE / m0)
        mass.m_F_ratio = float(m_F / m0)
        mass.useful_load_ratio = float(useful_load / m0)
        mass.structure_mass_ratio = float(struct_ratio)
        mass.converged = converged
        mass.iterations = iters
        mass.wing_loading_relative_delta = float(delta)

        project.add_trace(
            value_name="m_MTO_final",
            formula=r"m_0 = \frac{m_{цн} + m_{сл}}{1 - \sum \bar{m}_i}",
            values={"converged": converged, "iterations": iters, "delta": delta},
            result=float(m0),
            unit="кг",
            description="Уточненная взлетная масса после схождения итерационного баланса масс."
        )

        project.databases["component_masses"] = {
            "payload": float(project.feasibility.payload_mass),
            "service_load": float(mass.service_load_mass),
            "wing": float(m0 * w_ratio),
            "fuselage": float(m0 * f_ratio),
            "tail": float(m0 * t_ratio),
            "landing_gear": float(m0 * g_ratio),
            "powerplant": float(m0 * pp_ratio),
            "special_equipment": float(m0 * spec_equip_ratio),
            "fuel": float(m_F)
        }

        project.databases["mass_iteration_history"] = history

    def _calc_breguet_fuel_ratio(self, project: 'ProjectState') -> float:
        mass = project.mass
        exponent = -(project.feasibility.design_range * mass.cruise_sfc_power * STANDARD_GRAVITY /
                     (project.preliminary.K_max * mass.propeller_efficiency * HP_TO_WATT * 3.6))
        ratio = 1.0 - math.exp(exponent)
        project.add_trace(
            value_name="fuel_mass_ratio_breguet",
            formula=r"\bar{m}_{т}=1-\exp\left(-\frac{L C_{e} g}{K \eta_{в} \cdot 735.5 \cdot 3.6}\right)",
            values={"L_km": project.feasibility.design_range, "C_e": mass.cruise_sfc_power},
            result=float(ratio),
            unit="",
            description="Относительная масса топлива по формуле Бреге."
        )
        return ratio

    def _calc_battery_ratio(self, project: 'ProjectState') -> float:
        mass = project.mass
        prelim = project.preliminary
        design_range_m = project.feasibility.design_range * 1000.0
        numerator = STANDARD_GRAVITY * (mass.cruise_altitude_m + (
                0.5 * prelim.V_cruise ** 2) / STANDARD_GRAVITY + design_range_m / project.preliminary.K_max)
        denominator = 3600.0 * mass.battery_specific_energy_wh_kg * mass.electric_powertrain_efficiency
        ratio = numerator / denominator
        project.add_trace(
            value_name="battery_mass_ratio",
            formula=r"\bar{m}_{акб}=\frac{g\left(H+\frac{0.5V_{кр}^{2}}{g}+\frac{L}{K}\right)}{3600 q \eta_{су}}",
            values={"q": mass.battery_specific_energy_wh_kg, "H": mass.cruise_altitude_m},
            result=float(ratio),
            unit="",
            description="Относительная масса аккумуляторной батареи."
        )
        return ratio

    def _calc_electric_powerplant_ratio(self, project: 'ProjectState') -> float:
        mass = project.mass
        coefficient = 0.3491 if mass.is_under_2_5kg else 0.4695
        ratio = coefficient * mass.power_loading_N0_kw_kg
        project.add_trace(
            value_name="electric_powerplant_mass_ratio",
            formula=r"\bar{m}_{с.у}=C_{с.у}\bar{N}_{0}",
            values={"coefficient": coefficient, "N0": mass.power_loading_N0_kw_kg},
            result=float(ratio),
            unit="",
            description="Относительная масса электрической силовой установки."
        )
        return ratio

    def _calc_ice_powerplant_ratio(self, project: 'ProjectState', m0: float, iteration: int) -> float:
        mass = project.mass
        prelim = project.preliminary
        if mass.engine_type == "piston":
            k_n = 0.55
            gamma_engine = max(1.0 - 0.012 * math.sqrt(mass.takeoff_power_hp), 0.0)
        else:
            k_n = 0.23
            gamma_engine = 0.20

        powerplant_mass = prelim.N * mass.takeoff_power_hp * (gamma_engine + k_n)
        return powerplant_mass / m0

    def _calc_wing_ratio(self, project: 'ProjectState', m0: float, wing_area: float, iteration: int) -> float:
        mass = project.mass
        prelim = project.preliminary
        geom = project.geometry

        m_wing_1 = 0.002 * mass.wing_material_factor * m0 * prelim.n_max * mass.f_factor * (
                0.6 * ((math.sqrt(wing_area * prelim.Lambda) / 2.0) ** 2) + 1.0) + 3.0 * wing_area
        m_wing_2 = 0.0001 * mass.wing_material_factor * m0 * prelim.n_max * mass.f_factor * (
                prelim.Lambda * (geom.eta_wing + 3.0) * math.sqrt(wing_area / geom.eta_wing) * math.sqrt(
            mass.wing_relative_thickness))
        return (m_wing_1 + m_wing_2) / (2.0 * m0)

    def _calc_fuselage_ratio(self, project: 'ProjectState', m0: float, iteration: int) -> float:
        mass = project.mass
        k_sx = 1.0 if mass.wing_position == "high" else 0.85
        fuselage_mass = 0.584 * k_sx * (m0 ** 0.771)
        return fuselage_mass / m0

    def _calc_tail_ratio(self, project: 'ProjectState', m0: float, wing_area: float, iteration: int) -> float:
        prelim = project.preliminary
        geom = project.geometry

        S_go = wing_area * geom.k_horizontal_tail
        S_vo = wing_area * geom.k_vertical_tail
        cruise_speed_km_h = 3.6 * prelim.V_cruise

        horizontal_tail_mass = 7.2 * (S_go ** 1.2) * (0.4 + (cruise_speed_km_h + 113.0) / 935.0)
        vertical_tail_mass = 6.8 * (S_vo ** 1.2) * (0.4 + (cruise_speed_km_h + 113.0) / 1100.0)
        return (horizontal_tail_mass + vertical_tail_mass) / m0

    def _calc_landing_gear_ratio(self, project: 'ProjectState', iteration: int) -> float:
        mass = project.mass
        if not mass.has_landing_gear:
            return 0.0

        k_con = 1.0 if mass.landing_gear_material == "medium_steel" else 0.65
        if mass.landing_gear_fairing == "none":
            k_obt = 1.0
        elif mass.landing_gear_fairing == "wheel_fairings":
            k_obt = 1.05
        else:
            k_obt = 1.2

        base_ratio = k_con * k_obt * (11.3 + 6.0 * mass.landing_gear_strut_length_m) * 1e-3 + 0.005

        if mass.landing_gear_type == "ski":
            return base_ratio + 0.032
        return base_ratio + (0.022 if mass.has_brakes else 0.024)