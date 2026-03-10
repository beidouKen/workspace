"""广东政府采购网采集子 agent。

职责：尝试多个候选入口 URL → 在可用的列表页上提取前 N 条 → 进详情页补充摘要。
比广州体育局更复杂，因为需要动态寻找可用的列表入口。
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from adapters.gdgpo_adapter import check_page_usable, parse_detail, parse_list
from agents.base_agent import BaseAgent, BidItem
from config import ACTION_DELAY_SEC, DETAIL_TEXT_MAX_LEN, MAX_RETRIES, SITE_GDGPO

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class GdgpoAgent(BaseAgent):
    """广东政府采购网采集 agent。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(
            source_site=SITE_GDGPO.alias,
            **kwargs,
        )
        self.site = SITE_GDGPO

    async def _do_execute(self, page: Page) -> list[BidItem]:
        items: list[BidItem] = []

        # 找到可用的列表入口
        usable_url = await self._find_usable_entry(page)
        if not usable_url:
            self.errors.append("广东政府采购网所有候选入口均不可用")
            return items

        await self.safe_screenshot(f"{self.site.alias}_list")

        # 解析列表
        raw_items = await self._parse_list_with_retry(page)
        if not raw_items:
            self.errors.append("广东政府采购网列表页未获取到任何条目")
            return items

        # 逐条处理
        for idx, raw in enumerate(raw_items[: self.max_items]):
            try:
                item = await self._process_item(page, raw, idx, usable_url)
                items.append(item)
            except Exception as exc:
                logger.warning("[%s] 处理第 %d 条时出错: %s", self.agent_id, idx, exc)
                items.append(BidItem(
                    source_site=self.site.alias,
                    title=raw.get("title", ""),
                    publish_date=raw.get("publish_date", ""),
                    url=raw.get("url", ""),
                    summary="（详情获取失败）",
                ))

        return items

    async def _find_usable_entry(self, page: Page) -> str | None:
        """依次尝试主入口和备用入口，返回第一个可用的 URL。"""
        candidate_urls = [self.site.entry_url] + list(self.site.fallback_urls)

        for url in candidate_urls:
            logger.info("[%s] 尝试入口: %s", self.agent_id, url)
            try:
                await self.safe_navigate(url)
                page = self.tab_manager.get_page(self.tab_alias)
                if await check_page_usable(page):
                    logger.info("[%s] 入口可用: %s", self.agent_id, url)
                    return url
                logger.warning("[%s] 入口不可用: %s", self.agent_id, url)
            except Exception as exc:
                logger.warning("[%s] 入口加载失败 %s: %s", self.agent_id, url, exc)
            await asyncio.sleep(ACTION_DELAY_SEC)

        return None

    async def _parse_list_with_retry(self, page: Page) -> list[dict]:
        for attempt in range(1, MAX_RETRIES + 1):
            page = self.tab_manager.get_page(self.tab_alias)
            raw = await parse_list(page, self.max_items)
            if raw:
                return raw
            logger.warning("[%s] 列表解析第 %d 次未获取到数据，重试...", self.agent_id, attempt)
            await page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(ACTION_DELAY_SEC)
        return []

    async def _process_item(
        self, page: Page, raw: dict, idx: int, list_url: str
    ) -> BidItem:
        title = raw.get("title", "")
        url = raw.get("url", "")
        publish_date = raw.get("publish_date", "")
        detail_text = ""

        if url:
            try:
                await self.safe_navigate(url)
                detail_page = self.tab_manager.get_page(self.tab_alias)
                detail_text = await parse_detail(detail_page)
                await self.safe_screenshot(f"{self.site.alias}_detail_{idx}")
            except Exception as exc:
                logger.warning("[%s] 详情页 %s 加载失败: %s", self.agent_id, url, exc)
            finally:
                try:
                    await self.safe_navigate(list_url)
                except Exception:
                    pass

        summary = detail_text[:200] if detail_text else title

        return BidItem(
            source_site=self.site.alias,
            title=title,
            publish_date=publish_date,
            url=url,
            summary=summary,
            detail_text=detail_text[:DETAIL_TEXT_MAX_LEN],
        )
