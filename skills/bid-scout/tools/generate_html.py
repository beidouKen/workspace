#!/usr/bin/env python3
"""HTML 情报报告生成工具。

用法:
    python3 generate_html.py --input /tmp/bid_raw.json --output /tmp/bid_report.html

支持输入格式:
    - JSON 数组
    - 包含 "items" 字段的 JSON 对象

退出码: 0 成功, 1 失败
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from jinja2 import Environment
except ImportError:
    print("错误: 缺少 jinja2 库，请执行 pip install jinja2", file=sys.stderr)
    sys.exit(1)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>体育招投标情报报告</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Microsoft YaHei", sans-serif;
    background: #f0f2f5; color: #1d1d1f; line-height: 1.6; padding: 24px;
  }
  .container { max-width: 1200px; margin: 0 auto; }
  h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 8px; }
  .subtitle { color: #6e6e73; font-size: 0.9rem; margin-bottom: 24px; }

  /* 摘要卡片 */
  .summary-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin-bottom: 32px;
  }
  .summary-card {
    background: #fff; border-radius: 12px; padding: 20px; text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  .summary-card .num { font-size: 2rem; font-weight: 700; color: #0071e3; }
  .summary-card .label { font-size: 0.85rem; color: #6e6e73; margin-top: 4px; }

  /* 表格 */
  .table-wrap {
    background: #fff; border-radius: 12px; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 32px;
  }
  .table-wrap h2 { padding: 16px 20px 0; font-size: 1.1rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  th { background: #f5f5f7; text-align: left; padding: 10px 12px; font-weight: 600; white-space: nowrap; }
  td { padding: 10px 12px; border-top: 1px solid #e8e8ed; vertical-align: top; }
  tr:hover td { background: #f9f9fb; }

  /* 匹配等级标签 */
  .badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.78rem; font-weight: 600; }
  .badge-high { background: #d4edda; color: #155724; }
  .badge-medium { background: #fff3cd; color: #856404; }
  .badge-low-medium { background: #fde8d0; color: #7c4a1a; }
  .badge-low { background: #f8d7da; color: #721c24; }

  /* 折叠区 */
  details { margin-top: 6px; }
  details summary { cursor: pointer; color: #0071e3; font-size: 0.82rem; }
  details pre {
    background: #f5f5f7; padding: 12px; border-radius: 8px; margin-top: 6px;
    font-size: 0.78rem; white-space: pre-wrap; word-break: break-all; max-height: 300px; overflow-y: auto;
  }
  .detail-text { max-width: 600px; white-space: pre-wrap; word-break: break-all; font-size: 0.82rem; color: #444; }

  /* 异常区 */
  .anomaly-section { margin-bottom: 32px; }
  .anomaly-section h2 { font-size: 1.1rem; margin-bottom: 12px; }
  .anomaly-card {
    background: #fff; border-left: 4px solid #ff3b30; border-radius: 8px;
    padding: 12px 16px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    font-size: 0.85rem;
  }
  .anomaly-card .tag { display: inline-block; background: #f8d7da; color: #721c24; padding: 1px 8px; border-radius: 8px; font-size: 0.75rem; margin-right: 8px; }

  a { color: #0071e3; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .truncate { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }

  @media (max-width: 768px) {
    body { padding: 12px; }
    table { font-size: 0.8rem; }
    th, td { padding: 8px 6px; }
  }
</style>
</head>
<body>
<div class="container">

<h1>体育招投标情报报告</h1>
<p class="subtitle">生成时间: {{ report_time }}</p>

<!-- 摘要区 -->
<div class="summary-grid">
  <div class="summary-card">
    <div class="num">{{ total }}</div>
    <div class="label">总采集</div>
  </div>
  <div class="summary-card">
    <div class="num">{{ high_count }}</div>
    <div class="label">高匹配</div>
  </div>
  <div class="summary-card">
    <div class="num">{{ source_count }}</div>
    <div class="label">来源站点</div>
  </div>
  <div class="summary-card">
    <div class="num">{{ crawl_time_display }}</div>
    <div class="label">抓取时间</div>
  </div>
</div>

<!-- 主表格 -->
<div class="table-wrap">
  <h2>采集结果（共 {{ total }} 条）</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>标题</th>
        <th>发布日期</th>
        <th>来源</th>
        <th>匹配等级</th>
        <th>采购人</th>
        <th>预算</th>
        <th>摘要</th>
        <th>链接</th>
      </tr>
    </thead>
    <tbody>
    {% for item in items %}
      <tr>
        <td>{{ loop.index }}</td>
        <td>
          {{ item.title or "-" }}
          {% if item.detail_text %}
          <details>
            <summary>展开详情</summary>
            <div class="detail-text">{{ item.detail_text[:1000] }}</div>
          </details>
          {% endif %}
          {% if item.raw %}
          <details>
            <summary>原始 JSON</summary>
            <pre>{{ item.raw_json }}</pre>
          </details>
          {% endif %}
        </td>
        <td style="white-space:nowrap">{{ item.publish_date or "-" }}</td>
        <td style="white-space:nowrap">{{ item.source_site or "-" }}</td>
        <td>
          {% if item.match_level == "high" %}
            <span class="badge badge-high">高</span>
          {% elif item.match_level == "medium" %}
            <span class="badge badge-medium">中</span>
          {% elif item.match_level == "low-medium" %}
            <span class="badge badge-low-medium">低中</span>
          {% else %}
            <span class="badge badge-low">低</span>
          {% endif %}
        </td>
        <td>{{ item.purchaser or "-" }}</td>
        <td style="white-space:nowrap">{{ item.budget or "-" }}</td>
        <td><span class="truncate">{{ item.summary[:120] if item.summary else "-" }}</span></td>
        <td style="white-space:nowrap">
          {% if item.detail_url %}
            <a href="{{ item.detail_url }}" target="_blank">详情</a>
          {% elif item.url %}
            <a href="{{ item.url }}" target="_blank">列表</a>
          {% else %}
            -
          {% endif %}
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>

<!-- 异常区 -->
{% if anomalies %}
<div class="anomaly-section">
  <h2>异常条目（{{ anomalies | length }} 条）</h2>
  {% for a in anomalies %}
  <div class="anomaly-card">
    {% for tag in a.tags %}<span class="tag">{{ tag }}</span>{% endfor %}
    <strong>{{ a.title or "(无标题)" }}</strong>
    {% if a.source_site %} — {{ a.source_site }}{% endif %}
    {% if a.publish_date %} ({{ a.publish_date }}){% endif %}
  </div>
  {% endfor %}
</div>
{% endif %}

</div>
</body>
</html>"""


