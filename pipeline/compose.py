"""FFmpeg 합성: 장면 클립 + 나레이션 + 자막 → 세로 쇼츠 mp4.

장면마다 (영상 클립을 오디오 길이에 맞춰 1080x1920로 크롭 + 자막 번인 + 나레이션 오디오)
세그먼트를 만들고, 전체를 이어붙인 뒤 BGM(있으면)을 낮게 믹스한다.

전제: 시스템에 ffmpeg / ffprobe 설치되어 있어야 함.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import config

# 한국어 자막 폰트 (Windows 기본 맑은고딕). 없으면 assets/font.ttf 사용.
_FONT = Path("C:/Windows/Fonts/malgun.ttf")
if not _FONT.exists():
    _FONT = config.ASSETS_DIR / "font.ttf"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def _ff_font() -> str:
    # ffmpeg 필터 안에서 콜론/역슬래시 이스케이프
    return str(_FONT).replace("\\", "/").replace(":", "\\:")


def _make_segment(clip: Path, audio: Path, caption: str, dest: Path) -> None:
    dur = _duration(audio) + 0.3  # 여운
    cap_file = dest.with_suffix(".caption.txt")
    cap_file.write_text(caption, encoding="utf-8")

    vf = (
        f"scale={config.WIDTH}:{config.HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={config.WIDTH}:{config.HEIGHT},"
        f"drawtext=fontfile='{_ff_font()}':textfile='{cap_file.as_posix()}':"
        f"fontcolor=white:fontsize=56:borderw=4:bordercolor=black:"
        f"x=(w-text_w)/2:y=h-360:line_spacing=10"
    )
    _run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(clip),
        "-i", str(audio),
        "-t", f"{dur:.2f}",
        "-vf", vf,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-r", str(config.FPS),
        str(dest),
    ])


def compose(scenes: list[dict], clips: list[Path], audios: list[Path],
            run_dir: Path) -> Path:
    seg_dir = run_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    segments: list[Path] = []
    for i, (sc, clip, audio) in enumerate(zip(scenes, clips, audios), 1):
        seg = seg_dir / f"seg_{i:02d}.mp4"
        _make_segment(clip, audio, sc.get("caption", ""), seg)
        segments.append(seg)

    # concat demuxer 리스트
    concat_list = seg_dir / "list.txt"
    concat_list.write_text(
        "\n".join(f"file '{s.as_posix()}'" for s in segments), encoding="utf-8"
    )

    final = run_dir / "short.mp4"
    bgm = config.ASSETS_DIR / "bgm.mp3"

    if bgm.exists():
        # 먼저 무BGM 합본을 만든 뒤 BGM 믹스
        merged = seg_dir / "_merged.mp4"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
               "-i", str(concat_list), "-c", "copy", str(merged)])
        _run([
            "ffmpeg", "-y", "-i", str(merged), "-stream_loop", "-1", "-i", str(bgm),
            "-filter_complex",
            "[1:a]volume=0.15[bg];[0:a][bg]amix=inputs=2:duration=first[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
            "-shortest", str(final),
        ])
    else:
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
               "-i", str(concat_list), "-c", "copy", str(final)])

    return final
