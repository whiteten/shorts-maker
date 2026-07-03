"""실사 스톡 영상 소스 — Pexels Videos API (무료 키).

각 장면 stock_query로 세로 실사 푸티지를 검색·다운로드한다. 결과가 없거나 키가
없으면 그 장면만 auto(이미지+모션)로 폴백해 파이프라인이 끊기지 않게 한다.

키 발급(무료·즉시): https://www.pexels.com/api/  → .env의 PEXELS_API_KEY
"""
from __future__ import annotations

from pathlib import Path

import httpx

import settings as config
from . import auto

_SEARCH = "https://api.pexels.com/videos/search"


def _query_for(sc: dict) -> str:
    q = (sc.get("stock_query") or sc.get("caption") or "").strip()
    return q or "Seoul Korea city"


def _find_clip_url(query: str, key: str) -> str | None:
    """세로에 가까운 적당한 화질의 mp4 링크를 하나 고른다."""
    r = httpx.get(
        _SEARCH,
        headers={"Authorization": key},
        params={"query": query, "orientation": "portrait",
                "per_page": 5, "size": "medium"},
        timeout=60,
    )
    r.raise_for_status()
    videos = r.json().get("videos", [])
    for v in videos:
        # 세로 우선, 해상도 720~1080 근처 mp4
        files = sorted(
            (f for f in v.get("video_files", []) if f.get("link")),
            key=lambda f: abs((f.get("height") or 0) - config.HEIGHT),
        )
        portrait = [f for f in files if (f.get("height") or 0) >= (f.get("width") or 0)]
        pick = (portrait or files)
        if pick:
            return pick[0]["link"]
    return None


def _download(url: str, dest: Path) -> None:
    with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(1 << 16):
                f.write(chunk)


def generate_clips(scenes: list[dict], run_dir: Path) -> list[Path]:
    key = config.PEXELS_API_KEY
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    out: list[Path] = []
    for i, sc in enumerate(scenes, 1):
        clip = clips_dir / f"scene_{i:02d}.mp4"
        if clip.exists():
            out.append(clip)
            continue

        url = None
        if key:
            try:
                url = _find_clip_url(_query_for(sc), key)
            except Exception as e:  # noqa: BLE001
                print(f"[stock] scene {i} 검색 실패: {e}")

        if url:
            print(f"[stock] scene {i}/{len(scenes)} 실사 다운로드… ({_query_for(sc)})")
            try:
                _download(url, clip)
                out.append(clip)
                continue
            except Exception as e:  # noqa: BLE001
                print(f"[stock] scene {i} 다운로드 실패, 폴백: {e}")

        # 폴백: 이 장면만 이미지+모션
        print(f"[stock] scene {i}/{len(scenes)} 스톡 없음 → 이미지 폴백")
        img = (run_dir / "images"); img.mkdir(exist_ok=True)
        img_path = img / f"scene_{i:02d}.jpg"
        auto._generate_image(sc.get("video_prompt", ""), img_path)
        auto._ken_burns(img_path, clip)
        out.append(clip)

    return out
