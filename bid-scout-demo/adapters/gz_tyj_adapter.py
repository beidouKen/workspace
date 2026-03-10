"""广州市体育局采购招标页面适配器。

目标页面: https://tyj.gz.gov.cn/tzgg/cgzb/
页面结构: 标准政府 CMS 列表 — 每条公告包含标题超链接和日期。
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)

# 列表页主选择器：通用政府 CMS 列表条目
_LIST_SELECTORS = [
    "ul.list_20 li a",          # 常见 CMS 列表
    ".newsList li a",
    ".list-box li a",
    "ul.news_list li a",
    ".bt_content li a",         # 广州政府站常见
    "#container li a",
    ".main-content li a",
    "ul li a[href*='content/post']",  # 按链接特征兜底
]

# 日期选择器
_DATE_SELECTORS = [
    "ul.list_20 li span",
    ".newsList li span",
    ".list-box li span",
    "ul.news_list li span",
    ".bt_content li span",
    "#container li span",
    ".main-content li span",
    "ul li span",
]


async def parse_list(page: Page, max_items: int = 5) -> list[dict]:
    """解析列表页，返回 [{title, url, publish_date}, ...]。"""
    items: list[dict] = []

    # 尝试用 JS 一次性提取（更可靠，不依赖固定选择器）
    js_result = await page.evaluate("""() => {
        const results = [];
        // 策略1: 查找所有指向 content/post 的链接
        const links = document.querySelectorAll('a[href*="content/post"]');
        for (const a of links) {
            const li = a.closest('li');
            let date = '';
            if (li) {
                const span = li.querySelector('span');
                if (span) date = span.textContent.trim();
            }
            results.push({
                title: a.textContent.trim(),
                url: a.href,
                publish_date: date.replace(/[\\[\\]]/g, '').trim()
            });
        }
        if (results.length > 0) return results;

        // 策略2: 取页面中所有 li > a 并按列表区域特征过滤
        const allLi = document.querySelectorAll('li');
        for (const li of allLi) {
            const a = li.querySelector('a');
            const span = li.querySelector('span');
            if (a && a.href && a.textContent.trim().length > 4) {
                results.push({
                    title: a.textContent.trim(),
                    url: a.href,
                    publish_date: span ? span.textContent.trim().replace(/[\\[\\]]/g, '') : ''
                });
            }
        }
        return results;
    }""")

    if js_result:
        for item in js_result[:max_items]:
            title = item.get("title", "").strip()
            if title:
                items.append(item)
        logger.info("广州体育局列表页解析到 %d 条 (截取前 %d)", len(js_result), len(items))
    else:
        logger.warning("广州体育局列表页未解析到任何条目")

    return items


async def parse_detail(page: Page) -> str:
    """解析详情页，返回正文文本（前 500 字）。"""
    detail_text = await page.evaluate("""() => {
        // 常见正文区域选择器
        const selectors = [
            '.article-content', '.art_content', '.detail-content',
            '.news_content', '.TRS_Editor', '.content',
            '#zoom', '.bt_content', 'article',
            '.main-content .text', '#myContent',
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim().length > 20) {
                return el.textContent.trim();
            }
        }
        // 兜底：取 body 中最长的文本块
        const paras = document.querySelectorAll('p');
        let longest = '';
        for (const p of paras) {
            const t = p.textContent.trim();
            if (t.length > longest.length) longest = t;
        }
        return longest;
    }""")

    text = (detail_text or "").strip()
    # 清理多余空白
    text = re.sub(r'\s+', ' ', text)
    return text[:500]
