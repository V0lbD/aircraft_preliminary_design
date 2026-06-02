from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_data(
    data: dict[str, Any],
    path: str | Path,
    *,
    indent: int = 2,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=indent,
        )
        + "\n",
        encoding="utf-8",
    )