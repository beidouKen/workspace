#!/usr/bin/env python3
"""BidScout Demo — 体育服务运营类招投标信息采集总控入口。

使用方法:
    python main.py                     # 默认 headless=False，可以观察浏览器
    python main.py --headless          # 无头模式
    python main.py --max-items 3       # 每站最多抓 3 条

运行流程:
    1. 启动 Playwright Chromium 浏览器
    2. 创建两个固定标签页（广州体育局 / 广东政府采购网）
    3. 分别创建两个子 agent 执行采集
    4. 关键词筛选 + 打分
    5. 输出 JSON + HTML 报告到 output/
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，确保模块可导入
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from orchestrator import Orchestrator


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")
    # Playwright 自身日志较多，降级到 WARNING
    logging.getLogger("playwright").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BidScout Demo — 体育招投标采集")
    parser.add_argument("--headless", action="store_true", help="无头模式运行浏览器")
    parser.add_argument("--max-items", type=int, default=None, help="每站最大抓取条数")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    return parser.parse_args()


async def async_main(args: argparse.Namespace) -> None:
    from playwright.async_api import async_playwright

    if args.max_items is not None:
        config.MAX_ITEMS_PER_SITE = args.max_items

    # 确保输出目录存在
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("main")
    logger.info("BidScout Demo 启动")
    logger.info("  headless=%s  max_items=%d", args.headless, config.MAX_ITEMS_PER_SITE)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )

        try:
            orch = Orchestrator(context)
            await orch.run()
        finally:
            await context.close()
            await browser.close()
            logger.info("浏览器已关闭")

    logger.info("BidScout Demo 运行结束")
    logger.info("报告输出:")
    logger.info("  JSON: %s", config.REPORT_JSON_PATH)
    logger.info("  HTML: %s", config.REPORT_HTML_PATH)


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\n用户中断，退出。")
        sys.exit(1)


if __name__ == "__main__":
    main()
