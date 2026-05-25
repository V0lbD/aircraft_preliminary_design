from __future__ import annotations

import argparse
import logging
from pathlib import Path

from aircraft_design.core.errors import AircraftDesignError
from aircraft_design.io import load_project_input, write_json_result, write_txt_result
from aircraft_design.logging_config import configure_logging

from aircraft_design.app import run_calculation

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aircraft-design",
        description="Aircraft preliminary design calculation tool",
    )

    parser.add_argument(
        "--mode",
        choices=["gui", "batch", "validate"],
        default="gui",
        help="Run mode: gui, batch or validate.",
    )

    parser.add_argument(
        "--input",
        dest="input_path",
        help="Path to input JSON file.",
    )

    parser.add_argument(
        "--output",
        dest="output_path",
        default="outputs/result.txt",
        help="Path to output TXT file.",
    )

    parser.add_argument(
        "--output-format",
        choices=["txt", "json"],
        default=None,
        help=(
            "Output format. If omitted, format is inferred from output file "
            "extension; otherwise TXT is used by default."
        ),
    )

    parser.add_argument(
        "--trace",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Enable calculation trace. "
            "Use --no-trace to disable detailed formula trace."
        ),
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )

    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional path to log file.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(level=args.log_level, log_file=args.log_file)

    logger.info("Application started")
    logger.info("Mode: %s", args.mode)

    try:
        if args.mode == "gui":
            logger.info("GUI mode is not connected to the new core yet")
            raise NotImplementedError("GUI mode will be connected in a later step")

        if args.mode == "validate":
            return run_validate_mode(args, parser)

        if args.mode == "batch":
            return run_batch_mode(args, parser)

    except AircraftDesignError as exc:
        logger.error("%s", exc)
        return 1

    except NotImplementedError as exc:
        logger.error("%s", exc)
        return 1

    except Exception:
        logger.exception("Unexpected application error")
        return 1

    parser.error(f"Unsupported mode: {args.mode}")
    return 2


def run_validate_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.input_path:
        parser.error("--input is required for validate mode")

    project_input = load_project_input(args.input_path)

    logger.info("Input file is valid: %s", args.input_path)
    logger.info("Schema version: %s", project_input.schema_version)

    print(f"Input file is valid: {args.input_path}")
    return 0


def run_batch_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.input_path:
        parser.error("--input is required for batch mode")

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    output_format = resolve_output_format(output_path, args.output_format)

    logger.info("Loading input file: %s", input_path)
    project_input = load_project_input(input_path)

    logger.info("Running calculation")
    result = run_calculation(
        project_input,
        trace_enabled=args.trace,
    )

    logger.info("Writing %s result file: %s", output_format, output_path)

    if output_format == "json":
        write_json_result(result, output_path)
    else:
        write_txt_result(result, output_path)

    print(f"{output_format.upper()} result written to: {output_path}")
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


if __name__ == "__main__":
    raise SystemExit(main())