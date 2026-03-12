#!/usr/bin/env python3
"""关键词筛选与相关度打分 CLI 工具。

用法:
    python3 keyword_filter.py --input raw.json --output filtered.json
    cat raw.json | python3 keyword_filter.py > filtered.json

打分逻辑:
    同时命中体育词 + 服务运营词 → high  (0.8 ~ 1.0)
    仅命中体育词                → medium (0.5 ~ 0.7)
    仅命中服务运营词            → low-medium (0.2 ~ 0.4)
    均未命中                    → low (0.0)

退出码: 0 成功, 1 失败
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

SPORTS_KEYWORDS: list[str] = [
    "体育", "运动", "全民健身", "健身", "体育馆",
    "体育中心", "场馆", "赛事",
]

SERVICE_KEYWORDS: list[str] = [
    "服务", "运营", "管理", "承办", "培训",
    "维护", "保障", "活动组织", "执行",
]


@dataclass
class FilterResult:
    score: float
    level: str
    reasons: list[str]


def score_text(text: str) -> FilterResult:
    """对给定文本进行关键词匹配打分。"""
    if not text:
        return FilterResult(score=0.0, level="low", reasons=[])

    sports_hits: list[str] = [kw for kw in SPORTS_KEYWORDS if kw in text]
    service_hits: list[str] = [kw for kw in SERVICE_KEYWORDS if kw in text]

    reasons: list[str] = []
    if sports_hits:
        reasons.append(f"命中体育词: {', '.join(sports_hits)}")
    if service_hits:
        reasons.append(f"命中服务运营词: {', '.join(service_hits)}")

    has_sports = len(sports_hits) > 0
    has_service = len(service_hits) > 0

    if has_sports and has_service:
        score = min(1.0, 0.8 + 0.05 * (len(sports_hits) + len(service_hits) - 2))
        return FilterResult(score=score, level="high", reasons=reasons)

    if has_sports:
        score = min(0.7, 0.5 + 0.05 * (len(sports_hits) - 1))
        return FilterResult(score=score, level="medium", reasons=reasons)

    if has_service:
        score = min(0.4, 0.2 + 0.05 * (len(service_hits) - 1))
        return FilterResult(score=score, level="low-medium", reasons=reasons)

    return FilterResult(score=0.0, level="low", reasons=["未命中任何关键词"])


def apply_filter(items: list[dict]) -> list[dict]:
    """对条目列表做关键词打分，就地更新 match_score / match_reason / match_level。"""
    for item in items:
        combined = " ".join([
            item.get("title", ""),
            item.get("summary", ""),
            item.get("detail_text", ""),
        ])
        result = score_text(combined)
        item["match_score"] = result.score
        item["match_reason"] = "; ".join(result.reasons)
        item["match_level"] = result.level
    items.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="招投标关键词筛选打分工具")
    parser.add_argument("--input", "-i", help="输入 JSON 文件路径 (省略则从 stdin 读取)")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径 (省略则写入 stdout)")
    args = parser.parse_args()

    try:
        if args.input:
            raw = Path(args.input).read_text(encoding="utf-8")
        else:
            raw = sys.stdin.read()

        items = json.loads(raw)
        if not isinstance(items, list):
            print("错误: 输入必须是 JSON 数组", file=sys.stderr)
            return 1

        filtered = apply_filter(items)
        output_json = json.dumps(filtered, ensure_ascii=False, indent=2)

        if args.output:
            Path(args.output).write_text(output_json, encoding="utf-8")
            print(f"已写入 {len(filtered)} 条筛选结果到 {args.output}", file=sys.stderr)
        else:
            print(output_json)

        return 0

    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"文件未找到: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
