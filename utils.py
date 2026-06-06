"""Utility functions for YouTube Transcript Tool"""
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse


def extract_video_id(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if parsed.netloc in ['youtube.com', 'www.youtube.com']:
            query = parse_qs(parsed.query)
            if 'v' in query:
                return query['v'][0]
    except Exception:
        pass
    for pattern in [r'(?:v=|/)([0-9A-Za-z_-]{11}).*', r'youtu\.be/([0-9A-Za-z_-]{11})', r'embed/([0-9A-Za-z_-]{11})']:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"[{h:02d}:{m:02d}:{s:02d}]" if h > 0 else f"[{m:02d}:{s:02d}]"


def create_safe_filename(video_id: str, extension: str) -> str:
    return f"transcript_{re.sub(r'[^\\w\\-_]', '', video_id)}.{extension}"
