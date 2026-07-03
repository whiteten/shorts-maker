"""자동(무료) 영상 소스 — 이미지 생성 + Ken Burns 모션.

각 장면 video_prompt로 세로 이미지를 생성하고, FFmpeg zoompan(확대/이동)으로
움직이는 클립(mp4)을 만든다. GPU·키·수작업 불필요. '진짜 영상'은 아니지만 완전 자동.

이미지 생성 백엔드(config.IMAGE_BACKEND):
  - pollinations : 무료 이미지 생성 API(키 없음). 기본값.
  - (추후) local : 로컬 SDXL 등으로 교체 가능 — generate_image()만 갈아끼우면 됨.
"""
from __future__ import annotations

import subprocess
import urllib.parse
from pathlib import Path

import httpx

import settings as config

_CLIP_SECONDS = 10  # 넉넉히 만들고 compose에서 오디오 길이에 맞춰 자름


def _generate_image(prompt: str, dest: Path) -> None:
    """무료 이미지 생성(Pollinations). 실패 시 예외."""
    enc = urllib.parse.quote(prompt)
    url = (f"https://image.pollinations.ai/prompt/{enc}"
           f"?width={config.WIDTH}&height={config.HEIGHT}&nologo=true")
    r = httpx.get(url, timeout=120, follow_redirects=True)
    r.raise_for_status()
    dest.write_bytes(r.content)


def _ken_burns(image: Path, dest: Path) -> None:
    """정지 이미지 → 확대/이동 모션 클립."""
    frames = _CLIP_SECONDS * config.FPS
    vf = (
        f"scale={config.WIDTH*2}:{config.HEIGHT*2},"
        f"zoompan=z='min(zoom+0.0012,1.2)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={config.WIDTH}x{config.HEIGHT}:fps={config.FPS}"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-vf", vf, "-t", str(_CLIP_SECONDS),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest),
    ], check=True, capture_output=True)


def generate_clips(scenes: list[dict], run_dir: Path) -> list[Path]:
    img_dir = run_dir / "images"
    clips_dir = run_dir / "clips"
    img_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    out: list[Path] = []
    for i, sc in enumerate(scenes, 1):
        clip = clips_dir / f"scene_{i:02d}.mp4"
        if clip.exists():
            out.append(clip)
            continue
        img = img_dir / f"scene_{i:02d}.jpg"
        print(f"[auto] scene {i}/{len(scenes)} 이미지 생성…")
        _generate_image(sc.get("video_prompt", ""), img)
        _ken_burns(img, clip)
        out.append(clip)
    return out
