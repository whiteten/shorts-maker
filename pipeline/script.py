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

_SYSTEM = """너는 유튜브 쇼츠 대본 작가다. 주어진 주제로 {seconds}초 분량의
세로형 쇼츠 대본을 만든다. 규칙:
- 첫 3초에 강한 훅(hook)으로 시청자를 붙잡는다.
- 장면(scene)은 4~6개. 각 장면 나레이션은 한국어로 1~2문장(짧고 임팩트 있게).
- 각 장면의 video_prompt는 영상 생성 모델용 '영어' 프롬프트로, 세로 9:16 구도,
  구체적 피사체·움직임·분위기를 묘사한다. 화면에 글자/자막은 넣지 말 것.
- caption은 화면에 번인할 짧은 한국어 자막(나레이션 요약).
- 마지막 장면은 구독/좋아요 유도로 마무리.
반드시 아래 JSON 스키마만 출력한다(설명·코드펜스 없이):
{{"title","description","hashtags":[],"scenes":[{{"narration","video_prompt","caption"}}]}}"""


def _prompt(topic: str) -> tuple[str, str]:
    system = _SYSTEM.format(seconds=config.SHORT_SECONDS)
    user = f"주제: {topic}\n\n위 주제로 쇼츠 대본을 JSON으로 만들어줘."
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
