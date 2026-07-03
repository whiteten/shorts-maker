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
- video_prompt: an English prompt for an image generator describing realistic,
  documentary-style b-roll of the Korean scene (vertical 9:16).
  SAFETY (must follow): NO text or letters in the image; NO real, famous, or
  recognizable people's faces; NO celebrities; NO brand names, logos, or
  trademarks. Use generic streets, objects, food, buildings, environments.
- caption: a short ENGLISH on-screen caption (summary of the narration).
- Final scene: invite a follow and end with an "Only in Korea"-style punchline.

Output ONLY this JSON (no prose, no code fences):
{{"title","description","hashtags":[],"scenes":[{{"narration","video_prompt","caption"}}]}}"""


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
    if config.SCRIPT_BACKEND == "claude":
        data = _via_claude(topic)
    else:
        data = _via_ollama(topic)
    data["topic"] = topic
    return data


if __name__ == "__main__":
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "오늘의 트렌드"
    print(json.dumps(generate_script(topic), ensure_ascii=False, indent=2))
