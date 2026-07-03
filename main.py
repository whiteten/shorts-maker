"""쇼츠 자동 생성 오케스트레이터.

사용법:
  python main.py                 # 트렌드 1건 → 쇼츠 1개 생성 (업로드 안 함)
  python main.py --topic "주제"  # 주제 직접 지정
  python main.py --upload        # 생성 후 유튜브 업로드까지
  python main.py --count 3       # 트렌드 상위 3건으로 3개 생성
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import settings as config
from pipeline import compose, script, trends, tts
from pipeline import upload as uploader
from pipeline import video


def _slug(text: str) -> str:
    keep = "".join(c if c.isalnum() or c in " -_" else "" for c in text)
    return keep.strip().replace(" ", "_")[:40] or "short"


def make_one(topic: str, do_upload: bool) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = config.OUTPUT_DIR / f"{stamp}_{_slug(topic)}"
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== 주제: {topic} ===\n작업 폴더: {run_dir}")

    # 1. 스크립트
    print("[1/5] 스크립트 생성…")
    data = script.generate_script(topic)
    (run_dir / "script.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes = data["scenes"]

    # 2. 영상 클립 (manual 모드면 여기서 사용자 개입 후 재실행)
    print(f"[2/5] 영상 클립 확보… (source={config.VIDEO_SOURCE})")
    clips = video.generate_clips(scenes, run_dir)

    # 3. TTS
    print("[3/5] 나레이션 음성 생성…")
    audios = tts.synth_scenes(scenes, run_dir)

    # 4. 합성
    print("[4/5] FFmpeg 합성…")
    final = compose.compose(scenes, clips, audios, run_dir)
    print(f"    완성: {final}")

    # 5. 업로드 (옵션)
    if do_upload:
        print("[5/5] 유튜브 업로드…")
        uploader.upload(final, data)
    else:
        print("[5/5] 업로드 생략 (검토 후 --upload 로 게시).")

    return final


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="주제 직접 지정")
    ap.add_argument("--count", type=int, default=1, help="트렌드 상위 N건 생성")
    ap.add_argument("--upload", action="store_true", help="생성 후 업로드")
    args = ap.parse_args()

    if args.topic:
        topics = [args.topic]
    else:
        topics = trends.fetch_trending(args.count)

    for t in topics:
        make_one(t, args.upload)


if __name__ == "__main__":
    main()
