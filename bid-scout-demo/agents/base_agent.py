"""子 agent 基类：定义生命周期接口和安全浏览器操作方法。"""

from __future__ import annotations

import asyncio
import enum
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from config import ACTION_DELAY_SEC, SCREENSHOT_DIR

if TYPE_CHECKING:
    from playwright.async_api import Page

    from tab_manager import TabManager

logger = logging.getLogger(__name__)


class AgentState(enum.Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CLEANED_UP = "cleaned_up"


@dataclass
class BidItem:
    """采集到的单条招投标信息。"""

    source_site: str
    title: str
    publish_date: str
    url: str
    summary: str = ""
    detail_text: str = ""
    match_score: float = 0.0
    match_reason: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_site": self.source_site,
            "title": self.title,
            "publish_date": self.publish_date,
            "url": self.url,
            "summary": self.summary,
            "detail_text": self.detail_text,
            "match_score": self.match_score,
            "match_reason": self.match_reason,
        }


class BaseAgent:
    """子 agent 基类。

    子类需实现:
        - _do_execute(page) -> list[BidItem]
    """

    def __init__(
        self,
        agent_id: str,
        tab_alias: str,
        tab_manager: TabManager,
        source_site: str,
        max_items: int = 5,
    ) -> None:
        self.agent_id = agent_id
        self.tab_alias = tab_alias
        self.tab_manager = tab_manager
        self.source_site = source_site
        self.max_items = max_items
        self.state = AgentState.CREATED
        self.results: list[BidItem] = []
        self.errors: list[str] = []

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        self.state = AgentState.INITIALIZING
        logger.info("[%s] 初始化中 (tab=%s)", self.agent_id, self.tab_alias)
        await self.tab_manager.ensure_on_domain(self.tab_alias)
        logger.info("[%s] 标签页域名校验通过", self.agent_id)

    async def execute(self) -> list[BidItem]:
        self.state = AgentState.RUNNING
        logger.info("[%s] 开始执行采集", self.agent_id)
        try:
            page = self.tab_manager.get_page(self.tab_alias)
            self.results = await self._do_execute(page)
            self.state = AgentState.COMPLETED
            logger.info("[%s] 采集完成, 共 %d 条", self.agent_id, len(self.results))
        except Exception as exc:
            self.state = AgentState.FAILED
            self.errors.append(str(exc))
            logger.error("[%s] 采集失败: %s", self.agent_id, exc, exc_info=True)
        return self.results

    async def cleanup(self) -> None:
        self.state = AgentState.CLEANED_UP
        logger.info("[%s] 资源已回收 (state=%s)", self.agent_id, self.state.value)

    async def run(self) -> list[BidItem]:
        """完整生命周期：初始化 → 执行 → 清理。"""
        try:
            await self.initialize()
            return await self.execute()
        finally:
            await self.cleanup()

    # ------------------------------------------------------------------
    # 子类实现
    # ------------------------------------------------------------------

    async def _do_execute(self, page: Page) -> list[BidItem]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 安全浏览器操作（带锁 + 域名校验 + 延迟）
    # ------------------------------------------------------------------

    async def safe_navigate(self, url: str, *, timeout_ms: int = 30_000) -> None:
        """在持有标签页锁的前提下安全导航。"""
        await self.tab_manager.acquire_lock(self.tab_alias)
        try:
            await self.tab_manager.ensure_on_domain(self.tab_alias)
            page = self.tab_manager.get_page(self.tab_alias)
            await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            await asyncio.sleep(ACTION_DELAY_SEC)
        finally:
            self.tab_manager.release_lock(self.tab_alias)

    async def safe_screenshot(self, name: str) -> str:
        """截图并保存到 output/screenshots/，返回文件路径。"""
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOT_DIR / f"{name}.png"
        await self.tab_manager.acquire_lock(self.tab_alias)
        try:
            page = self.tab_manager.get_page(self.tab_alias)
            await page.screenshot(path=str(path), full_page=False)
        finally:
            self.tab_manager.release_lock(self.tab_alias)
        logger.info("[%s] 截图已保存: %s", self.agent_id, path)
        return str(path)

    async def safe_eval(self, expression: str) -> object:
        """在持有锁的前提下执行 JS 表达式。"""
        await self.tab_manager.acquire_lock(self.tab_alias)
        try:
            page = self.tab_manager.get_page(self.tab_alias)
            return await page.evaluate(expression)
        finally:
            self.tab_manager.release_lock(self.tab_alias)

    async def safe_query_all(self, selector: str, extractor_js: str) -> list[dict]:
        """查询所有匹配 selector 的元素，对每个元素执行 extractor_js 并返回结果列表。

        extractor_js 应为一个函数体字符串，接收 el 参数，例如：
            "el => ({ title: el.textContent, href: el.href })"
        """
        await self.tab_manager.acquire_lock(self.tab_alias)
        try:
            page = self.tab_manager.get_page(self.tab_alias)
            elements = await page.query_selector_all(selector)
            results = []
            for el in elements:
                data = await el.evaluate(extractor_js)
                results.append(data)
            return results
        finally:
            self.tab_manager.release_lock(self.tab_alias)
