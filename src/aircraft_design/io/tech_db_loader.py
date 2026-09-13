from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
import pandas as pd

from aircraft_design.core.models.project import ProjectState

logger = logging.getLogger(__name__)

def get_resource_path(relative_path: str) -> Path:
    """Ищет файлы рядом с .exe или в текущей папке при запуске из IDE."""
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path.cwd()
    return base_path / relative_path

def load_technology_database_into_project(project: ProjectState) -> None:
    """Загружает таблицы Excel (1-10) в project.databases['technology_db']."""
    db_path = get_resource_path("inputs/tables")
    if not db_path.is_dir():
        project.add_warning(f"Папка {db_path} не найдена. Блок технологий может завершиться ошибкой.")
        return

    file_map: dict[str, Path] = {}
    for f in db_path.glob("*.xlsx"):
        if match := re.match(r"^(\d+)", f.name):
            file_map[match.group(1)] = f

    table_keys = {
        "1": "nel", "2": "ndet", "3": "m_el", "4": "kim",
        "5": "c1", "6": "cst1", "7": "nrb", "8": "cnrb", "9": "s1",
    }

    def create_obj():
        return type("Obj", (object,), {})()

    db_dict = {}
    try:
        for num, key in table_keys.items():
            if num not in file_map:
                continue
            df = pd.read_excel(file_map[num], header=None)
            table_obj = create_obj()

            def parse_component(start_col: int):
                comp_obj = create_obj()
                tech_names = ["alum_1", "alum_2", "comp_1", "comp_2"]
                for i, tech in enumerate(tech_names):
                    tech_obj = create_obj()
                    tech_obj.skin = float(str(df.iloc[2 + i, start_col]).replace(",", ".")) if not pd.isna(df.iloc[2 + i, start_col]) else 0.0
                    tech_obj.transverse = float(str(df.iloc[2 + i, start_col + 1]).replace(",", ".")) if not pd.isna(df.iloc[2 + i, start_col + 1]) else 0.0
                    tech_obj.longitudinal = float(str(df.iloc[2 + i, start_col + 2]).replace(",", ".")) if not pd.isna(df.iloc[2 + i, start_col + 2]) else 0.0
                    setattr(comp_obj, tech, tech_obj)
                return comp_obj

            table_obj.wing = parse_component(1)
            table_obj.fuselage = parse_component(4)
            table_obj.tail = parse_component(7)
            db_dict[key] = table_obj

        if "10" in file_map:
            df10 = pd.read_excel(file_map["10"], header=None)
            glob_obj = create_obj()
            keys = ["k_skl", "k_oper", "k_prod", "k_ras", "k_vspom", "k_sb", "k_adm", "s_k_adm", "c_1m", "k_prib"]
            for i, k in enumerate(keys):
                val = df10.iloc[i, 0]
                setattr(glob_obj, k, float(str(val).replace(",", ".")) if not pd.isna(val) else 0.0)
            db_dict["globals"] = glob_obj

        db_master = create_obj()
        for k, v in db_dict.items():
            setattr(db_master, k, v)

        project.databases["technology_db"] = db_master

    except Exception as exc:
        project.add_warning(f"Ошибка загрузки базы технологий: {exc}")
        logger.warning("Ошибка загрузки базы технологий: %s", exc)