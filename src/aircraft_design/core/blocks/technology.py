from __future__ import annotations

import itertools
import logging
import math
from typing import Any

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.technology_names import resolve_technology_name

logger = logging.getLogger(__name__)


class TechnologyBlock(BaseBlock):
    """
    Блок производственно-экономической оптимизации (Design for Manufacturing).
    Выбирает оптимальную комбинацию технологий изготовления для минимизации себестоимости.
    """
    name = "technology"
    display_name = "Параметры производства"

    def calculate(self, project: 'ProjectState') -> None:
        tech = project.technology
        mass = project.mass

        # 1. Проверяем наличие базы данных
        if "technology_db" not in project.databases:
            raise InputValidationError(
                "База данных технологий (Excel) не загружена в проект (project.databases['technology_db']).")

        db = project.databases["technology_db"]

        # 2. Получаем исходные массы для пересчета M0
        m_mto_initial = mass.m_MTO
        if m_mto_initial <= 0:
            raise InputValidationError("Невозможно рассчитать экономику: M0 <= 0. Выполнен ли расчет масс?")

        if "component_masses" not in project.databases:
            raise InputValidationError("Развесовка компонентов (component_masses) не найдена в базе проекта.")

        comp_masses = project.databases["component_masses"]
        m_fixed = comp_masses.get("payload", 0.0) + comp_masses.get("service_load", 0.0)

        m_kr_old = comp_masses.get("wing", 0.0) / m_mto_initial
        m_fuse_old = comp_masses.get("fuselage", 0.0) / m_mto_initial
        m_tail_old = comp_masses.get("tail", 0.0) / m_mto_initial
        denom_old = m_fixed / m_mto_initial

        NLA = tech.NLA
        T = tech.T
        TLA = NLA / T

        alum_techs = ["alum_1", "alum_2"]
        comp_techs = ["comp_1", "comp_2"]
        valid_component_combos = (
                list(itertools.product(alum_techs, repeat=3)) +
                list(itertools.product(comp_techs, repeat=3))
        )

        project.add_trace(
            value_name="Уравнения технико-экономического перебора",
            formula=(
                r"m_{0,new} = \frac{m_{fix}}{\bar{m}_{fix,old} - \Delta\bar{m}_{struct}} \\ "
                r"n_{стан} = \left\lceil \frac{T_{LA} N_{эл}}{N_{дет}} \right\rceil \\ "
                r"C_{мат} = C_1 \cdot \frac{m_{эл}}{КИМ} \cdot m_{0,new} \\ "
                r"C_{труд} = 1.3 \cdot n_{стан} \cdot n_{раб} \cdot C_{н.ч.} \cdot T \\ "
                r"C_{осн} = n_{стан} \cdot C_{ст1}"
            ),
            values={"NLA": NLA, "T": T, "TLA": TLA},
            result="Запуск перебора технологий",
            unit="",
            description="Формулы для расчета стоимости материалов, труда и оснастки на каждой итерации перебора."
        )

        best_cost = float("inf")
        best_details = {}
        best_combo_names = {}

        logger.info(f"Начало перебора {len(valid_component_combos) ** 3} комбинаций технологий...")

        # 3. Основной цикл перебора
        for wing_combo, fuse_combo, tail_combo in itertools.product(valid_component_combos, repeat=3):
            wing_res = self._calc_component('wing', wing_combo, db, TLA, T, m_kr_old)
            fuse_res = self._calc_component('fuselage', fuse_combo, db, TLA, T, m_fuse_old)
            tail_res = self._calc_component('tail', tail_combo, db, TLA, T, m_tail_old)

            m_kr_new = wing_res['mel_total']
            m_fuse_new = fuse_res['mel_total']
            m_tail_new = tail_res['mel_total']

            delta_struct = (m_kr_new + m_fuse_new + m_tail_new) - (m_kr_old + m_fuse_old + m_tail_old)
            denom_new = denom_old - delta_struct

            if denom_new <= 0.01:
                continue

            m0_new = m_fixed / denom_new

            cmat_total = (wing_res['cmat_factor'] + fuse_res['cmat_factor'] + tail_res['cmat_factor']) * m0_new
            cla_i = NLA * cmat_total

            ctrud_total = wing_res['ctrud'] + fuse_res['ctrud'] + tail_res['ctrud']
            cosn_total = wing_res['cosn'] + fuse_res['cosn'] + tail_res['cosn']
            spr_total = wing_res['spr'] + fuse_res['spr'] + tail_res['spr']
            workers_total = wing_res['workers'] + fuse_res['workers'] + tail_res['workers']

            svpm = spr_total * (
                        db.globals.k_skl * db.globals.k_oper * db.globals.k_prod * db.globals.k_ras * db.globals.k_vspom)
            sb = workers_total * db.globals.k_sb
            sadm = workers_total * db.globals.k_adm * db.globals.s_k_adm

            cspl = (spr_total + svpm + sb + sadm) * db.globals.c_1m
            csum = (cla_i + cosn_total + ctrud_total + cspl) * db.globals.k_prib

            seb_1 = csum / NLA

            if seb_1 < best_cost:
                best_cost = seb_1
                best_combo_names = {
                    "wing": wing_combo,
                    "fuselage": fuse_combo,
                    "tail": tail_combo,
                }
                best_details = {
                    "m0_new": m0_new,
                    "CSUM_total": float(csum),
                    "CLA_I_materials": float(cla_i),
                    "COSN_machines": float(cosn_total),
                    "CTRUD_labor": float(ctrud_total),
                    "CSPL_space": float(cspl),
                }

        logger.info("Оптимальная сборка найдена.")

        # 4. Запись результатов обратно в проект
        tech.best_cost_seb1 = float(best_cost)
        tech.m0_new = best_details.get("m0_new", m_mto_initial)
        tech.CSUM_total = best_details.get("CSUM_total", 0.0)
        tech.CLA_I_materials = best_details.get("CLA_I_materials", 0.0)
        tech.COSN_machines = best_details.get("COSN_machines", 0.0)
        tech.CTRUD_labor = best_details.get("CTRUD_labor", 0.0)
        tech.CSPL_space = best_details.get("CSPL_space", 0.0)

        if best_combo_names:
            def split_tech(t_str):
                mat, idx = t_str.split("_")
                return mat, int(idx)

            w_skin_m, w_skin_i = split_tech(best_combo_names["wing"][0])
            w_long_m, w_long_i = split_tech(best_combo_names["wing"][1])
            w_trans_m, w_trans_i = split_tech(best_combo_names["wing"][2])

            tech.wing_skin_tech = resolve_technology_name("wing", "skin", w_skin_m, w_skin_i)
            tech.wing_long_tech = resolve_technology_name("wing", "longitudinal", w_long_m, w_long_i)
            tech.wing_trans_tech = resolve_technology_name("wing", "transverse", w_trans_m, w_trans_i)

            f_skin_m, f_skin_i = split_tech(best_combo_names["fuselage"][0])
            f_long_m, f_long_i = split_tech(best_combo_names["fuselage"][1])
            f_trans_m, f_trans_i = split_tech(best_combo_names["fuselage"][2])

            tech.fuse_skin_tech = resolve_technology_name("fuselage", "skin", f_skin_m, f_skin_i)
            tech.fuse_long_tech = resolve_technology_name("fuselage", "longitudinal", f_long_m, f_long_i)
            tech.fuse_trans_tech = resolve_technology_name("fuselage", "transverse", f_trans_m, f_trans_i)

            t_skin_m, t_skin_i = split_tech(best_combo_names["tail"][0])
            t_long_m, t_long_i = split_tech(best_combo_names["tail"][1])
            t_trans_m, t_trans_i = split_tech(best_combo_names["tail"][2])

            tech.tail_skin_tech = resolve_technology_name("tail", "skin", t_skin_m, t_skin_i)
            tech.tail_long_tech = resolve_technology_name("tail", "longitudinal", t_long_m, t_long_i)
            tech.tail_trans_tech = resolve_technology_name("tail", "transverse", t_trans_m, t_trans_i)

        project.add_trace(
            value_name="Уравнение суммарной стоимости партии",
            formula=r"C_{\Sigma} = (C_{мат} \cdot N_{LA} + C_{осн} + C_{труд} + C_{пл}) \cdot k_{приб}",
            values={
                "CLA_I_materials": tech.CLA_I_materials,
                "COSN_machines": tech.COSN_machines,
                "CTRUD_labor": tech.CTRUD_labor,
                "CSPL_space": tech.CSPL_space
            },
            result=float(tech.CSUM_total),
            unit="руб.",
            description="Формирование суммарной производственной стоимости для оптимальной комбинации технологий."
        )

        project.add_trace(
            value_name="best_cost_seb1",
            formula=r"C_{SEB1} = \frac{C_{\Sigma}}{N_{LA}}",
            values={"C_sum": tech.CSUM_total, "NLA": NLA},
            result=float(best_cost),
            unit="руб.",
            description="Минимальная расчетная себестоимость 1 экземпляра."
        )

    def _calc_component(self, comp_name: str, combo: tuple, db: Any, TLA: float, T: float,
                        m_old_relative: float) -> dict[str, float]:
        parts = ['skin', 'longitudinal', 'transverse']
        cmat_factor_sum, ctrud_sum, spr_sum = 0.0, 0.0, 0.0
        workers_sum, cosn_sum, mel_total = 0.0, 0.0, 0.0

        for part, tech_name in zip(parts, combo):
            nel_val = getattr(getattr(db.nel, comp_name).__dict__[tech_name], part)
            if nel_val <= 0:
                continue

            ndet_val = getattr(getattr(db.ndet, comp_name).__dict__[tech_name], part)
            mel_table_val = getattr(getattr(db.m_el, comp_name).__dict__[tech_name], part)
            mel_val = mel_table_val * m_old_relative
            kim_val = getattr(getattr(db.kim, comp_name).__dict__[tech_name], part)
            c1_val = getattr(getattr(db.c1, comp_name).__dict__[tech_name], part)
            cst1_val = getattr(getattr(db.cst1, comp_name).__dict__[tech_name], part)
            nrb_val = getattr(getattr(db.nrb, comp_name).__dict__[tech_name], part)
            cnrb_val = getattr(getattr(db.cnrb, comp_name).__dict__[tech_name], part)
            s1_val = getattr(getattr(db.s1, comp_name).__dict__[tech_name], part)

            mel_total += mel_val
            nelpotr = TLA * nel_val

            if ndet_val > 0:
                nstan_raw = nelpotr / ndet_val
                if nstan_raw == 0:
                    nstan = 0
                elif nstan_raw < 1.1:
                    nstan = 1
                else:
                    nstan = math.floor(nstan_raw + 0.9)
            else:
                nstan = 0

            if kim_val > 0:
                mmat_factor = mel_val / kim_val
                cmat_factor_sum += mmat_factor * c1_val

            ctrud_sum += 1.3 * nstan * nrb_val * cnrb_val * T
            spr_sum += nstan * s1_val
            workers_sum += nstan * nrb_val
            cosn_sum += nstan * cst1_val

        return {
            'cmat_factor': cmat_factor_sum, 'ctrud': ctrud_sum, 'spr': spr_sum,
            'workers': workers_sum, 'cosn': cosn_sum, 'mel_total': mel_total
        }