"""스크립트 생성: 주제 → LLM → 구조화된 쇼츠 대본(JSON).

백엔드 전환(config.SCRIPT_BACKEND):
  - ollama : 로컬 무료 (기본, qwen2.5:7b)
  - claude : Anthropic API (유료, 품질↑)

반환 구조:
{
  "title": "...", "description": "...", "hashtags": ["#..", ...],
  "scenes": [
    {"narration": "나레이션", "video_prompt": "영어 영상 프롬프트", "caption": "화면 자막"},
    ...
  ]
}
"""
from __future__ import annotations

import json
import shutil
import subprocess

import httpx

import settings as config

_SYSTEM = """You write viral ENGLISH YouTube Shorts about Korea for a global
audience curious about Korean culture, technology, and daily life.
Given a topic, write a {seconds}-second vertical short.

RULES
- Language: English. Punchy, conversational, energetic — spoken narration.
- Structure: a strong HOOK in the first 3 seconds (e.g. "You won't believe
  this exists in Korea"), then 3-5 quick fact scenes, then a closing scene
  that ends with a memorable line like "Only in Korea."
- 4-6 scenes total. Each narration is 1-2 short sentences.
- ACCURACY (critical): state only widely-known, TRUE facts about Korea. Do NOT
  invent statistics, percentages, or numbers. Never encourage or praise illegal
  or unsafe behavior. Keep the tone positive and respectful toward Korea.
- video_prompt: an English prompt for an image generator describing realistic,
  documentary-style b-roll (vertical 9:16). Every scene is EXPLICITLY SET IN
  KOREA — describe Korean people, Korean streets/architecture, Seoul, hangul
  signage (blurred/unreadable), so it clearly looks Korean.
  SAFETY (must follow): NO readable text or letters in the image; NO real,
  famous, or recognizable people's faces; NO celebrities; NO brand names,
  logos, or trademarks.
- caption: a short ENGLISH on-screen caption (summary of the narration).
- stock_query: 2-4 English keywords to find matching REAL stock FOOTAGE for
  this scene (e.g. "Seoul street night", "Korean apartment building",
  "night market food"). Use concrete, filmable subjects — generic enough that
  stock libraries will have it, but Korea/Asia-flavored when possible.
- Final scene: invite a follow and end with an "Only in Korea"-style punchline.

Output ONLY this JSON (no prose, no code fences):
{{"title","description","hashtags":[],"scenes":[{{"narration","video_prompt","caption","stock_query"}}]}}"""


def _prompt(topic: str) -> tuple[str, str]:
    system = _SYSTEM.format(seconds=config.SHORT_SECONDS)
    user = f"Topic: {topic}\n\nWrite the short's script as JSON."
    return system, user


def _clean_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    return json.loads(text)


def _via_ollama(topic: str) -> dict:
    system, user = _prompt(topic)
    resp = httpx.post(
        f"{config.OLLAMA_HOST}/api/chat",
        json={
            "model": config.OLLAMA_MODEL,
            "format": "json",  # JSON 강제
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=300,
    )
    resp.raise_for_status()
    return _clean_json(resp.json()["message"]["content"])


def _via_claude_cli(topic: str) -> dict:
    """Claude Code CLI 헤드리스(`claude -p`)로 생성. Max 구독 인증 사용, API 키 불필요."""
    system, user = _prompt(topic)
    full = f"{system}\n\n{user}\n\n(Remember: output ONLY the JSON object.)"
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", "--output-format", "json"]
    if config.CLAUDE_CLI_MODEL:
        cmd += ["--model", config.CLAUDE_CLI_MODEL]
    p = subprocess.run(cmd, input=full, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f"claude CLI 실패 (exit {p.returncode}): {(p.stderr or '')[:300]}")
    envelope = json.loads(p.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude CLI 오류: {str(envelope.get('result',''))[:300]}")
    return _clean_json(envelope["result"])


def _via_claude(topic: str) -> dict:
    from anthropic import Anthropic

    system, user = _prompt(topic)
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.SCRIPT_MODEL, max_tokens=2000,
        system=system, messages=[{"role": "user", "content": user}],
    )
    return _clean_json(msg.content[0].text)


def generate_script(topic: str) -> dict:
    if config.SCRIPT_BACKEND == "claude_cli":
        data = _via_claude_cli(topic)
    elif config.SCRIPT_BACKEND == "claude":
        data = _via_claude(topic)
    else:
        data = _via_ollama(topic)
    data["topic"] = topic
    return data


if __name__ == "__main__":
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "오늘의 트렌드"
    print(json.dumps(generate_script(topic), ensure_ascii=False, indent=2))
