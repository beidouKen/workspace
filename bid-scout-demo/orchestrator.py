"""编排器：负责创建标签页、创建子 agent、等待完成、汇总结果、生成报告、清理资源。

子 agent 生命周期管理：
  1. 总控创建两个子 agent，分别绑定到各自的标签页
  2. 使用 asyncio.gather 并发启动（浏览器操作通过 TabManager 的锁串行化）
  3. 等待全部完成（return_exceptions=True 保证一个失败不阻塞另一个）
  4. 汇总结果 → 关键词筛选 → 生成 JSON + HTML 报告
  5. 显式清理每个子 agent → 关闭标签页
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from agents.base_agent import AgentState, BidItem
from agents.gdgpo_agent import GdgpoAgent
from agents.gz_tyj_agent import GzTyjAgent
from config import ALL_SITES, MAX_ITEMS_PER_SITE
from filters.keyword_filter import apply_filter
from reporters.html_reporter import write_html_report
from reporters.json_writer import write_json_report
from tab_manager import TabManager

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, context: BrowserContext) -> None:
        self.context = context
        self.tab_manager = TabManager(context)
        self.agents: list[GzTyjAgent | GdgpoAgent] = []
        self.all_items: list[dict] = []
        self.all_errors: list[str] = []

    async def run(self) -> None:
        try:
            await self._setup_tabs()
            await self._create_agents()
            await self._execute_agents()
            await self._generate_reports()
        finally:
            await self._cleanup()

    # ------------------------------------------------------------------
    # 第一步：创建固定标签页
    # ------------------------------------------------------------------

    async def _setup_tabs(self) -> None:
        logger.info("=== 第一步：创建固定标签页 ===")
        for site in ALL_SITES:
            await self.tab_manager.create_tab(
                alias=site.alias,
                entry_url=site.entry_url,
                expected_domain=site.expected_domain,
            )
        logger.info("共创建 %d 个标签页", len(ALL_SITES))

    # ------------------------------------------------------------------
    # 第二步：创建子 agent
    # ------------------------------------------------------------------

    async def _create_agents(self) -> None:
        logger.info("=== 第二步：创建子 agent ===")

        agent_a = GzTyjAgent(
            agent_id="subagent_a",
            tab_alias="tab_gz_tyj",
            tab_manager=self.tab_manager,
            max_items=MAX_ITEMS_PER_SITE,
        )
        agent_b = GdgpoAgent(
            agent_id="subagent_b",
            tab_alias="tab_gdgpo",
            tab_manager=self.tab_manager,
            max_items=MAX_ITEMS_PER_SITE,
        )
        self.agents = [agent_a, agent_b]
        logger.info("子 agent 已创建: %s", [a.agent_id for a in self.agents])

    # ------------------------------------------------------------------
    # 第三步：并发执行（浏览器操作通过锁串行化）
    # ------------------------------------------------------------------

    async def _execute_agents(self) -> None:
        logger.info("=== 第三步：执行采集任务 ===")

        results = await asyncio.gather(
            *[agent.run() for agent in self.agents],
            return_exceptions=True,
        )

        for agent, result in zip(self.agents, results):
            if isinstance(result, BaseException):
                self.all_errors.append(f"[{agent.agent_id}] 异常: {result}")
                logger.error("[%s] 执行异常: %s", agent.agent_id, result)
            elif isinstance(result, list):
                items_dicts = [item.to_dict() for item in result]
                self.all_items.extend(items_dicts)
                logger.info("[%s] 返回 %d 条数据", agent.agent_id, len(result))
            # 收集 agent 内部记录的错误
            self.all_errors.extend(agent.errors)

        logger.info("全部采集完成: 共 %d 条数据, %d 个错误", len(self.all_items), len(self.all_errors))

    # ------------------------------------------------------------------
    # 第四步：关键词筛选 + 生成报告
    # ------------------------------------------------------------------

    async def _generate_reports(self) -> None:
        logger.info("=== 第四步：生成报告 ===")

        filtered = apply_filter(self.all_items)
        sources = [s.alias for s in ALL_SITES]

        json_path = write_json_report(filtered, self.all_errors, sources)
        html_path = write_html_report(filtered, self.all_errors, sources)

        logger.info("报告生成完成:")
        logger.info("  JSON: %s", json_path)
        logger.info("  HTML: %s", html_path)

    # ------------------------------------------------------------------
    # 第五步：清理
    # ------------------------------------------------------------------

    async def _cleanup(self) -> None:
        logger.info("=== 第五步：清理资源 ===")

        # 清理每个子 agent
        for agent in self.agents:
            if agent.state not in (AgentState.CLEANED_UP,):
                try:
                    await agent.cleanup()
                except Exception as exc:
                    logger.warning("清理 agent %s 时出错: %s", agent.agent_id, exc)

        # 关闭标签页
        await self.tab_manager.cleanup()

        logger.info("所有资源已清理")
        self._print_summary()

    def _print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("  BidScout Demo 运行摘要")
        print("=" * 60)
        for agent in self.agents:
            status = "OK" if agent.state in (AgentState.COMPLETED, AgentState.CLEANED_UP) and not agent.errors else "FAIL"
            print(f"  [{status}] {agent.agent_id} ({agent.source_site}): {len(agent.results)} 条")
        print(f"  总计: {len(self.all_items)} 条数据, {len(self.all_errors)} 个错误")
        if self.all_errors:
            print("  错误:")
            for e in self.all_errors:
                print(f"    - {e}")
        print("=" * 60 + "\n")
