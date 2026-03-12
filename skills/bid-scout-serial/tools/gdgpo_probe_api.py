#!/usr/bin/env python3
"""广东省政府采购网 API 端点探测工具。

静态分析搜索页 HTML / JS bundle，尝试发现真实数据接口。

用法:
    python3 gdgpo_probe_api.py --output /tmp/gdgpo_probe.json
    python3 gdgpo_probe_api.py --config ../config/gdgpo_api.json --output /tmp/gdgpo_probe.json --verbose
    python3 gdgpo_probe_api.py --update-config ../config/gdgpo_api.json --output /tmp/gdgpo_probe.json

退出码: 0 成功（含部分探测失败）, 1 致命错误
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("错误: 缺少 requests 库，请执行 pip install requests", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger("gdgpo_probe")

SEARCH_PAGE_URL = "https://gdgpo.czt.gd.gov.cn/maincms-web/fullSearchingGd"
BASE_URL = "https://gdgpo.czt.gd.gov.cn"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL + "/",
}

API_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"""['"]([^'"]*(?:fullText|fullSearch|newText|getSearch|queryByPage|searchList|textSearch)[^'"]*?)['"]""", re.IGNORECASE),
    re.compile(r"""['"](/maincms-web/[^'"]{5,80})['"]"""),
    re.compile(r"""['"]([^'"]*?/api/[^'"]{3,80})['"]""", re.IGNORECASE),
]

PARAM_KEYWORDS = [
    "pageNum", "pageSize", "keyword", "searchKey", "keyWord",
    "pageNo", "page_size", "page_num", "currentPage", "searchWord",
    "queryKey", "fullText", "content", "totalCount", "totalPage",
]

PROBE_PAYLOADS: list[dict[str, Any]] = [
    {"keyword": "体育", "pageNum": 1, "pageSize": 10},
    {"keyWord": "体育", "pageNum": 1, "pageSize": 10},
    {"searchKey": "体育", "pageNum": 1, "pageSize": 10},
    {"keyword": "体育", "pageNo": 1, "pageSize": 10},
    {"keyword": "体育", "currentPage": 1, "pageSize": 10},
]


def fetch_page_html(session: requests.Session, url: str) -> tuple[bool, str, int]:
    """请求页面 HTML，返回 (是否成功, HTML内容, HTTP状态码)。"""
    try:
        resp = session.get(url, headers=BROWSER_HEADERS, timeout=30, allow_redirects=True)
        logger.info("GET %s -> %d (%d bytes)", url, resp.status_code, len(resp.text))
        return resp.status_code == 200, resp.text, resp.status_code
    except requests.RequestException as exc:
        logger.warning("请求页面失败: %s -> %s", url, exc)
        return False, "", 0


def extract_js_bundles(html: str, base_url: str) -> list[str]:
    """从 HTML 中提取 <script src="..."> 引用的 JS 文件 URL。"""
    pattern = re.compile(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']', re.IGNORECASE)
    raw_urls = pattern.findall(html)
    resolved: list[str] = []
    for raw in raw_urls:
        full = urljoin(base_url, raw)
        resolved.append(full)
    logger.info("发现 %d 个 JS bundle", len(resolved))
    return resolved


def analyze_bundle(session: requests.Session, js_url: str) -> list[dict[str, Any]]:
    """下载 JS bundle 并扫描 API 相关模式，返回候选端点列表。"""
    candidates: list[dict[str, Any]] = []
    try:
        resp = session.get(js_url, headers=BROWSER_HEADERS, timeout=30)
        if resp.status_code != 200:
            logger.warning("JS bundle 下载失败: %s -> %d", js_url, resp.status_code)
            return candidates
        js_text = resp.text
    except requests.RequestException as exc:
        logger.warning("JS bundle 请求异常: %s -> %s", js_url, exc)
        return candidates

    param_hits = [kw for kw in PARAM_KEYWORDS if kw in js_text]
    if param_hits:
        logger.info("JS %s 中发现参数关键词: %s", js_url.split("/")[-1], param_hits)

    for pattern in API_PATH_PATTERNS:
        for match in pattern.finditer(js_text):
            raw_path = match.group(1)
            if _is_noise_path(raw_path):
                continue

            confidence = _compute_confidence(raw_path, param_hits)
            context_start = max(0, match.start() - 80)
            context_end = min(len(js_text), match.end() + 80)
            context_snippet = js_text[context_start:context_end].replace("\n", " ").strip()

            method = "POST"
            if re.search(r'\.get\s*\(', js_text[max(0, match.start() - 30):match.start()], re.IGNORECASE):
                method = "GET"

            full_url = raw_path if raw_path.startswith("http") else urljoin(BASE_URL, raw_path)
            candidates.append({
                "url": full_url,
                "raw_path": raw_path,
                "method": method,
                "confidence": round(confidence, 2),
                "reason": f"bundle={js_url.split('/')[-1]}, params={param_hits[:5]}, context={context_snippet[:120]}",
                "source_bundle": js_url,
            })

    return candidates


