import argparse
import logging
import json
from pathlib import Path

from aircraft_design.app import run_calculation
from aircraft_design.core.models.project import ProjectState
from aircraft_design.io.json_io import load_project_from_json, save_project_to_json, create_input_template
from aircraft_design.io.tech_db_loader import load_technology_database_into_project

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aircraft-design",
        description="Программа предварительного проектирования самолета (расчет параметров, масс, геометрии и технологий).",
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "batch", "template"],
        default="gui",
        help="Режим работы программы: gui — графический интерфейс (по умолчанию), batch — пакетный расчет файла, template — генерация шаблона входных данных.",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        help="Путь к входному файлу проекта в формате JSON (обязателен для режима batch).",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default="outputs/result.json",
        help="Путь для сохранения результирующего JSON файла или шаблона (по умолчанию: outputs/result.json).",
    )
    parser.add_argument(
        "--export-dat",
        dest="dat_path",
        default=None,
        help="Опциональный путь для экспорта параметров геометрии в формат .dat для 3D-моделирования.",
    )
    parser.add_argument(
        "--export-trace",
        dest="trace_path",
        default=None,
        help="Опциональный путь для экспорта отчета с формулами (.md).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.mode == "gui":
        from aircraft_design.ui.run import run_gui_application
        return run_gui_application()

    if args.mode == "template":
        return run_template_mode(args)

    if args.mode == "batch":
        if not args.input_path:
            parser.error("Для пакетного режима (batch) требуется параметр --input")

        project = ProjectState()
        # Подгрузка БД технологий...

        load_project_from_json(project, Path(args.input_path))

        load_technology_database_into_project(project)

        success = run_calculation(project)
        save_project_to_json(project, Path(args.output_path))

        if args.dat_path:
            from aircraft_design.io.dat_writer import write_3d_dat
            write_3d_dat(project, Path(args.dat_path))
            print(f"Файл 3D-модели сохранён в: {args.dat_path}")

        if args.trace_path:
            from aircraft_design.io.trace_writer import write_trace_markdown
            write_trace_markdown(project, Path(args.trace_path))
            print(f"Отчет с формулами сохранён в: {args.trace_path}")

        return 0 if success else 1


def run_template_mode(args: argparse.Namespace) -> int:
    output_path = Path(args.output_path)
    if output_path.suffix != ".json":
        output_path = output_path.with_suffix(".json")

    project = ProjectState()
    template_data = create_input_template(project)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(template_data, indent=4, ensure_ascii=False), encoding="utf-8")

    print(f"Шаблон ввода сохранён в: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())