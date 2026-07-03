"""TTS: 장면별 나레이션 → 한국어 음성(mp3). Edge-TTS(무료).

각 장면 오디오를 개별 파일로 만들어, 그 길이에 맞춰 영상/자막을 배치할 수 있게 한다.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

import settings as config


async def _synth(text: str, dest: Path, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(dest))


def synth_scenes(scenes: list[dict], run_dir: Path) -> list[Path]:
    """각 장면 나레이션을 음성 파일로 만들어 경로 리스트 반환."""
    audio_dir = run_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    async def run_all() -> list[Path]:
        paths: list[Path] = []
        for i, sc in enumerate(scenes, 1):
            dest = audio_dir / f"scene_{i:02d}.mp3"
            await _synth(sc.get("narration", ""), dest, config.TTS_VOICE)
            paths.append(dest)
        return paths

    return asyncio.run(run_all())


if __name__ == "__main__":
    demo = [{"narration": "안녕하세요, 테스트 음성입니다."}]
    print(synth_scenes(demo, config.OUTPUT_DIR / "_tts_test"))
