#!/usr/bin/env python3
"""CSV 报告生成工具。

用法:
    python3 generate_csv.py --input filtered.json --output report.csv
    cat filtered.json | python3 generate_csv.py --output report.csv

输出列: 来源站点, 标题, 发布日期, URL, 摘要, 匹配分数, 匹配等级, 匹配原因
默认 utf-8-sig 编码以兼容 Excel 中文显示。

退出码: 0 成功, 1 失败
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from io import StringIO
from pathlib import Path

CSV_COLUMNS = [
    ("source_site", "来源站点"),
    ("title", "标题"),
    ("publish_date", "发布日期"),
    ("url", "URL"),
    ("purchaser", "采购人"),
    ("budget", "预算金额"),
    ("summary", "摘要"),
    ("detail_text", "详情正文"),
    ("match_score", "匹配分数"),
    ("match_level", "匹配等级"),
    ("match_reason", "匹配原因"),
]


def items_to_csv(items: list[dict], encoding: str = "utf-8-sig") -> bytes:
    """将条目列表转为 CSV 字节流。"""
    buf = StringIO()
    writer = csv.writer(buf)

    writer.writerow([col[1] for col in CSV_COLUMNS])

    for item in items:
        row: list[str] = []
        for key, _ in CSV_COLUMNS:
            value = item.get(key, "")
            if isinstance(value, list):
                value = "; ".join(str(v) for v in value)
            elif isinstance(value, float):
                value = f"{value:.2f}"
            row.append(str(value))
        writer.writerow(row)

    return buf.getvalue().encode(encoding)


def main() -> int:
    parser = argparse.ArgumentParser(description="招投标 CSV 报告生成工具")
    parser.add_argument("--input", "-i", help="输入 JSON 文件路径 (省略则从 stdin 读取)")
    parser.add_argument("--output", "-o", required=True, help="输出 CSV 文件路径")
    parser.add_argument(
        "--encoding", default="utf-8-sig",
        help="CSV 编码 (默认 utf-8-sig 兼容 Excel)",
    )
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

        csv_bytes = items_to_csv(items, encoding=args.encoding)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(csv_bytes)

        print(f"已生成 CSV 报告: {args.output} ({len(items)} 条记录)", file=sys.stderr)
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
