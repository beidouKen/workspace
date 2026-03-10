"""JSON 报告输出。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from config import REPORT_JSON_PATH

logger = logging.getLogger(__name__)


def write_json_report(
    items: list[dict],
    errors: list[str],
    sources: list[str],
    output_path: Path | None = None,
) -> Path:
    path = output_path or REPORT_JSON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": sources,
        "total_items": len(items),
        "items": items,
        "errors": errors,
    }

    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("JSON 报告已写入: %s", path)
    return path
