from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
) -> None:
    """
    Configure application logging.

    Parameters
    ----------
    level:
        Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL.
    log_file:
        Optional path to log file.
    """
    numeric_level = getattr(logging, level.upper(), None)

    if not isinstance(numeric_level, int):
        raise ValueError(f"Unknown logging level: {level}")

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    if log_file is not None:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )