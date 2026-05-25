from __future__ import annotations

import argparse
import logging

from aircraft_design.logging_config import configure_logging

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
        help="Path to output TXT file.",
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

    if args.mode == "gui":
        logger.info("GUI mode is not connected to the new core yet")
        raise NotImplementedError("GUI mode will be connected in a later step")

    if args.mode == "batch":
        logger.info("Batch mode requested")
        logger.info("Input path: %s", args.input_path)
        logger.info("Output path: %s", args.output_path)
        raise NotImplementedError("Batch mode will be implemented after JSON input is ready")

    if args.mode == "validate":
        logger.info("Validation mode requested")
        logger.info("Input path: %s", args.input_path)
        raise NotImplementedError("Validation mode will be implemented after JSON schema is ready")

    parser.error(f"Unsupported mode: {args.mode}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())