"""Veo(Gemini API) 영상 소스 — 자동 생성. 초당 과금 주의.

google-genai SDK 사용. 각 장면 video_prompt로 8초 내외 세로 클립 생성.
문서: https://ai.google.dev/gemini-api/docs/video
"""
from __future__ import annotations

import time
from pathlib import Path

import config


def generate_clips(scenes: list[dict], run_dir: Path) -> list[Path]:
    from google import genai  # 지연 임포트 (manual 모드에선 불필요)

    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY가 비어 있습니다 (.env 확인).")

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    out: list[Path] = []
    for i, sc in enumerate(scenes, 1):
        dest = clips_dir / f"scene_{i:02d}.mp4"
        if dest.exists():
            out.append(dest)
            continue

        prompt = sc.get("video_prompt", "")
        print(f"[veo] scene {i}/{len(scenes)} 생성 중… (초당 과금)")

        # 비동기 작업 시작 → 폴링
        op = client.models.generate_videos(
            model=config.VEO_MODEL,
            prompt=prompt,
            config={"aspect_ratio": "9:16"},
        )
        while not op.done:
            time.sleep(10)
            op = client.operations.get(op)

        video = op.response.generated_videos[0]
        client.files.download(file=video.video)
        video.video.save(str(dest))
        out.append(dest)

    return out
