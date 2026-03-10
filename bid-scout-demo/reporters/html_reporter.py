"""HTML 报告生成。"""

from __future__ import annotations

import html
import logging
from datetime import datetime
from pathlib import Path

from config import REPORT_HTML_PATH

logger = logging.getLogger(__name__)

_LEVEL_LABELS = {
    "high": ("高相关", "#2e7d32", "#e8f5e9"),
    "medium": ("中相关", "#f57f17", "#fff8e1"),
    "low-medium": ("低-中相关", "#e65100", "#fff3e0"),
    "low": ("低相关", "#757575", "#f5f5f5"),
}


def _relevance_badge(score: float) -> tuple[str, str, str]:
    if score >= 0.8:
        return _LEVEL_LABELS["high"]
    if score >= 0.5:
        return _LEVEL_LABELS["medium"]
    if score >= 0.2:
        return _LEVEL_LABELS["low-medium"]
    return _LEVEL_LABELS["low"]


def _esc(text: str) -> str:
    return html.escape(text or "", quote=True)


def write_html_report(
    items: list[dict],
    errors: list[str],
    sources: list[str],
    output_path: Path | None = None,
) -> Path:
    path = output_path or REPORT_HTML_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_names = {
        "tab_gz_tyj": "广州市体育局",
        "tab_gdgpo": "广东政府采购网",
    }

    rows_html = []
    for idx, item in enumerate(items, 1):
        label, color, bg = _relevance_badge(item.get("match_score", 0))
        reasons = "<br>".join(_esc(r) for r in item.get("match_reason", []))
        site_name = source_names.get(item.get("source_site", ""), item.get("source_site", ""))

        rows_html.append(f"""
        <tr>
          <td>{idx}</td>
          <td>{_esc(site_name)}</td>
          <td><a href="{_esc(item.get('url', '#'))}" target="_blank">{_esc(item.get('title', ''))}</a></td>
          <td>{_esc(item.get('publish_date', ''))}</td>
          <td><span class="badge" style="background:{bg};color:{color}">{label}</span><br>
              <small>{item.get('match_score', 0):.2f}</small></td>
          <td><small>{reasons or '-'}</small></td>
          <td><details><summary>展开</summary><p>{_esc(item.get('summary', ''))}</p></details></td>
        </tr>""")

    error_items = "".join(f"<li>{_esc(e)}</li>" for e in errors) if errors else "<li>无</li>"

    page_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>体育服务运营招投标采集报告</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f0f2f5; color: #333; padding: 24px; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; border-left: 4px solid #1565c0; padding-left: 12px; margin-bottom: 8px; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-bottom: 20px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #1565c0; color: #fff; padding: 10px 8px; text-align: left; font-size: 0.85rem; }}
  td {{ padding: 10px 8px; border-bottom: 1px solid #eee; font-size: 0.85rem; vertical-align: top; }}
  tr:hover {{ background: #f5f8ff; }}
  a {{ color: #1565c0; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }}
  details summary {{ cursor: pointer; color: #1565c0; font-size: 0.82rem; }}
  details p {{ margin-top: 6px; color: #555; line-height: 1.5; }}
  .errors {{ color: #c62828; }}
  .footer {{ text-align: center; color: #999; font-size: 0.8rem; margin-top: 24px; }}
</style>
</head>
<body>
<div class="container">
  <h1>体育服务运营类招投标信息采集报告</h1>
  <p class="meta">运行时间: {now} &nbsp;|&nbsp; 数据来源: {', '.join(source_names.get(s, s) for s in sources)} &nbsp;|&nbsp; 共 {len(items)} 条</p>

  <div class="card">
    <table>
      <thead>
        <tr>
          <th>#</th><th>来源</th><th>标题</th><th>发布日期</th><th>相关度</th><th>匹配原因</th><th>摘要</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html) if rows_html else '<tr><td colspan="7" style="text-align:center;color:#999">暂无数据</td></tr>'}
      </tbody>
    </table>
  </div>

  <div class="card errors">
    <h3>异常信息</h3>
    <ul>{error_items}</ul>
  </div>

  <p class="footer">由 BidScout Demo (OpenClaw) 自动生成</p>
</div>
</body>
</html>"""

    path.write_text(page_html, encoding="utf-8")
    logger.info("HTML 报告已写入: %s", path)
    return path
