"""영상 소스 모듈. VIDEO_SOURCE 설정에 따라 구현을 고른다."""
from __future__ import annotations

from pathlib import Path

import config


def generate_clips(scenes: list[dict], run_dir: Path) -> list[Path]:
    """각 장면에 대한 영상 클립 파일 경로 리스트를 반환.

    구현은 VIDEO_SOURCE 값으로 분기:
      - manual: 프롬프트를 파일로 내보내고, 사용자가 Flow에서 넣은 클립을 회수 (무료·수동)
      - auto:   무료 이미지 생성 + Ken Burns 모션 (무료·완전자동)
      - veo:    Gemini Veo API로 자동 생성 (유료·완전자동)
    """
    if config.VIDEO_SOURCE == "veo":
        from . import veo
        return veo.generate_clips(scenes, run_dir)
    if config.VIDEO_SOURCE == "auto":
        from . import auto
        return auto.generate_clips(scenes, run_dir)
    from . import manual
    return manual.generate_clips(scenes, run_dir)
