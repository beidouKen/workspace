"""全局配置：站点信息、关键词、运行参数。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# 站点配置
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SiteConfig:
    alias: str
    name: str
    entry_url: str
    expected_domain: str
    fallback_urls: list[str] = field(default_factory=list)


SITE_GZ_TYJ = SiteConfig(
    alias="tab_gz_tyj",
    name="广州市体育局",
    entry_url="https://tyj.gz.gov.cn/tzgg/cgzb/",
    expected_domain="tyj.gz.gov.cn",
)

SITE_GDGPO = SiteConfig(
    alias="tab_gdgpo",
    name="广东政府采购网",
    entry_url="https://gdgpo.czt.gd.gov.cn/cms-gd/site/guangdong/cggg/index.html",
    expected_domain="gdgpo.czt.gd.gov.cn",
    fallback_urls=[
        "https://gdgpo.czt.gd.gov.cn/freecms/site/guangdong/wlzfcgxx/index.html",
        "https://gdgpo.czt.gd.gov.cn/",
    ],
)

ALL_SITES = [SITE_GZ_TYJ, SITE_GDGPO]

# ---------------------------------------------------------------------------
# 关键词
# ---------------------------------------------------------------------------

SPORTS_KEYWORDS: list[str] = [
    "体育", "运动", "全民健身", "健身", "体育馆",
    "体育中心", "场馆", "赛事",
]

SERVICE_KEYWORDS: list[str] = [
    "服务", "运营", "管理", "承办", "培训",
    "维护", "保障", "活动组织", "执行",
]

# ---------------------------------------------------------------------------
# 运行参数
# ---------------------------------------------------------------------------

MAX_ITEMS_PER_SITE: int = 5
PAGE_LOAD_TIMEOUT_MS: int = 30_000
ACTION_DELAY_SEC: float = 2.0
DETAIL_TEXT_MAX_LEN: int = 500
MAX_RETRIES: int = 2

# ---------------------------------------------------------------------------
# 输出路径
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"
REPORT_JSON_PATH = OUTPUT_DIR / "report.json"
REPORT_HTML_PATH = OUTPUT_DIR / "report.html"
