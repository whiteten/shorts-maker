"""수동(Flow) 영상 소스.

각 장면의 video_prompt를 prompts.txt로 내보낸다. 사용자는 제미나이 Flow에서
클립을 뽑아 run_dir/clips/ 에 scene_01.mp4, scene_02.mp4 ... 이름으로 넣는다.
그 파일들이 모두 준비되면 경로 리스트를 반환한다(없으면 안내 후 중단).
"""
from __future__ import annotations

import sys
from pathlib import Path


def generate_clips(scenes: list[dict], run_dir: Path) -> list[Path]:
    clips_dir = run_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # 프롬프트 파일 작성
    prompts_path = run_dir / "prompts.txt"
    lines = []
    for i, sc in enumerate(scenes, 1):
        lines.append(f"### scene_{i:02d}  (파일명: clips/scene_{i:02d}.mp4)")
        lines.append(sc.get("video_prompt", ""))
        lines.append("")
    prompts_path.write_text("\n".join(lines), encoding="utf-8")

    expected = [clips_dir / f"scene_{i:02d}.mp4" for i in range(1, len(scenes) + 1)]
    missing = [p for p in expected if not p.exists()]

    if missing:
        print("\n" + "=" * 60)
        print("[manual] Flow에서 아래 프롬프트로 클립을 만들어 넣어주세요:")
        print(f"  프롬프트: {prompts_path}")
        print(f"  넣을 위치: {clips_dir}")
        print("  필요한 파일:")
        for p in missing:
            print(f"    - {p.name}")
        print("=" * 60)
        print("클립을 넣은 뒤 같은 명령을 다시 실행하면 이어서 진행됩니다.")
        sys.exit(0)

    return expected
