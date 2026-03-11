"""OpenClaw 官方 browser 能力桥接层。

对接方式：POST /tools/invoke  — 这是 OpenClaw Gateway 官方暴露的
工具调用接口，与 agent 内部调用 `browser navigate url:"..."` 等价。

本模块仅用于 --openclaw 模式下的连通性校验和标签页感知，
实际的页面操作仍由 Playwright 完成（demo 阶段的务实选择）。
"""

from __future__ import annotations

import logging

import aiohttp

import config

logger = logging.getLogger(__name__)


class OpenClawBridge:
    """通过 Gateway Tools Invoke API 调用 OpenClaw browser 工具。"""

    def __init__(self) -> None:
        cfg = config.load_openclaw_config()
        self._host: str = str(cfg["host"])
        self._port: int = int(cfg["port"])
        self._token: str = str(cfg["token"])
        self._profile: str = str(cfg["profile"])
        self._base = f"http://{self._host}:{self._port}"
        self._session: aiohttp.ClientSession | None = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # 核心：Tools Invoke
    # ------------------------------------------------------------------

    async def invoke(self, action: str, **args: str) -> dict:
        """调用 browser 工具。等价于 agent 内的 `browser <action> key:value ...`。"""
        session = await self._ensure_session()
        payload = {
            "tool": "browser",
            "action": action,
            "args": {**args, "profile": self._profile},
        }
        url = f"{self._base}/tools/invoke"
        async with session.post(url, json=payload) as resp:
            if resp.status >= 400:
                body = await resp.text()
                logger.error("tools/invoke %s 失败 (%d): %s", action, resp.status, body[:200])
                return {"error": body, "status": resp.status}
            return await resp.json(content_type=None)

    # ------------------------------------------------------------------
    # 便捷方法（映射 OpenClaw 官方 browser 命令）
    # ------------------------------------------------------------------

    async def verify_connection(self) -> bool:
        """检查 Gateway 是否可达。"""
        try:
            session = await self._ensure_session()
            async with session.get(f"{self._base}/health") as resp:
                ok = resp.status < 400
                logger.info("OpenClaw Gateway 连通性: %s (status=%d)", "OK" if ok else "FAIL", resp.status)
                return ok
        except Exception as exc:
            logger.warning("OpenClaw Gateway 不可达: %s", exc)
            return False

    async def browser_status(self) -> dict:
        return await self.invoke("status")

    async def browser_navigate(self, url: str) -> dict:
        return await self.invoke("navigate", url=url)

    async def browser_screenshot(self) -> dict:
        return await self.invoke("screenshot")

    async def browser_snapshot(self) -> dict:
        return await self.invoke("snapshot")

    async def browser_tabs(self) -> dict:
        return await self.invoke("tabs")

    async def browser_click(self, ref: str) -> dict:
        return await self.invoke("click", ref=ref)

    async def browser_scroll(self, direction: str = "down", amount: str = "800") -> dict:
        return await self.invoke("scroll", direction=direction, amount=amount)