def extract_items(data: list | dict) -> list[dict]:
    """从输入中提取条目列表，兼容数组和对象两种格式。"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "items" in data:
        items = data["items"]
        if isinstance(items, list):
            return items
    raise ValueError("输入必须是 JSON 数组或包含 'items' 字段的 JSON 对象")


def build_anomalies(items: list[dict]) -> list[dict]:
    """提取异常条目：detail_url 未解析 或 data_quality=low。"""
    anomalies: list[dict] = []
    for item in items:
        tags: list[str] = []
        if item.get("detail_url_status") in ("unresolved_js_detail", "unresolved"):
            tags.append("detail_url 未解析")
        if item.get("data_quality") == "low":
            tags.append("数据质量低")
        if tags:
            anomalies.append({
                "title": item.get("title", ""),
                "source_site": item.get("source_site", ""),
                "publish_date": item.get("publish_date", ""),
                "tags": tags,
            })
    return anomalies


def render_html(items: list[dict]) -> str:
    """将条目列表渲染为 HTML 字符串。"""
    now = datetime.now(timezone.utc)
    report_time = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    sources = {item.get("source_site", "未知") for item in items}
    high_count = sum(1 for i in items if i.get("match_level") == "high")

    crawl_times = [i.get("crawl_time", "") for i in items if i.get("crawl_time")]
    crawl_time_display = crawl_times[0][:10] if crawl_times else now.strftime("%Y-%m-%d")

    for item in items:
        raw = item.get("raw")
        if raw and isinstance(raw, dict):
            item["raw_json"] = json.dumps(raw, ensure_ascii=False, indent=2)[:2000]
        else:
            item["raw_json"] = ""

    anomalies = build_anomalies(items)

    env = Environment(autoescape=True)
    template = env.from_string(HTML_TEMPLATE)
    return template.render(
        items=items,
        total=len(items),
        high_count=high_count,
        source_count=len(sources),
        crawl_time_display=crawl_time_display,
        report_time=report_time,
        anomalies=anomalies,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="招投标 HTML 情报报告生成工具")
    parser.add_argument("--input", "-i", required=True, help="输入 JSON 文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出 HTML 文件路径")
    args = parser.parse_args()

    try:
        raw = Path(args.input).read_text(encoding="utf-8")
        data = json.loads(raw)
        items = extract_items(data)

        html = render_html(items)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

        print(f"已生成 HTML 报告: {args.output} ({len(items)} 条记录)", file=sys.stderr)
        return 0

    except json.JSONDecodeError as e:
        print(f"JSON 解析错误: {e}", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
