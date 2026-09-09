import argparse
import logging
import json
from pathlib import Path

from aircraft_design.core.errors import AircraftDesignError
from aircraft_design.io import (
    load_project_input,
    write_project_result,
    write_trace_json,
    write_trace_markdown,
    write_txt_result,
)
from aircraft_design.logging_config import configure_logging
from aircraft_design.app import run_calculation
from aircraft_design.core.models import create_input_template, input_schemas_to_dict
from aircraft_design.core.pipeline import get_default_input_schemas
from aircraft_design.io.excel_loader import load_technology_database
from aircraft_design.ui.main_window import get_resource_path

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aircraft-design",
        description="Приложение предварительного проектирования самолета",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["gui", "batch", "validate", "schema", "template"],
        default="gui",
        help="Режим запуска:\n"
             "gui - запуск с интерфейсом;\n"
             "batch -автоматический режим;\n"
             "validate - проверка входного файла на корректность;\n"
             "schema - создание схемы для входного JSON;\n"
             "template - создание примера входного файла.",
    )

    parser.add_argument(
        "--input",
        dest="input_path",
        help="Путь к входному JSON-файлу.",
    )

    parser.add_argument(
        "--output",
        dest="output_path",
        default="outputs/result.txt",
        help="Путь к выходному файлу (по умолчанию TXT).",
    )

    parser.add_argument(
        "--output-format",
        choices=["txt", "json"],
        default=None,
        help=(
            "Формат выходного файла. Если не указан, определяется по расширению "
            "файла; в противном случае по умолчанию используется TXT."
        ),
    )

    parser.add_argument(
        "--trace",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Включить трассировку расчётов. "
            "Используйте --no-trace, чтобы отключить подробный вывод формул."
        ),
    )

    parser.add_argument(
        "--trace-md",
        dest="trace_md_path",
        default=None,
        help="Путь для сохранения файла трассировки расчётов в формате Markdown (удобном для чтения).",
    )

    parser.add_argument(
        "--trace-json",
        dest="trace_json_path",
        default=None,
        help="Путь для сохранения файла трассировки расчётов в формате JSON (машинно-читаемом).",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Уровень логирования.",
    )

    parser.add_argument(
        "--log-file",
        default=None,
        help="Опциональный путь к файлу логов.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(level=args.log_level, log_file=args.log_file)

    logger.info("Приложение Aircraft Design (версия 16.07.2026) запущено")
    logger.info("Режим: %s", args.mode)

    try:
        if args.mode == "gui":
            return run_gui_mode()

        if args.mode == "validate":
            return run_validate_mode(args, parser)

        if args.mode == "batch":
            return run_batch_mode(args, parser)

        if args.mode == "schema":
            return run_schema_mode(args)

        if args.mode == "template":
            return run_template_mode(args)

    except AircraftDesignError as exc:
        logger.error("%s", exc)
        return 1

    except NotImplementedError as exc:
        logger.error("%s", exc)
        return 1

    except Exception:
        logger.exception("Неожиданная ошибка приложения")
        return 1

    parser.error(f"Неподдерживаемый режим: {args.mode}")
    return 2


def run_validate_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.input_path:
        parser.error("Для режима проверки (validate) требуется параметр --input")

    project_input = load_project_input(args.input_path)

    logger.info("Входной файл действителен: %s", args.input_path)
    logger.info("Версия схемы: %s", project_input.schema_version)

    print(f"Входной файл действителен: {args.input_path}")
    return 0


def run_batch_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.input_path:
        parser.error("Для пакетного режима (batch) требуется параметр --input")

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    output_format = resolve_output_format(output_path, args.output_format)

    logger.info("Загрузка входного файла: %s", input_path)
    project_input = load_project_input(input_path)

    try:
        db_path = get_resource_path("inputs/tables")
        project_input.technology_db = load_technology_database(db_path)
    except Exception as e:
        print(f"Внимание: Ошибка загрузки базы технологий: {e}")

    logger.info("Запуск расчёта")
    result = run_calculation(
        project_input,
        trace_enabled=args.trace,
    )

    logger.info("Запись файла результатов в формате %s: %s", output_format, output_path)

    if output_format == "json":
        write_project_result(result, output_path)
    else:
        write_txt_result(result, output_path)

    if args.trace_md_path:
        trace_md_path = Path(args.trace_md_path)
        logger.info("Запись файла трассировки в формате Markdown: %s", trace_md_path)
        write_trace_markdown(result, trace_md_path)

    if args.trace_json_path:
        trace_json_path = Path(args.trace_json_path)
        logger.info("Запись файла трассировки в формате JSON: %s", trace_json_path)
        write_trace_json(result, trace_json_path)

    print(f"Результат в формате {output_format.upper()} сохранён в: {output_path}")
    return 0 if result.success else 1


def resolve_output_format(
    output_path: Path,
    requested_format: str | None,
) -> str:
    if requested_format is not None:
        return requested_format

    if output_path.suffix.lower() == ".json":
        return "json"

    return "txt"


def run_schema_mode(args: argparse.Namespace) -> int:
    output_path = Path(args.output_path)
    schemas = get_default_input_schemas()
    data = input_schemas_to_dict(schemas)

    logger.info("Запись файла схемы ввода: %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Схема ввода сохранена в: {output_path}")
    return 0

def run_template_mode(args: argparse.Namespace) -> int:
    output_path = Path(args.output_path)
    schemas = get_default_input_schemas()
    data = create_input_template(schemas)

    logger.info("Запись файла шаблона ввода: %s", output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Шаблон ввода сохранён в: {output_path}")
    return 0


def run_gui_mode() -> int:
    logger.info("Запуск графического интерфейса (GUI)")

    from aircraft_design.ui.run import run_gui_application

    return run_gui_application()

if __name__ == "__main__":
    raise SystemExit(main())