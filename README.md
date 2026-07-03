# shorts-maker

트렌드를 자동 조사해서 **AI 영상(제미나이 Veo)** 기반 유튜브 쇼츠를 만들고 업로드하는 자동화 파이프라인.

## 파이프라인

```
1. trends   트렌드 수집 (Google Trends KR RSS)
2. script   스크립트/장면 생성 (Claude)
3. video    AI 영상 클립 생성 (Veo API  또는  Flow 수동)   ← 갈아끼움 가능
4. tts      한국어 음성 (Edge-TTS, 무료)
5. compose  FFmpeg 합성 (세로 1080x1920 + 자막 번인 + BGM)
6. review   완성본을 output/ 에 저장 (사람이 확인)
7. upload   YouTube Data API v3 업로드
```

기본값: **한국어 · 검토 후 업로드(반자동)**.

## 영상 생성 방식 (`.env`의 VIDEO_SOURCE로 선택)

| 값 | 설명 | 비용 | 자동화 |
|---|---|---|---|
| `manual` | 장면 프롬프트를 `output/<run>/prompts.txt`로 내보냄. 제미나이 Flow에서 손으로 뽑아 `output/<run>/clips/`에 넣으면 이어서 진행. | 구독료뿐 | 반자동 |
| `auto` | 무료 이미지 생성(Pollinations) + FFmpeg Ken Burns 모션. "움직이는 이미지". | **0원** | 완전자동 |
| `veo` | Gemini API(Veo)로 진짜 AI 영상 자동 생성. | ~$0.15/초 | 완전자동 |

**완전 무료 구성**: 스크립트=`ollama`(qwen2.5:7b), 영상=`manual` 또는 `auto`, TTS=Edge-TTS.

## 설치

```bash
pip install -r requirements.txt
# ffmpeg 필요 (Windows): winget install Gyan.FFmpeg   또는  https://ffmpeg.org
```

`.env.example`를 `.env`로 복사하고 값 채우기.

## 실행

```bash
python main.py                # 트렌드 1건으로 쇼츠 1개 생성
python main.py --topic "직접 지정한 주제"
python main.py --upload       # 생성 후 바로 업로드까지
```

## 상태

🚧 스캐폴드 단계. 각 모듈은 동작하는 스텁이며 TODO 표시된 부분(자격증명/키)을 채워야 완전 동작.
