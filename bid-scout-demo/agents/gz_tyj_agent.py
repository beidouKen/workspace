"""广州市体育局采集子 agent。

职责：在绑定的标签页中打开列表页 → 提取前 N 条 → 进入详情页获取摘要。
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from adapters.gz_tyj_adapter import parse_detail, parse_list
from agents.base_agent import BaseAgent, BidItem
from config import ACTION_DELAY_SEC, DETAIL_TEXT_MAX_LEN, MAX_RETRIES, SITE_GZ_TYJ

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class GzTyjAgent(BaseAgent):
    """广州市体育局采集 agent。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(
            source_site=SITE_GZ_TYJ.alias,
            **kwargs,
        )
        self.site = SITE_GZ_TYJ

    async def _do_execute(self, page: Page) -> list[BidItem]:
        items: list[BidItem] = []

        # 截图列表页
        await self.safe_screenshot(f"{self.site.alias}_list")

        # 解析列表
        raw_items = await self._parse_list_with_retry(page)
        if not raw_items:
            self.errors.append("广州体育局列表页未获取到任何条目")
            return items

        # 逐条进入详情页
        for idx, raw in enumerate(raw_items[: self.max_items]):
            try:
                item = await self._process_item(page, raw, idx)
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

    async def _parse_list_with_retry(self, page: Page) -> list[dict]:
        for attempt in range(1, MAX_RETRIES + 1):
            raw = await parse_list(page, self.max_items)
            if raw:
                return raw
            logger.warning("[%s] 列表解析第 %d 次未获取到数据，重试...", self.agent_id, attempt)
            await page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(ACTION_DELAY_SEC)
        return []

    async def _process_item(self, page: Page, raw: dict, idx: int) -> BidItem:
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
                # 返回列表页
                try:
                    await self.safe_navigate(self.site.entry_url)
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
