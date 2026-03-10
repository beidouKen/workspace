"""关键词筛选与相关度打分。

打分逻辑：
  - 同时命中体育词 + 服务运营词 → high  (0.8 ~ 1.0)
  - 仅命中体育词                → medium (0.5 ~ 0.7)
  - 仅命中服务运营词            → low-medium (0.2 ~ 0.4)
  - 均未命中                    → low (0.0)
"""

from __future__ import annotations

from dataclasses import dataclass

from config import SERVICE_KEYWORDS, SPORTS_KEYWORDS


@dataclass
class FilterResult:
    score: float
    level: str  # "high" | "medium" | "low-medium" | "low"
    reasons: list[str]


def score_text(text: str) -> FilterResult:
    """对给定文本进行关键词匹配打分。"""
    if not text:
        return FilterResult(score=0.0, level="low", reasons=[])

    sports_hits: list[str] = []
    service_hits: list[str] = []

    for kw in SPORTS_KEYWORDS:
        if kw in text:
            sports_hits.append(kw)

    for kw in SERVICE_KEYWORDS:
        if kw in text:
            service_hits.append(kw)

    reasons: list[str] = []
    if sports_hits:
        reasons.append(f"命中体育词: {', '.join(sports_hits)}")
    if service_hits:
        reasons.append(f"命中服务运营词: {', '.join(service_hits)}")

    has_sports = len(sports_hits) > 0
    has_service = len(service_hits) > 0

    if has_sports and has_service:
        # 命中数越多分越高，上限 1.0
        score = min(1.0, 0.8 + 0.05 * (len(sports_hits) + len(service_hits) - 2))
        return FilterResult(score=score, level="high", reasons=reasons)

    if has_sports:
        score = min(0.7, 0.5 + 0.05 * (len(sports_hits) - 1))
        return FilterResult(score=score, level="medium", reasons=reasons)

    if has_service:
        score = min(0.4, 0.2 + 0.05 * (len(service_hits) - 1))
        return FilterResult(score=score, level="low-medium", reasons=reasons)

    return FilterResult(score=0.0, level="low", reasons=["未命中任何关键词"])


def apply_filter(items: list[dict]) -> list[dict]:
    """对 BidItem.to_dict() 列表做关键词打分，就地更新 match_score / match_reason。"""
    for item in items:
        combined = " ".join([
            item.get("title", ""),
            item.get("summary", ""),
            item.get("detail_text", ""),
        ])
        result = score_text(combined)
        item["match_score"] = result.score
        item["match_reason"] = result.reasons
    # 按分数降序排列
    items.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return items
