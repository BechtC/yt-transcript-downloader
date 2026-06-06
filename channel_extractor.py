"""YouTube Channel Video URL Extractor
Adapted from YT-Channel to CSV project.
"""
import re
import logging
from urllib.parse import urlparse, parse_qs
from typing import List, Tuple
import yt_dlp

logger = logging.getLogger(__name__)

YT_DLP_OPTS = {
    'quiet': True, 'extract_flat': 'in_playlist', 'force_generic_extractor': False,
    'playlistreverse': False, 'simulate': True, 'ignoreerrors': True,
    'no_warnings': True, 'extract_flat_playlist': True, 'playlist_items': '1-10000',
}


class ChannelExtractor:
    def __init__(self, url: str):
        self.url = url
        self.ydl_opts = YT_DLP_OPTS.copy()

    @staticmethod
    def detect_url_type(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parse_qs(parsed.query)
        if 'list' in query or '/playlist' in path:
            return 'playlist'
        if (path.startswith('/@') or '/channel/' in path
                or '/user/' in path or '/c/' in path or path.endswith('/videos')):
            return 'channel'
        return 'unknown'

    @staticmethod
    def extract_channel_name(url: str) -> str:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if path_parts:
            part = path_parts[0]
            if part.startswith('@'):
                name = part[1:]
            elif part in ('channel', 'user', 'c'):
                name = path_parts[1] if len(path_parts) > 1 else 'channel'
            else:
                name = part
        else:
            name = 'channel'
        return re.sub(r'[^\w\-_]', '_', name)

    def get_video_urls(self) -> Tuple[str, List[str]]:
        url = self.url
        url_type = self.detect_url_type(url)
        channel_name = self.extract_channel_name(url)
        if url_type == 'channel' and not url.rstrip('/').endswith('/videos'):
            url = f"{url.rstrip('/')}/videos"
        logger.info(f"Scanning channel: {url}")
        video_urls = []
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and 'entries' in info:
                    for entry in info['entries']:
                        if entry and 'id' in entry:
                            video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            raise
        logger.info(f"Found {len(video_urls)} videos for channel '{channel_name}'")
        return channel_name, video_urls
