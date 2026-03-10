"""标签页管理器：创建、绑定、互斥锁、域名校验。

每个标签页通过 TabBinding 对象与一个子 agent 绑定，保证：
- 标签页与站点域名一一对应
- 同一标签页同一时刻只有一个 agent 在操作（asyncio.Lock）
- 操作前自动校验 URL 域名，不匹配则重新导航
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from config import PAGE_LOAD_TIMEOUT_MS

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)


@dataclass
class TabBinding:
    """一个标签页绑定的元信息。"""

    alias: str
    expected_domain: str
    entry_url: str
    page: Page | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock


class TabManager:
    """管理多个标签页的创建、绑定与互斥访问。"""

    def __init__(self, context: BrowserContext) -> None:
        self._context = context
        self._bindings: dict[str, TabBinding] = {}

    async def create_tab(
        self,
        alias: str,
        entry_url: str,
        expected_domain: str,
    ) -> TabBinding:
        """创建一个新标签页并绑定到 alias。"""
        if alias in self._bindings:
            raise ValueError(f"标签页 alias={alias} 已存在")

        page = await self._context.new_page()
        binding = TabBinding(
            alias=alias,
            expected_domain=expected_domain,
            entry_url=entry_url,
            page=page,
        )
        self._bindings[alias] = binding
        logger.info("创建标签页 alias=%s  entry=%s", alias, entry_url)

        # 导航到入口 URL
        try:
            await page.goto(entry_url, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="domcontentloaded")
            logger.info("标签页 %s 已加载 %s", alias, entry_url)
        except Exception:
            logger.warning("标签页 %s 首次加载 %s 失败，将在 agent 执行时重试", alias, entry_url)

        return binding

    def get_binding(self, alias: str) -> TabBinding:
        binding = self._bindings.get(alias)
        if binding is None:
            raise KeyError(f"未找到标签页 alias={alias}")
        return binding

    def get_page(self, alias: str) -> Page:
        binding = self.get_binding(alias)
        if binding.page is None or binding.page.is_closed():
            raise RuntimeError(f"标签页 {alias} 的 Page 已关闭")
        return binding.page

    async def validate_tab(self, alias: str) -> bool:
        """校验标签页当前 URL 是否匹配 expected_domain。"""
        binding = self.get_binding(alias)
        page = self.get_page(alias)
        current_domain = urlparse(page.url).hostname or ""
        if binding.expected_domain in current_domain:
            return True
        logger.warning(
            "标签页 %s 域名不匹配: 期望 %s, 当前 %s → 将重新导航",
            alias, binding.expected_domain, current_domain,
        )
        return False

    async def ensure_on_domain(self, alias: str) -> None:
        """确保标签页在正确域名上，否则导航回入口。"""
        if not await self.validate_tab(alias):
            page = self.get_page(alias)
            entry = self.get_binding(alias).entry_url
            await page.goto(entry, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="domcontentloaded")

    async def acquire_lock(self, alias: str) -> None:
        binding = self.get_binding(alias)
        await binding.lock.acquire()
        logger.debug("锁已获取: %s", alias)

    def release_lock(self, alias: str) -> None:
        binding = self.get_binding(alias)
        binding.lock.release()
        logger.debug("锁已释放: %s", alias)

    async def cleanup(self) -> None:
        """关闭所有标签页。"""
        for alias, binding in self._bindings.items():
            if binding.page and not binding.page.is_closed():
                try:
                    await binding.page.close()
                    logger.info("标签页 %s 已关闭", alias)
                except Exception as exc:
                    logger.warning("关闭标签页 %s 时出错: %s", alias, exc)
        self._bindings.clear()