def _is_noise_path(path: str) -> bool:
    """过滤明显不是 API 的路径（静态资源、第三方等）。"""
    noise_patterns = [
        ".css", ".png", ".jpg", ".svg", ".gif", ".woff", ".ttf",
        ".map", "node_modules", "chunk-", "vendor", "polyfill",
        "webpack", "sourcemap", "favicon",
    ]
    lower = path.lower()
    return any(n in lower for n in noise_patterns)


def _compute_confidence(path: str, param_hits: list[str]) -> float:
    """根据路径名和参数命中计算置信度。"""
    score = 0.3

    path_lower = path.lower()
    high_signal_terms = ["fulltext", "search", "fullsearch", "textsearch", "searchlist", "getlist"]
    medium_signal_terms = ["query", "list", "page", "data"]

    for term in high_signal_terms:
        if term in path_lower:
            score += 0.25
            break

    for term in medium_signal_terms:
        if term in path_lower:
            score += 0.1
            break

    relevant_params = {"pageNum", "pageSize", "keyword", "searchKey", "keyWord", "pageNo"}
    param_overlap = len(relevant_params & set(param_hits))
    score += param_overlap * 0.08

    if "/maincms-web/" in path:
        score += 0.1

    return min(score, 0.99)


def probe_endpoint(
    session: requests.Session,
    url: str,
    method: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    """对候选 URL 发起试探请求，检查是否返回有效 JSON。"""
    result: dict[str, Any] = {
        "url": url,
        "method": method,
        "probed": True,
        "status_code": 0,
        "is_json": False,
        "has_list_data": False,
        "sample_keys": [],
        "error": None,
    }

    probe_headers = {**BROWSER_HEADERS, **headers}
    probe_headers["Content-Type"] = "application/json;charset=UTF-8"
    probe_headers["Accept"] = "application/json, text/plain, */*"
    probe_headers["Referer"] = SEARCH_PAGE_URL

    for payload in PROBE_PAYLOADS:
        try:
            if method.upper() == "POST":
                resp = session.post(url, json=payload, headers=probe_headers, timeout=15)
            else:
                resp = session.get(url, params=payload, headers=probe_headers, timeout=15)

            result["status_code"] = resp.status_code
            logger.info("PROBE %s %s payload=%s -> %d", method, url, payload, resp.status_code)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    result["is_json"] = True
                    if isinstance(data, dict):
                        result["sample_keys"] = list(data.keys())[:15]
                        has_list = _find_list_in_response(data)
                        result["has_list_data"] = has_list
                    elif isinstance(data, list):
                        result["is_json"] = True
                        result["has_list_data"] = len(data) > 0
                    if result["is_json"]:
                        result["working_payload"] = payload
                        return result
                except (ValueError, KeyError):
                    result["is_json"] = False

            if resp.status_code in (403, 429):
                logger.info("收到 %d，跳过后续 payload 尝试", resp.status_code)
                break

        except requests.RequestException as exc:
            result["error"] = str(exc)
            logger.warning("PROBE 异常: %s -> %s", url, exc)

    return result


def _find_list_in_response(data: dict[str, Any], depth: int = 0) -> bool:
    """递归检查响应 JSON 中是否包含数组（可能是结果列表）。"""
    if depth > 3:
        return False
    for val in data.values():
        if isinstance(val, list) and len(val) > 0:
            return True
        if isinstance(val, dict):
            if _find_list_in_response(val, depth + 1):
                return True
    return False


def load_config(config_path: str | None) -> dict[str, Any]:
    """加载配置文件，不存在则返回空字典。"""
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        logger.warning("配置文件不存在: %s", config_path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("配置文件解析失败: %s -> %s", config_path, exc)
        return {}


def update_config_file(config_path: str, best_api: dict[str, Any]) -> bool:
    """将探测到的最佳端点写回配置文件。

    payload_template 始终写为字符串占位符格式以保证 build_payload 兼容。
    """
    path = Path(config_path)
    if not path.exists():
        logger.warning("配置文件不存在，无法更新: %s", config_path)
        return False
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        config["search_api"] = best_api.get("url", "")
        config["search_method"] = best_api.get("method", "POST")
        if "working_payload" in best_api:
            # 将 probe 发现的具体 payload 转为占位符模板
            raw_payload = best_api["working_payload"]
            template: dict[str, Any] = {}
            for k, v in raw_payload.items():
                template[k] = v
            config["payload_template"] = template
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("已更新配置文件: %s", config_path)
        return True
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("配置文件更新失败: %s", exc)
        return False


def run_probe(config: dict[str, Any], do_endpoint_probe: bool = True) -> dict[str, Any]:
    """执行完整的探测流程。"""
    report: dict[str, Any] = {
        "page_url": SEARCH_PAGE_URL,
        "page_accessible": False,
        "page_status_code": 0,
        "js_bundles_found": [],
        "js_bundles_analyzed": 0,
        "suspected_apis": [],
        "probed_results": [],
        "best_endpoint": None,
        "needs_runtime_confirmation": True,
        "probe_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    session = requests.Session()

    # 阶段 1：获取搜索页 HTML
    accessible, html, status_code = fetch_page_html(session, SEARCH_PAGE_URL)
    report["page_accessible"] = accessible
    report["page_status_code"] = status_code

    all_candidates: list[dict[str, Any]] = []

    if accessible and html:
        # 阶段 2：提取并分析 JS bundle
        bundles = extract_js_bundles(html, SEARCH_PAGE_URL)
        report["js_bundles_found"] = bundles

        for bundle_url in bundles:
            logger.info("分析 JS bundle: %s", bundle_url)
            candidates = analyze_bundle(session, bundle_url)
            all_candidates.extend(candidates)
            report["js_bundles_analyzed"] += 1
            time.sleep(0.5)
    else:
        logger.warning("搜索页不可访问 (status=%d)，跳过 HTML/JS 分析", status_code)

    # 阶段 3：合并配置文件中的候选端点
    config_suspects = config.get("suspected_apis", [])
    for suspect in config_suspects:
        already_found = any(c["url"] == suspect["url"] for c in all_candidates)
        if not already_found:
            all_candidates.append({
                "url": suspect["url"],
                "method": suspect.get("method", "POST"),
                "confidence": 0.35,
                "reason": f"来自配置文件 suspected_apis: {suspect.get('note', '')}",
                "source_bundle": "config",
            })

    # 去重并按置信度排序
    seen_urls: set[str] = set()
    unique_candidates: list[dict[str, Any]] = []
    for c in all_candidates:
        if c["url"] not in seen_urls:
            seen_urls.add(c["url"])
            unique_candidates.append(c)
    unique_candidates.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    report["suspected_apis"] = unique_candidates[:20]

    # 阶段 4：试探候选端点
    if do_endpoint_probe and unique_candidates:
        api_headers = config.get("headers", {})
        probed: list[dict[str, Any]] = []
        for candidate in unique_candidates[:8]:
            logger.info("试探端点: %s (%s)", candidate["url"], candidate["method"])
            probe_result = probe_endpoint(session, candidate["url"], candidate["method"], api_headers)
            probe_result["original_confidence"] = candidate.get("confidence", 0)
            probed.append(probe_result)
            time.sleep(1)

        report["probed_results"] = probed

        # 找出最佳端点
        for pr in probed:
            if pr.get("is_json") and pr.get("has_list_data"):
                report["best_endpoint"] = {
                    "url": pr["url"],
                    "method": pr["method"],
                    "status_code": pr["status_code"],
                    "sample_keys": pr.get("sample_keys", []),
                    "working_payload": pr.get("working_payload"),
                    "confirmed": True,
                }
                report["needs_runtime_confirmation"] = False
                logger.info("发现可用端点: %s", pr["url"])
                break

        if report["best_endpoint"] is None:
            for pr in probed:
                if pr.get("is_json"):
                    report["best_endpoint"] = {
                        "url": pr["url"],
                        "method": pr["method"],
                        "status_code": pr["status_code"],
                        "sample_keys": pr.get("sample_keys", []),
                        "confirmed": False,
                    }
                    report["needs_runtime_confirmation"] = True
                    logger.info("发现疑似端点（无列表数据）: %s", pr["url"])
                    break

    if report["best_endpoint"] is None:
        report["needs_runtime_confirmation"] = True
        logger.warning("未能确认任何可用端点，需要通过浏览器网络面板或运行态拦截确认")

    session.close()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="广东省政府采购网 API 端点探测工具")
    parser.add_argument("--output", "-o", help="输出 JSON 报告文件路径")
    parser.add_argument("--config", "-c", help="配置文件路径 (config/gdgpo_api.json)")
    parser.add_argument("--update-config", help="探测成功后将结果写回指定配置文件")
    parser.add_argument("--no-probe", action="store_true", help="跳过端点试探（仅做静态分析）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config(args.config)
    report = run_probe(config, do_endpoint_probe=not args.no_probe)

    if args.update_config and report.get("best_endpoint") and report["best_endpoint"].get("confirmed"):
        update_config_file(args.update_config, report["best_endpoint"])

    report_json = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_json, encoding="utf-8")
        logger.info("探测报告已写入: %s", args.output)
    else:
        print(report_json)

    total_suspects = len(report.get("suspected_apis", []))
    best = report.get("best_endpoint")
    confirmed = best.get("confirmed", False) if best else False

    print(f"\n===== 探测摘要 =====", file=sys.stderr)
    print(f"页面可访问: {report['page_accessible']} (HTTP {report['page_status_code']})", file=sys.stderr)
    print(f"JS bundle 数量: {len(report.get('js_bundles_found', []))}", file=sys.stderr)
    print(f"候选 API 数量: {total_suspects}", file=sys.stderr)
    print(f"最佳端点: {best['url'] if best else '未发现'}", file=sys.stderr)
    print(f"已确认: {confirmed}", file=sys.stderr)
    print(f"需要运行时确认: {report['needs_runtime_confirmation']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
