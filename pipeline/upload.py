"""YouTube 업로드: 완성 mp4 → YouTube Data API v3.

최초 1회 브라우저 OAuth 동의 후 token.json에 저장, 이후 자동 갱신.
Google Cloud Console에서 'YouTube Data API v3' 사용 설정 + OAuth 클라이언트(데스크톱)
만들어 client_secret.json 다운로드 필요.
"""
from __future__ import annotations

from pathlib import Path

import settings as config

_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_TOKEN = config.ROOT / "token.json"


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if _TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN), _SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.YOUTUBE_CLIENT_SECRET, _SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload(video_path: Path, script: dict) -> str:
    """영상을 업로드하고 videoId 반환."""
    from googleapiclient.http import MediaFileUpload

    youtube = _service()
    tags = [h.lstrip("#") for h in script.get("hashtags", [])]
    body = {
        "snippet": {
            "title": script.get("title", "Shorts")[:100],
            "description": script.get("description", "") + "\n\n" +
                           " ".join(script.get("hashtags", [])) + "\n#Shorts",
            "tags": tags,
            "categoryId": config.YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": config.YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True,
                            mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = req.execute()
    vid = resp["id"]
    print(f"[upload] 완료: https://youtu.be/{vid}  (공개범위={config.YOUTUBE_PRIVACY})")
    return vid
