from pathlib import Path

from aircraft_design.core.models.project import ProjectState

def write_3d_dat(project: ProjectState, path: str | Path) -> None:
    """Экспорт геометрических параметров в формат .dat для 3D-моделирования."""
    geom = project.geometry

    lines = [
        # Крыло
        f"{geom.l_wing:.3f}",
        f"{geom.b0_wing:.3f}",
        f"{geom.bk_wing:.3f}",
        f"{geom.sweep_wing_LE:.3f}",
        f"{geom.y_wing:.3f}",
        "",
        # Горизонтальное оперение (ГО)
        f"{geom.l_ht:.3f}",
        f"{geom.b0_ht:.3f}",
        f"{geom.bk_ht:.3f}",
        f"{geom.sweep_ht_LE:.3f}",
        f"{geom.x_ht:.3f}",
        f"{geom.y_ht:.3f}",
        "",
        # Вертикальное оперение (ВО)
        f"{geom.l_vt:.3f}",
        f"{geom.b0_vt:.3f}",
        f"{geom.bk_vt:.3f}",
        f"{geom.sweep_vt_LE:.3f}",
        f"{geom.x_vt:.3f}",
        "",
        # Фюзеляж
        f"{geom.L_fuselage:.3f}",
        f"{geom.r_fuselage:.3f}",  # Max radius
        f"{geom.x_fuselage:.3f}",
        ""
    ]

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")