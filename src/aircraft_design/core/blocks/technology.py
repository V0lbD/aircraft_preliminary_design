from __future__ import annotations

import itertools
import logging
import math
from typing import Any

from aircraft_design.core.blocks.base import BaseBlock
from aircraft_design.core.errors import InputValidationError
from aircraft_design.core.models import CalculationState
from aircraft_design.core.models.technology import TechnologyDatabase
from aircraft_design.core.models import BlockInputSchema, CalculationState, ParameterSpec

logger = logging.getLogger(__name__)


class TechnologyBlock(BaseBlock):
    """
    Блок производственно-экономической оптимизации (Design for Manufacturing).
    Выбирает оптимальную комбинацию технологий изготовления для минимизации себестоимости.
    """

    name = "technology"
    required_input_sections = ()

    input_schema = BlockInputSchema(
        section_name="metadata",
        block_name="technology",
        display_name="Параметры производства",
        description="Данные для экономического расчёта и планирования",
        parameters=(
            ParameterSpec(name="NLA", display_name="Количество ЛА в партии", value_type="number", description="",
                          unit="шт", default=100.0),
            ParameterSpec(name="T", display_name="Срок выполнения заказа", value_type="number", description="",
                          unit="нед", default=50.0),
        )
    )

    def validate(self, state: CalculationState) -> None:
        super().validate(state)

        if not hasattr(state.project_input, "technology_db") or state.project_input.technology_db is None:
            raise InputValidationError("База данных технологий (Excel) не загружена в проект.")

        if "mass_estimation" not in state.data:
            raise InputValidationError("Блок technology требует выполнения блока mass_estimation.")

    def calculate(self, state: CalculationState) -> dict[str, Any]:
        db: TechnologyDatabase = state.project_input.technology_db
        mass_outputs = state.data["mass_estimation"]

        # Получаем исходные массы для пересчета M0
        m_mto_initial = mass_outputs.get("m_MTO", 0.0)
        comp_masses = mass_outputs.get("component_masses", {})
        m_fixed = comp_masses.get("payload", 0.0) + comp_masses.get("service_load", 0.0)

        # Надежный способ получения старых относительных масс
        m_kr_old = comp_masses.get("wing", 0.0) / m_mto_initial if m_mto_initial else 0.0
        m_fuse_old = comp_masses.get("fuselage", 0.0) / m_mto_initial if m_mto_initial else 0.0
        m_tail_old = comp_masses.get("tail", 0.0) / m_mto_initial if m_mto_initial else 0.0

        denom_old = m_fixed / m_mto_initial if m_mto_initial > 0 else 1.0

        NLA = float(getattr(state.project_input.metadata, "NLA", 100))
        T = float(getattr(state.project_input.metadata, "T", 50))
        TLA = NLA / T

        alum_techs = ["alum_1", "alum_2"]
        comp_techs = ["comp_1", "comp_2"]
        valid_component_combos = (
                list(itertools.product(alum_techs, repeat=3)) +
                list(itertools.product(comp_techs, repeat=3))
        )

        best_cost = float("inf")
        best_combination = None
        best_details = {}

        logger.info(f"Начало перебора {len(valid_component_combos) ** 3} комбинаций технологий...")

        for wing_combo, fuse_combo, tail_combo in itertools.product(valid_component_combos, repeat=3):

            # 1. Расчет компонентов с передачей старой относительной массы!
            wing_res = self._calc_component('wing', wing_combo, db, TLA, T, m_kr_old)
            fuse_res = self._calc_component('fuselage', fuse_combo, db, TLA, T, m_fuse_old)
            tail_res = self._calc_component('tail', tail_combo, db, TLA, T, m_tail_old)

            # 2. Пересчет новой массы самолета M0
            m_kr_new = wing_res['mel_total']
            m_fuse_new = fuse_res['mel_total']
            m_tail_new = tail_res['mel_total']

            delta_struct = (m_kr_new + m_fuse_new + m_tail_new) - (m_kr_old + m_fuse_old + m_tail_old)
            denom_new = denom_old - delta_struct

            if denom_new <= 0.01:
                continue

            m0_new = m_fixed / denom_new

            # 3. Суммирование материалов
            cmat_total = (wing_res['cmat_factor'] + fuse_res['cmat_factor'] + tail_res['cmat_factor']) * m0_new
            cla_i = NLA * cmat_total

            # 4. Расчет остальной экономики
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
                best_combination = {
                    "wing": wing_combo,
                    "fuselage": fuse_combo,
                    "tail": tail_combo,
                }
                best_details = {
                    "m0_new": m0_new,
                    "SEB_1": float(seb_1),
                    "CSUM_total": float(csum),
                    "CLA_I_materials": float(cla_i),
                    "COSN_machines": float(cosn_total),
                    "CTRUD_labor": float(ctrud_total),
                    "CSPL_space": float(cspl),
                    "m_kr_relative": m_kr_new,
                    "m_fuse_relative": m_fuse_new,
                    "m_tail_relative": m_tail_new,
                }

        logger.info("Оптимальная сборка найдена.")

        return {
            "best_combination": best_combination,
            "best_cost_seb1": float(best_cost),
            "details": best_details
        }

    def _calc_component(self, comp_name: str, combo: tuple, db: TechnologyDatabase, TLA: float, T: float,
                        m_old_relative: float) -> dict[str, float]:
        parts = ['skin', 'longitudinal', 'transverse']

        cmat_factor_sum = 0.0
        ctrud_sum = 0.0
        spr_sum = 0.0
        workers_sum = 0.0
        cosn_sum = 0.0
        mel_total = 0.0

        for part, tech_name in zip(parts, combo):
            nel_val = getattr(getattr(db.nel, comp_name).__dict__[tech_name], part)
            if nel_val <= 0:
                continue

            ndet_val = getattr(getattr(db.ndet, comp_name).__dict__[tech_name], part)

            # Читаем долю из таблицы и УМНОЖАЕМ на старую относительную массу агрегата!
            mel_table_val = getattr(getattr(db.m_el, comp_name).__dict__[tech_name], part)
            mel_val = mel_table_val * m_old_relative

            kim_val = getattr(getattr(db.kim, comp_name).__dict__[tech_name], part)
            c1_val = getattr(getattr(db.c1, comp_name).__dict__[tech_name], part)
            cst1_val = getattr(getattr(db.cst1, comp_name).__dict__[tech_name], part)
            nrb_val = getattr(getattr(db.nrb, comp_name).__dict__[tech_name], part)
            cnrb_val = getattr(getattr(db.cnrb, comp_name).__dict__[tech_name], part)
            s1_val = getattr(getattr(db.s1, comp_name).__dict__[tech_name], part)

            mel_total += mel_val

            # 2. NELPOTR
            nelpotr = TLA * nel_val

            # 3. NSTAN
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

            # 5 & 6. MMAT и CMAT
            if kim_val > 0:
                mmat_factor = mel_val / kim_val
                cmat_factor_sum += mmat_factor * c1_val

            # 7. CTRUD
            ctrud_sum += 1.3 * nstan * nrb_val * cnrb_val * T

            # 8. SPR
            spr_sum += nstan * s1_val
            workers_sum += nstan * nrb_val

            # 13. COSN
            cosn_sum += nstan * cst1_val

        return {
            'cmat_factor': cmat_factor_sum,
            'ctrud': ctrud_sum,
            'spr': spr_sum,
            'workers': workers_sum,
            'cosn': cosn_sum,
            'mel_total': mel_total
        }