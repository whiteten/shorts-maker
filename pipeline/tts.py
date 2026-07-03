"""TTS: 장면별 나레이션 → 음성(mp3) + 단어별 타이밍(json).

Edge-TTS(무료). 각 장면 오디오를 개별 파일로 만들고, WordBoundary 이벤트로
단어별 시작/길이(초)를 기록한다 → compose에서 음성에 싱크된 애니 자막에 사용.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import edge_tts

import settings as config


def _expand(text: str, start: float, dur: float) -> list[dict]:
    """문장(또는 단어) 구간을 단어들로 쪼개 글자 수 비례로 시간 배분."""
    toks = text.split()
    if not toks:
        return []
    total = sum(len(t) for t in toks) or 1
    out, acc = [], start
    for t in toks:
        wd = dur * (len(t) / total)
        out.append({"text": t, "start": acc, "dur": wd})
        acc += wd
    return out


async def _synth(text: str, mp3: Path, words_path: Path, voice: str) -> None:
    communicate = edge_tts.Communicate(text, voice)
    words: list[dict] = []
    with mp3.open("wb") as f:
        async for chunk in communicate.stream():
            t = chunk.get("type")
            if t == "audio":
                f.write(chunk["data"])
            elif t in ("WordBoundary", "SentenceBoundary"):
                # 100ns → 초. Sentence면 단어로 확장, Word면 그대로.
                words.extend(_expand(chunk["text"],
                                     chunk["offset"] / 1e7,
                                     chunk["duration"] / 1e7))
    words_path.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")


def synth_scenes(scenes: list[dict], run_dir: Path) -> list[Path]:
    """각 장면 나레이션을 음성 파일로 만들어 mp3 경로 리스트 반환.
    단어 타이밍은 같은 폴더에 scene_XX.words.json으로 저장."""
    audio_dir = run_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    async def run_all() -> list[Path]:
        paths: list[Path] = []
        for i, sc in enumerate(scenes, 1):
            mp3 = audio_dir / f"scene_{i:02d}.mp3"
            words = audio_dir / f"scene_{i:02d}.words.json"
            await _synth(sc.get("narration", ""), mp3, words, config.TTS_VOICE)
            paths.append(mp3)
        return paths

    return asyncio.run(run_all())


def words_for(audio: Path) -> list[dict]:
    """오디오 경로에 대응하는 단어 타이밍 로드(없으면 빈 리스트)."""
    wp = audio.with_name(audio.stem + ".words.json")
    if wp.exists():
        return json.loads(wp.read_text(encoding="utf-8"))
    return []


if __name__ == "__main__":
    demo = [{"narration": "You won't believe this exists in Korea."}]
    print(synth_scenes(demo, config.OUTPUT_DIR / "_tts_test"))
