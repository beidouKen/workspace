#!/usr/bin/env python3
"""广东省政府采购网 API-first 数据抓取工具。

优先通过 HTTP API 采集搜索结果和详情页，支持关键词搜索、翻页、详情提取、
体育相关性评分和结构化 JSON/CSV 输出。

用法:
    python3 gdgpo_api_fetch.py --keyword 体育 --pages 5 --output /tmp/gdgpo_raw.json
    python3 gdgpo_api_fetch.py --keyword 体育 --pages 3 --page-size 10 --config ../config/gdgpo_api.json --verbose

退出码: 0 成功, 1 致命错误（但仍会输出结构化 JSON）
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import tempfile
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

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

logger = logging.getLogger("gdgpo_fetch")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

BASE_URL = "https://gdgpo.czt.gd.gov.cn"
SEARCH_PAGE_URL = f"{BASE_URL}/maincms-web/fullSearchingGd"

SPORTS_KEYWORDS: list[str] = [
    "体育", "运动", "健身", "场馆", "赛事", "全民健身",
    "体育局", "体育中心", "足球", "篮球", "羽毛球",
    "游泳", "跑道", "体育公园", "田径", "排球",
    "乒乓球", "网球", "武术", "体操", "冰雪",
    "滑冰", "健身房", "运动场", "体育馆",
]

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": SEARCH_PAGE_URL,
    "Origin": BASE_URL,
}

# ---------------------------------------------------------------------------
# 配置加载
# ---------------------------------------------------------------------------


def load_config(config_path: str | None) -> dict[str, Any]:
    """加载 JSON 配置文件。缺失或解析失败返回空字典。"""
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        logger.warning("配置文件不存在: %s，使用默认配置", config_path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("配置文件解析失败: %s -> %s", config_path, exc)
        return {}


def load_probe_result(probe_path: str | None) -> dict[str, Any]:
    """加载 probe 输出的 JSON 报告。"""
    if not probe_path:
        return {}
    path = Path(probe_path)
    if not path.exists():
        logger.info("probe 结果文件不存在: %s", probe_path)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("probe 结果解析失败: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# 端点解析
# ---------------------------------------------------------------------------


def resolve_api_endpoint(
    config: dict[str, Any],
    probe_result: dict[str, Any],
) -> tuple[str, str, dict[str, Any] | None]:
    """确定要使用的 API URL 和方法。

    优先级：config.search_api > probe.best_endpoint > config.suspected_apis
    返回 (url, method, payload_template 或 None)
    """
    # 优先级 1：配置文件中已确认的端点
    api_url = config.get("search_api", "").strip()
    if api_url:
        method = config.get("search_method", "POST")
        template = config.get("payload_template")
        logger.info("使用配置文件端点: %s (%s)", api_url, method)
        return api_url, method, template

    # 优先级 2：probe 发现的最佳端点
    best = probe_result.get("best_endpoint")
    if best and best.get("url"):
        url = best["url"]
        method = best.get("method", "POST")
        template = best.get("working_payload")
        confirmed = best.get("confirmed", False)
        label = "已确认" if confirmed else "未完全确认"
        logger.info("使用 probe 发现的端点 (%s): %s (%s)", label, url, method)
        return url, method, template

    # 优先级 3：配置文件中的候选端点列表
    suspects = config.get("suspected_apis", [])
    if suspects:
        first = suspects[0]
        url = first.get("url", "")
        method = first.get("method", "POST")
        logger.info("使用候选端点（未确认）: %s (%s)", url, method)
        return url, method, None

    return "", "", None


def run_probe_subprocess(config_path: str | None, output_path: str) -> dict[str, Any]:
    """调用 gdgpo_probe_api.py 子进程执行探测。"""
    script_dir = Path(__file__).parent
    probe_script = script_dir / "gdgpo_probe_api.py"
    if not probe_script.exists():
        logger.warning("probe 脚本不存在: %s", probe_script)
        return {}

    cmd = [sys.executable, str(probe_script), "--output", output_path]
    if config_path:
        cmd.extend(["--config", config_path])

    logger.info("执行 probe 子进程: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return load_probe_result(output_path)
        else:
            logger.warning("probe 子进程失败 (exit=%d): %s", result.returncode, result.stderr[:500])
    except subprocess.TimeoutExpired:
        logger.warning("probe 子进程超时")
    except OSError as exc:
        logger.warning("probe 子进程启动失败: %s", exc)
    return {}


# ---------------------------------------------------------------------------
# 搜索请求
# ---------------------------------------------------------------------------


def build_payload(
    template: dict[str, Any] | None,
    keyword: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """根据模板构建请求 payload，将占位符替换为实际值。

    模板值可以是字符串占位符（如 "{keyword}"）或来自 probe 的具体值（int）。
    对于已知语义的 key，始终用当前调用参数覆盖。
    """
    PAGE_NUM_KEYS = {"pageNum", "pageNo", "currentPage", "page_num"}
    PAGE_SIZE_KEYS = {"pageSize", "page_size"}
    KEYWORD_KEYS = {"keyword", "keyWord", "searchKey", "searchWord", "queryKey"}

    if template:
        payload: dict[str, Any] = {}
        for key, val in template.items():
            if key in KEYWORD_KEYS:
                payload[key] = keyword
            elif key in PAGE_NUM_KEYS:
                payload[key] = page
            elif key in PAGE_SIZE_KEYS:
                payload[key] = page_size
            elif isinstance(val, str):
                val = val.replace("{keyword}", keyword)
                val = val.replace("{pageNum}", str(page))
                val = val.replace("{pageSize}", str(page_size))
                if val.isdigit():
                    payload[key] = int(val)
                else:
                    payload[key] = val
            else:
                payload[key] = val
        return payload
    return {"keyword": keyword, "pageNum": page, "pageSize": page_size}


def search_page(
    session: requests.Session,
    api_url: str,
    method: str,
    keyword: str,
    page: int,
    page_size: int,
    payload_template: dict[str, Any] | None,
    headers: dict[str, str],
    timeout: int,
    retry_max: int,
    retry_delay: float,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """执行单页搜索请求。返回 (成功, 响应JSON, 错误描述)。"""
    payload = build_payload(payload_template, keyword, page, page_size)
    request_headers = {**DEFAULT_HEADERS, **headers}

    for attempt in range(retry_max + 1):
        try:
            logger.info(
                "搜索请求: page=%d, payload=%s, attempt=%d/%d",
                page, json.dumps(payload, ensure_ascii=False), attempt + 1, retry_max + 1,
            )

            if method.upper() == "POST":
                resp = session.post(api_url, json=payload, headers=request_headers, timeout=timeout)
            else:
                resp = session.get(api_url, params=payload, headers=request_headers, timeout=timeout)

            logger.info("响应: HTTP %d, %d bytes", resp.status_code, len(resp.content))

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    return True, data, None
                except ValueError:
                    return False, None, f"HTTP 200 但响应不是有效 JSON (前200字符: {resp.text[:200]})"

            if resp.status_code in (403, 429):
                wait = retry_delay * (attempt + 1) * 2
                logger.warning("收到 HTTP %d，等待 %.1fs 后重试", resp.status_code, wait)
                time.sleep(wait)
                continue

            return False, None, f"HTTP {resp.status_code}: {resp.text[:200]}"

        except requests.Timeout:
            logger.warning("请求超时 (attempt %d)", attempt + 1)
            if attempt < retry_max:
                time.sleep(retry_delay)
                continue
            return False, None, f"请求超时 ({timeout}s)"

        except requests.RequestException as exc:
            logger.warning("请求异常: %s", exc)
            if attempt < retry_max:
                time.sleep(retry_delay)
                continue
            return False, None, f"请求异常: {exc}"

    return False, None, "重试次数耗尽"


def parse_search_response(
    data: Any,
    mapping: dict[str, str],
) -> tuple[list[dict[str, Any]], int]:
    """从搜索 API 响应中提取条目列表。

    返回 (条目列表, 总条数)。
    自动探测响应结构：支持常见的 data.records / data.list / rows 等嵌套格式。
    """
    total = 0
    items_list: list[Any] = []

    if isinstance(data, list):
        items_list = data
        total = len(data)
    elif isinstance(data, dict):
        # 尝试按 mapping 取值
        list_path = mapping.get("list_path", "").strip()
        total_path = mapping.get("total_path", "").strip()

        if list_path:
            items_list = _resolve_json_path(data, list_path)
        else:
            # 自动探测常见列表路径
            candidate_paths = [
                "data.records", "data.list", "data.rows", "data.items",
                "data.dataList", "data.resultList", "result.records",
                "result.list", "result.data", "records", "list",
                "rows", "data", "items", "results",
            ]
            for cp in candidate_paths:
                found = _resolve_json_path(data, cp)
                if isinstance(found, list) and len(found) > 0:
                    items_list = found
                    logger.info("自动探测到列表路径: %s (%d 条)", cp, len(found))
                    break

        if total_path:
            total_val = _resolve_json_path(data, total_path)
            if isinstance(total_val, (int, float)):
                total = int(total_val)
        else:
            # 自动探测总条数
            for tp in ["data.total", "data.totalCount", "total", "totalCount", "data.totalElements"]:
                total_val = _resolve_json_path(data, tp)
                if isinstance(total_val, (int, float)) and total_val > 0:
                    total = int(total_val)
                    break

    if not isinstance(items_list, list):
        items_list = []

    if total == 0:
        total = len(items_list)

    # 将原始记录映射为标准字段
    mapped_items: list[dict[str, Any]] = []
    for raw_item in items_list:
        if not isinstance(raw_item, dict):
            continue
        item = _map_item(raw_item, mapping)
        mapped_items.append(item)

    return mapped_items, total


def _resolve_json_path(data: Any, path: str) -> Any:
    """按点分路径取值，如 'data.records'。"""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _map_item(raw: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """将原始记录映射为标准字段结构。"""
    item: dict[str, Any] = {"source_site": "广东省政府采购网", "raw": raw}

    field_candidates: dict[str, list[str]] = {
        "title": [mapping.get("title", ""), "title", "name", "noticeName",
                  "projectName", "articleTitle", "noticeTitle", "cgName"],
        "publish_date": [mapping.get("publish_date", ""), "publishDate", "createTime",
                        "publishTime", "pubDate", "createDate", "releaseDate",
                        "issueTime", "noticeTime"],
        "url": [mapping.get("url", ""), "url", "link", "detailUrl", "href",
                "noticeUrl", "articleUrl"],
        "summary": [mapping.get("summary", ""), "summary", "content", "description",
                    "digest", "abstractContent", "brief"],
        "purchaser": [mapping.get("purchaser", ""), "purchaser", "buyerName",
                      "purchaserName", "cgr", "cgrmc", "tenderee",
                      "procuringEntity", "owner"],
        "budget": [mapping.get("budget", ""), "budget", "budgetAmount",
                   "totalBudget", "projectAmount", "amount",
                   "ysje", "cgys", "estimatedAmount"],
    }

    for standard_field, candidates in field_candidates.items():
        for candidate in candidates:
            if not candidate:
                continue
            val = raw.get(candidate)
            if val and str(val).strip():
                item[standard_field] = str(val).strip()
                break
        if standard_field not in item:
            item[standard_field] = ""

    # 补全 URL 为绝对路径
    if item.get("url") and not item["url"].startswith("http"):
        item["url"] = urljoin(BASE_URL, item["url"])

    return item


# ---------------------------------------------------------------------------
# 详情页抓取
# ---------------------------------------------------------------------------


def fetch_detail(
    session: requests.Session,
    url: str,
    selectors: dict[str, list[str]],
    headers: dict[str, str],
    timeout: int,
) -> dict[str, str]:
    """请求详情页 HTML，用 BeautifulSoup 提取字段。"""
    result: dict[str, str] = {}

    if not HAS_BS4:
        logger.warning("bs4 未安装，跳过详情页解析: %s", url)
        return result

    try:
        page_headers = {
            "User-Agent": headers.get("User-Agent", DEFAULT_HEADERS["User-Agent"]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": SEARCH_PAGE_URL,
        }
        resp = session.get(url, headers=page_headers, timeout=timeout)
        if resp.status_code != 200:
            logger.warning("详情页请求失败: %s -> HTTP %d", url, resp.status_code)
            return result

        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 提取各字段
        for field, css_selectors in selectors.items():
            for sel in css_selectors:
                if not sel:
                    continue
                try:
                    # 处理 meta 标签
                    if sel.startswith("meta["):
                        elem = soup.select_one(sel)
                        if elem and elem.get("content"):
                            result[field] = elem["content"].strip()
                            break
                    elif ":contains(" in sel:
                        # 解析 "td:contains('采购人')+td" 格式
                        m = re.match(r"(\w+):contains\(['\"]?(.+?)['\"]?\)", sel)
                        if m:
                            tag_name = m.group(1)
                            search_text = m.group(2)
                            for elem in soup.find_all(tag_name):
                                if search_text in (elem.get_text() or ""):
                                    # +tag 语义：取同级下一个同类型元素
                                    sibling = elem.find_next_sibling(tag_name)
                                    if sibling:
                                        result[field] = sibling.get_text(strip=True)
                                        break
                            if field in result:
                                break
                    else:
                        elem = soup.select_one(sel)
                        if elem:
                            text = elem.get_text(strip=True)
                            if text:
                                result[field] = text[:2000]
                                break
                except Exception as exc:
                    logger.debug("选择器 %s 失败: %s", sel, exc)
                    continue

        # content 字段特殊处理：截取前 2000 字符
        if "content" in result:
            result["detail_text"] = result.pop("content")[:2000]

        # 尝试从 <title> 补全标题
        if "title" not in result:
            title_tag = soup.find("title")
            if title_tag:
                result["title"] = title_tag.get_text(strip=True)

    except requests.Timeout:
        logger.warning("详情页超时: %s", url)
    except requests.RequestException as exc:
        logger.warning("详情页请求异常: %s -> %s", url, exc)
    except Exception as exc:
        logger.warning("详情页解析异常: %s -> %s", url, exc)

    return result


# ---------------------------------------------------------------------------
# 体育相关性评分
# ---------------------------------------------------------------------------


def score_sports_relevance(item: dict[str, Any]) -> float:
    """对单条记录进行体育相关性评分。返回 0.0 ~ 1.0。"""
    text = " ".join([
        item.get("title", ""),
        item.get("summary", ""),
        item.get("detail_text", ""),
        item.get("purchaser", ""),
    ])

    if not text.strip():
        return 0.0

    hits: list[str] = []
    for kw in SPORTS_KEYWORDS:
        if kw in text:
            hits.append(kw)

    if not hits:
        return 0.0

    # 基础分：命中越多分越高
    base = min(0.5 + len(hits) * 0.08, 0.95)

    # 标题命中加权
    title = item.get("title", "")
    title_hits = sum(1 for kw in SPORTS_KEYWORDS if kw in title)
    if title_hits > 0:
        base = min(base + title_hits * 0.1, 0.99)

    return round(base, 2)


# ---------------------------------------------------------------------------
# 输出构建
# ---------------------------------------------------------------------------


def build_output(
    items: list[dict[str, Any]],
    keyword: str,
    pages_requested: int,
    pages_succeeded: int,
    errors: list[str],
) -> dict[str, Any]:
    """构建最终输出 JSON。"""
    status = "completed"
    if pages_succeeded == 0 and not items:
        status = "failed"
    elif pages_succeeded < pages_requested:
        status = "partial"

    return {
        "status": status,
        "site": "广东省政府采购网",
        "keyword": keyword,
        "pages_requested": pages_requested,
        "pages_succeeded": pages_succeeded,
        "total_items": len(items),
        "items": items,
        "errors": errors,
        "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def write_output(output: dict[str, Any], output_path: str | None) -> None:
    """写出结果 JSON 和可选的 items-only 文件。"""
    output_json = json.dumps(output, ensure_ascii=False, indent=2)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output_json, encoding="utf-8")
        logger.info("结果已写入: %s", output_path)

        # 额外输出纯 items 数组文件，兼容 keyword_filter.py
        items_path = out.with_name(out.stem + "_items" + out.suffix)
        items_json = json.dumps(output["items"], ensure_ascii=False, indent=2)
        items_path.write_text(items_json, encoding="utf-8")
        logger.info("items 文件已写入: %s", items_path)
    else:
        print(output_json)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="广东省政府采购网 API-first 数据抓取工具")
    parser.add_argument("--keyword", "-k", default="体育", help="搜索关键词 (默认: 体育)")
    parser.add_argument("--pages", "-p", type=int, default=5, help="抓取页数 (默认: 5)")
    parser.add_argument("--page-size", type=int, default=10, help="每页条数 (默认: 10)")
    parser.add_argument("--output", "-o", help="输出 JSON 文件路径")
    parser.add_argument("--config", "-c", help="配置文件路径 (config/gdgpo_api.json)")
    parser.add_argument("--probe-result", help="probe 结果文件路径")
    parser.add_argument("--no-detail", action="store_true", help="跳过详情页抓取")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志输出")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("===== 广东省政府采购网 API 抓取开始 =====")
    logger.info("关键词: %s, 页数: %d, 每页: %d", args.keyword, args.pages, args.page_size)

    errors: list[str] = []

    # 加载配置
    config = load_config(args.config)
    headers = config.get("headers", {})
    timeout = config.get("request_timeout_seconds", 30)
    retry_max = config.get("retry_max", 2)
    retry_delay = config.get("retry_delay_seconds", 3)
    page_delay = config.get("page_delay_seconds", 1.5)
    detail_delay = config.get("detail_delay_seconds", 1.0)
    detail_selectors = config.get("detail_selectors", {})
    result_mapping = config.get("result_mapping", {})

    # 加载 probe 结果
    probe_result = load_probe_result(args.probe_result)

    # 解析 API 端点
    api_url, method, payload_template = resolve_api_endpoint(config, probe_result)

    if not api_url:
        # 尝试自动执行 probe
        logger.info("无可用端点，尝试自动执行 probe...")
        probe_output = str(Path(tempfile.gettempdir()) / "gdgpo_auto_probe.json")
        probe_result = run_probe_subprocess(args.config, probe_output)
        api_url, method, payload_template = resolve_api_endpoint(config, probe_result)

    if not api_url:
        msg = "无法确定 API 端点。请先运行 probe 脚本确认接口，或在 config/gdgpo_api.json 中手动填写 search_api"
        logger.error(msg)
        errors.append(msg)
        output = build_output([], args.keyword, args.pages, 0, errors)
        write_output(output, args.output)
        return 1

    logger.info("使用 API 端点: %s (%s)", api_url, method)

    session = requests.Session()
    all_items: list[dict[str, Any]] = []
    pages_succeeded = 0

    # 逐页搜索
    for page_num in range(1, args.pages + 1):
        logger.info("--- 第 %d/%d 页 ---", page_num, args.pages)

        ok, resp_data, err_msg = search_page(
            session=session,
            api_url=api_url,
            method=method,
            keyword=args.keyword,
            page=page_num,
            page_size=args.page_size,
            payload_template=payload_template,
            headers=headers,
            timeout=timeout,
            retry_max=retry_max,
            retry_delay=retry_delay,
        )

        if not ok or resp_data is None:
            error_text = f"第 {page_num} 页搜索失败: {err_msg}"
            logger.warning(error_text)
            errors.append(error_text)
            time.sleep(page_delay)
            continue

        items, total = parse_search_response(resp_data, result_mapping)
        logger.info("第 %d 页解析出 %d 条 (总计约 %d 条)", page_num, len(items), total)

        if not items:
            if page_num == 1:
                logger.warning("第一页即无结果，可能接口不匹配或搜索词无结果")
                errors.append(f"第 {page_num} 页解析出 0 条结果")
            break

        pages_succeeded += 1

        # 详情页抓取
        if not args.no_detail and detail_selectors:
            detail_success = 0
            for idx, item in enumerate(items):
                detail_url = item.get("url", "")
                if not detail_url:
                    continue
                logger.info("  详情 [%d/%d]: %s", idx + 1, len(items), detail_url)
                detail = fetch_detail(session, detail_url, detail_selectors, headers, timeout)
                if detail:
                    # 合并详情字段，不覆盖已有非空值
                    for key, val in detail.items():
                        if val and not item.get(key):
                            item[key] = val
                    detail_success += 1
                time.sleep(detail_delay)
            logger.info("  详情页成功: %d/%d", detail_success, len(items))

        # 体育相关性评分（同步写入 match_score/match_level 以兼容 generate_csv.py）
        for item in items:
            s = score_sports_relevance(item)
            item["score"] = s
            item["match_score"] = s
            if s >= 0.8:
                item["match_level"] = "high"
            elif s >= 0.5:
                item["match_level"] = "medium"
            elif s >= 0.2:
                item["match_level"] = "low-medium"
            else:
                item["match_level"] = "low"

        all_items.extend(items)
        time.sleep(page_delay)

    # 按评分降序排列
    all_items.sort(key=lambda x: x.get("score", 0), reverse=True)

    output = build_output(all_items, args.keyword, args.pages, pages_succeeded, errors)
    write_output(output, args.output)

    # 打印摘要
    print(f"\n===== 抓取摘要 =====", file=sys.stderr)
    print(f"关键词: {args.keyword}", file=sys.stderr)
    print(f"请求页数: {args.pages}, 成功页数: {pages_succeeded}", file=sys.stderr)
    print(f"总条目数: {len(all_items)}", file=sys.stderr)
    high_score = sum(1 for i in all_items if i.get("score", 0) >= 0.7)
    print(f"高相关性条目 (score>=0.7): {high_score}", file=sys.stderr)
    print(f"错误数: {len(errors)}", file=sys.stderr)
    print(f"状态: {output['status']}", file=sys.stderr)

    session.close()
    return 0 if output["status"] != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
