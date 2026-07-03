"""중앙 설정 로더. .env를 읽어 상수로 노출."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
ASSETS_DIR = ROOT / "assets"  # BGM, 폰트 등

# 스크립트 생성  (backend: ollama=무료 기본 | claude=유료)
SCRIPT_BACKEND = os.getenv("SCRIPT_BACKEND", "ollama").lower()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SCRIPT_MODEL = os.getenv("SCRIPT_MODEL", "claude-opus-4-8")

# 영상 생성  (manual=Flow수동·무료 | auto=이미지+모션·무료 | veo=API·유료)
VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "manual").lower()
IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "pollinations").lower()  # auto 모드용
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
VEO_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview")

# 콘텐츠
LANGUAGE = os.getenv("LANGUAGE", "ko")
SHORT_SECONDS = int(os.getenv("SHORT_SECONDS", "45"))
TTS_VOICE = os.getenv("TTS_VOICE", "ko-KR-SunHiNeural")

# 유튜브
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "client_secret.json")
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "24")

# 세로 쇼츠 규격
WIDTH, HEIGHT = 1080, 1920
FPS = 30
