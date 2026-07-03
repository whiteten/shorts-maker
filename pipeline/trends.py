"""트렌드 수집: Google Trends 한국 실시간 인기 검색어 RSS.

공식 RSS라 키·인증 불필요. 실패 시 폴백 키워드 사용.
"""
from __future__ import annotations

import feedparser

TRENDS_RSS = "https://trends.google.com/trending/rss?geo=KR"

_FALLBACK = ["오늘의 이슈", "생활 꿀팁", "알아두면 좋은 상식"]


def fetch_trending(limit: int = 10) -> list[str]:
    """한국 실시간 인기 검색어 상위 N개를 반환."""
    try:
        feed = feedparser.parse(TRENDS_RSS)
        titles = [e.title.strip() for e in feed.entries if getattr(e, "title", "").strip()]
        if titles:
            return titles[:limit]
    except Exception as e:  # noqa: BLE001
        print(f"[trends] RSS 실패, 폴백 사용: {e}")
    return _FALLBACK[:limit]


def pick_topic() -> str:
    """가장 인기 있는 주제 하나를 고른다."""
    return fetch_trending(1)[0]


if __name__ == "__main__":
    for i, t in enumerate(fetch_trending(), 1):
        print(f"{i:2}. {t}")
