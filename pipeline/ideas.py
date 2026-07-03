"""주제 아이디어 생성 — 해외 타깃 '한국 관련 쇼츠' 니치.

트렌드 실시간 검색어 대신, 조회수 검증된 '한국 문화/기술 차이' 포맷의 영어 주제를
LLM으로 매일 새로 생성한다. 이미 쓴 주제는 output/used_topics.txt로 중복 방지.
"""
from __future__ import annotations

import json

import httpx

import settings as config

# 검증된 시드 주제(폴백 + LLM에 스타일 예시로 제공). 실존 인물/브랜드 없음.
SEED_TOPICS = [
    "Why Korea has no trash cans on the streets",
    "Why Korean food delivery is insanely fast",
    "Why Koreans don't wear shoes indoors",
    "Why Korean apartments all look the same",
    "Why Korea has 24-hour everything",
    "Why the Korean subway feels like the future",
    "Why Koreans have two different ages",
    "Why there is no tipping in Korea",
    "Why Korean public bathrooms are so clean",
    "Why Koreans use metal chopsticks",
    "Why Korea has the fastest internet in the world",
    "Why Korean convenience stores can do everything",
    "Why Korea has call buttons on every restaurant table",
    "Why Koreans get free side dishes at restaurants",
    "Why Korean cafes stay open all night",
]

_USED_FILE = config.OUTPUT_DIR / "used_topics.txt"

_GEN_SYSTEM = """You generate ideas for viral ENGLISH YouTube Shorts about Korea,
aimed at a global audience fascinated by Korean culture, technology, and daily
life. Titles follow the proven "Why Korea..." / "Only in Korea" curiosity style.
SAFETY: never mention real people, celebrities, or brand names — only general
cultural/technological facts. Output ONLY JSON: {"ideas": ["title", ...]}"""


def _used() -> set[str]:
    if _USED_FILE.exists():
        return {l.strip() for l in _USED_FILE.read_text(encoding="utf-8").splitlines() if l.strip()}
    return set()


def mark_used(topic: str) -> None:
    _USED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _USED_FILE.open("a", encoding="utf-8") as f:
        f.write(topic.strip() + "\n")


def _via_ollama(n: int, avoid: set[str]) -> list[str]:
    avoid_list = "\n".join(f"- {t}" for t in list(avoid)[:60])
    user = (
        f"Give me {n} fresh short-video title ideas in the same style as these "
        f"examples:\n" + "\n".join(f"- {s}" for s in SEED_TOPICS[:8]) +
        (f"\n\nDo NOT repeat any of these already-used titles:\n{avoid_list}"
         if avoid else "")
    )
    resp = httpx.post(
        f"{config.OLLAMA_HOST}/api/chat",
        json={
            "model": config.OLLAMA_MODEL, "format": "json", "stream": False,
            "messages": [
                {"role": "system", "content": _GEN_SYSTEM},
                {"role": "user", "content": user},
            ],
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = json.loads(resp.json()["message"]["content"])
    return [t.strip() for t in data.get("ideas", []) if t.strip()]


def generate_ideas(n: int = 1) -> list[str]:
    """중복을 피한 새 주제 n개. LLM 실패 시 시드에서 미사용분 폴백."""
    used = _used()
    try:
        ideas = [t for t in _via_ollama(max(n, 5), used) if t not in used]
        if ideas:
            return ideas[:n]
    except Exception as e:  # noqa: BLE001
        print(f"[ideas] LLM 실패, 시드 폴백: {e}")
    fresh = [t for t in SEED_TOPICS if t not in used]
    return (fresh or SEED_TOPICS)[:n]


def pick_topic() -> str:
    return generate_ideas(1)[0]


if __name__ == "__main__":
    for t in generate_ideas(8):
        print("-", t)
