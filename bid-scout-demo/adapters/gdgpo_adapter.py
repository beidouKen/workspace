"""广东政府采购网页面适配器。

目标页面: https://gdgpo.czt.gd.gov.cn/ 及其子栏目
页面结构: FreeCMS 平台生成的采购公告列表，结构可能随栏目不同而变化。
采用多策略提取以提高兼容性。
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def check_page_usable(page: Page) -> bool:
    """检查页面是否正常加载（非 403 / 空白 / 错误页）。"""
    result = await page.evaluate("""() => {
        const body = document.body;
        if (!body) return false;
        const text = body.innerText || '';
        if (text.includes('403') && text.includes('Forbidden')) return false;
        if (text.includes('访问被拒绝')) return false;
        if (text.trim().length < 50) return false;
        return true;
    }""")
    return bool(result)


async def parse_list(page: Page, max_items: int = 5) -> list[dict]:
    """解析采购公告列表页，返回 [{title, url, publish_date}, ...]。"""

    js_result = await page.evaluate("""(maxItems) => {
        const results = [];

        // 策略1: FreeCMS 标准列表 — 表格行
        const rows = document.querySelectorAll('table tr, .list-content tr, .data-list tr');
        for (const row of rows) {
            const a = row.querySelector('a');
            const tds = row.querySelectorAll('td');
            if (a && a.textContent.trim().length > 4) {
                let date = '';
                for (const td of tds) {
                    const t = td.textContent.trim();
                    if (/\\d{4}[-/]\\d{2}[-/]\\d{2}/.test(t)) {
                        date = t.match(/\\d{4}[-/]\\d{2}[-/]\\d{2}/)[0];
                        break;
                    }
                }
                results.push({
                    title: a.textContent.trim(),
                    url: a.href,
                    publish_date: date
                });
            }
            if (results.length >= maxItems) break;
        }
        if (results.length > 0) return results;

        // 策略2: ul/li 结构
        const lis = document.querySelectorAll('.list li, .notice-list li, ul.newsList li, .cggg li, .list-item');
        for (const li of lis) {
            const a = li.querySelector('a');
            if (a && a.textContent.trim().length > 4) {
                let date = '';
                const spans = li.querySelectorAll('span, em, .date, .time');
                for (const s of spans) {
                    const t = s.textContent.trim();
                    if (/\\d{4}[-/]\\d{2}[-/]\\d{2}/.test(t)) {
                        date = t.match(/\\d{4}[-/]\\d{2}[-/]\\d{2}/)[0];
                        break;
                    }
                }
                results.push({
                    title: a.textContent.trim(),
                    url: a.href,
                    publish_date: date
                });
            }
            if (results.length >= maxItems) break;
        }
        if (results.length > 0) return results;

        // 策略3: 通用 — 取页面中所有带 href 的 a 标签，过滤出像公告的
        const allLinks = document.querySelectorAll('a[href]');
        for (const a of allLinks) {
            const text = a.textContent.trim();
            const href = a.href;
            // 过滤导航链接、过短文本
            if (text.length < 8) continue;
            if (href.includes('javascript:')) continue;
            if (href === window.location.href) continue;
            // 看起来像公告标题的：包含"采购"、"招标"、"公告"、"项目"等词
            const isNotice = /采购|招标|公告|项目|中标|成交|磋商|竞价|询价|比选/.test(text);
            if (isNotice || href.includes('/info/') || href.includes('/content/') || href.includes('.html')) {
                results.push({
                    title: text,
                    url: href,
                    publish_date: ''
                });
            }
            if (results.length >= maxItems) break;
        }
        return results;
    }""", max_items)

    items: list[dict] = []
    if js_result:
        for item in js_result[:max_items]:
            title = item.get("title", "").strip()
            if title:
                items.append(item)
        logger.info("广东政府采购网列表页解析到 %d 条 (截取前 %d)", len(js_result), len(items))
    else:
        logger.warning("广东政府采购网列表页未解析到任何条目")

    return items


async def parse_detail(page: Page) -> str:
    """解析详情页，返回正文文本（前 500 字）。"""
    detail_text = await page.evaluate("""() => {
        const selectors = [
            '.article-content', '.detail-content', '.news-detail',
            '.content-detail', '.noticeDetail', '.detail-box',
            '.article', '.content', '.main-text',
            '#content', '#detail', '.TRS_Editor',
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.textContent.trim().length > 20) {
                return el.textContent.trim();
            }
        }
        // 兜底
        const paras = document.querySelectorAll('p');
        const texts = [];
        for (const p of paras) {
            const t = p.textContent.trim();
            if (t.length > 10) texts.push(t);
        }
        return texts.join(' ');
    }""")

    text = (detail_text or "").strip()
    text = re.sub(r'\s+', ' ', text)
    return text[:500]
