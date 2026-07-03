"""FFmpeg 합성: 장면 클립 + 나레이션 + 자막 → 세로 쇼츠 mp4.

장면마다 (영상 클립을 오디오 길이에 맞춰 1080x1920로 크롭 + 자막 번인 + 나레이션 오디오)
세그먼트를 만들고, 전체를 이어붙인 뒤 BGM(있으면)을 낮게 믹스한다.

전제: 시스템에 ffmpeg / ffprobe 설치되어 있어야 함.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import settings as config
from pipeline import tts

# 자막 폰트 (영어 기준 Arial Bold; 한국어면 맑은고딕으로 자동)
_FONT = Path("C:/Windows/Fonts/malgun.ttf")
if not _FONT.exists():
    _FONT = config.ASSETS_DIR / "font.ttf"

# 애니 자막 스타일
_CAP_FONT = "Arial"
_CAP_SIZE = 96
_GROUP = 3  # 한 번에 보여줄 단어 수


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if p.returncode != 0:
        tail = "\n".join((p.stderr or "").splitlines()[-8:])
        raise RuntimeError(f"ffmpeg 실패 (exit {p.returncode}):\n{tail}")


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def _ff_path(p) -> str:
    # ffmpeg 필터 인자용: 슬래시 통일 + 콜론 이스케이프 (Windows 'C:' 대응)
    return str(p).replace("\\", "/").replace(":", "\\:")


def _ass_ts(t: float) -> str:
    t = max(t, 0.0)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_text(s: str) -> str:
    return s.replace("{", "(").replace("}", ")").replace("\n", " ")


def _build_ass(words: list[dict], dest: Path, seg_dur: float) -> bool:
    """단어 타이밍 → 음성 싱크 애니 자막 ASS. 성공 시 True."""
    words = [w for w in words if w.get("text", "").strip()]
    if not words:
        return False

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {config.WIDTH}
PlayResY: {config.HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,{_CAP_FONT},{_CAP_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,7,3,2,60,60,540,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    n = len(words)
    lines = []
    for gi in range(0, n, _GROUP):
        chunk = words[gi:gi + _GROUP]
        for wi, w in enumerate(chunk):
            idx = gi + wi
            start = w["start"]
            end = words[idx + 1]["start"] if idx + 1 < n else w["start"] + w["dur"]
            end = min(end, seg_dur)
            if end <= start:
                end = start + 0.15
            parts = []
            for cj, cw in enumerate(chunk):
                t = _ass_text(cw["text"])
                if cj == wi:  # 현재 발화 단어 = 노랑 강조
                    parts.append(r"{\c&H0000FFFF&}" + t + r"{\c&H00FFFFFF&}")
                else:
                    parts.append(t)
            pop = r"{\fad(40,0)\t(0,110,\fscx118\fscy118)\t(110,190,\fscx100\fscy100)}" if wi == 0 else ""
            lines.append(
                f"Dialogue: 0,{_ass_ts(start)},{_ass_ts(end)},Pop,,0,0,0,,{pop}" +
                " ".join(parts)
            )
    dest.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return True


def _make_segment(clip: Path, audio: Path, caption: str, words: list[dict],
                  dest: Path) -> None:
    dur = _duration(audio) + 0.3  # 여운
    base = (f"scale={config.WIDTH}:{config.HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={config.WIDTH}:{config.HEIGHT}")

    ass = dest.with_suffix(".ass")
    if _build_ass(words, ass, dur):
        vf = f"{base},subtitles=filename='{_ff_path(ass)}'"
    else:  # 폴백: 정적 자막
        cap_file = dest.with_suffix(".caption.txt")
        cap_file.write_text(caption, encoding="utf-8")
        vf = (f"{base},drawtext=fontfile='{_ff_path(_FONT)}':"
              f"textfile='{_ff_path(cap_file)}':fontcolor=white:fontsize=56:"
              f"borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-360")

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
        _make_segment(clip, audio, sc.get("caption", ""), tts.words_for(audio), seg)
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
