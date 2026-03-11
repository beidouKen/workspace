"""验证码 / 登录 / 访问拒绝 检测与人工接管暂停机制。

检测逻辑通过 JS evaluate 在页面中搜索特征文本和元素。
一旦检测到异常，通过 asyncio.to_thread(input, ...) 暂停 agent，
等待用户在真实浏览器中手动处理后按回车恢复。
"""

from __future__ import annotations

import asyncio
import enum
import logging
from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


class BlockType(enum.Enum):
    CAPTCHA = "captcha"
    LOGIN = "login"
    FORBIDDEN = "forbidden"


_DETECT_JS = """() => {
    const text = (document.body && document.body.innerText) || '';
    const html = document.documentElement.innerHTML || '';

    const captchaPatterns = [
        '验证码', '滑动验证', '请完成验证', 'captcha',
        '人机验证', '请拖动', '安全验证', '图形验证',
    ];
    const loginPatterns = [
        '请登录', '用户登录', '统一身份认证', 'login',
        '账号密码', '请输入密码',
    ];
    const forbiddenPatterns = [
        '403', 'Forbidden', '访问被拒绝', 'Access Denied',
        '请求被拦截', '访问受限',
    ];

    const lower = text.toLowerCase();

    for (const p of captchaPatterns) {
        if (lower.includes(p.toLowerCase())) return 'captcha';
    }

    // 检测验证码相关 DOM 元素
    const captchaSelectors = [
        '#captcha', '.captcha', '[class*="captcha"]',
        '[class*="verify"]', '[class*="slider"]',
        'iframe[src*="captcha"]',
    ];
    for (const sel of captchaSelectors) {
        if (document.querySelector(sel)) return 'captcha';
    }

    for (const p of loginPatterns) {
        if (lower.includes(p.toLowerCase())) {
            // 排除导航栏中的"登录"按钮（仅当页面主体是登录表单时才判定）
            const forms = document.querySelectorAll('form');
            const inputs = document.querySelectorAll('input[type="password"]');
            if (forms.length > 0 || inputs.length > 0) return 'login';
        }
    }

    for (const p of forbiddenPatterns) {
        if (lower.includes(p.toLowerCase())) {
            // 排除正常页面中偶尔出现的"403"数字
            if (text.trim().length < 500) return 'forbidden';
        }
    }

    return null;
}"""


async def detect_block(page: Page) -> BlockType | None:
    """检测页面是否被验证码/登录/403 阻断。"""
    if not config.CAPTCHA_DETECTION_ENABLED:
        return None

    try:
        result = await page.evaluate(_DETECT_JS)
    except Exception as exc:
        logger.debug("captcha 检测 JS 执行失败 (可能页面未就绪): %s", exc)
        return None

    if result == "captcha":
        return BlockType.CAPTCHA
    if result == "login":
        return BlockType.LOGIN
    if result == "forbidden":
        return BlockType.FORBIDDEN
    return None


_PROMPTS = {
    BlockType.CAPTCHA: (
        "\n╔══════════════════════════════════════════════════╗\n"
        "║  检测到验证码！请在浏览器中手动完成验证。       ║\n"
        "║  完成后按 Enter 继续，输入 q 放弃...            ║\n"
        "╚══════════════════════════════════════════════════╝\n"
    ),
    BlockType.LOGIN: (
        "\n╔══════════════════════════════════════════════════╗\n"
        "║  检测到登录页面！请在浏览器中手动登录。         ║\n"
        "║  完成后按 Enter 继续，输入 q 放弃...            ║\n"
        "╚══════════════════════════════════════════════════╝\n"
    ),
    BlockType.FORBIDDEN: (
        "\n╔══════════════════════════════════════════════════╗\n"
        "║  页面返回 403 / 访问被拒绝。                    ║\n"
        "║  请检查网络或在浏览器中刷新。                   ║\n"
        "║  处理后按 Enter 继续，输入 q 放弃...            ║\n"
        "╚══════════════════════════════════════════════════╝\n"
    ),
}


async def wait_for_human(block_type: BlockType, agent_id: str) -> bool:
    """暂停 agent 并等待用户在浏览器中手动处理。

    Returns:
        True  — 用户已处理，可继续
        False — 用户放弃或超时
    """
    prompt = _PROMPTS.get(block_type, _PROMPTS[BlockType.FORBIDDEN])
    logger.warning("[%s] 等待人工处理: %s", agent_id, block_type.value)

    try:
        user_input: str = await asyncio.wait_for(
            asyncio.to_thread(input, f"[{agent_id}] {prompt}> "),
            timeout=config.HUMAN_TAKEOVER_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning("[%s] 人工接管超时 (%ds)", agent_id, config.HUMAN_TAKEOVER_TIMEOUT_SEC)
        return False

    if user_input.strip().lower() == "q":
        logger.info("[%s] 用户选择放弃", agent_id)
        return False

    logger.info("[%s] 用户已确认处理完成，恢复执行", agent_id)
    return True
