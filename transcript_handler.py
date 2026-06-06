"""Handler for fetching and processing YouTube transcripts."""
from typing import Optional, List, Dict, Union, Tuple
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._errors import VideoUnavailable
import pandas as pd
from pathlib import Path
import logging
import time
from tqdm import tqdm
import requests
from datetime import datetime

from config import DEFAULT_TRANSCRIPT_LANG, MAX_RETRIES, ERROR_MESSAGES, OUTPUT_FILE_TEMPLATE, YOUTUBE_API_KEY
from utils import extract_video_id, format_timestamp, create_safe_filename


class TranscriptHandler:
    def __init__(self, language: str = DEFAULT_TRANSCRIPT_LANG):
        self.language = language
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('transcript_download.log'), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def get_video_details(self, video_id: str) -> Optional[str]:
        try:
            params = {'part': 'snippet', 'id': video_id, 'key': YOUTUBE_API_KEY}
            response = requests.get("https://www.googleapis.com/youtube/v3/videos", params=params)
            data = response.json()
            if 'items' in data and data['items']:
                upload_date = data['items'][0]['snippet']['publishedAt']
                return datetime.strptime(upload_date, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y%m%d')
            return None
        except Exception as e:
            self.logger.error(f"Error fetching video details: {str(e)}")
            return None

    def create_filename_with_date(self, video_id: str, upload_date: Optional[str]) -> str:
        date_prefix = f"{upload_date}_" if upload_date else ""
        return f"{date_prefix}{video_id}.txt"

    def get_transcript(self, video_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns (transcript_text, upload_date, error_reason). error_reason is None on success."""
        video_id = extract_video_id(video_url)
        if not video_id:
            return None, None, "Ungültige URL"

        upload_date = self.get_video_details(video_id)

        for attempt in range(MAX_RETRIES):
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                all_transcripts = list(transcript_list)
                if not all_transcripts:
                    return None, upload_date, "Kein Transkript verfügbar"

                preferred_lang = self.language
                transcript = None
                source = None

                # 1) Manuelle Spur in gewünschter Sprache
                for t in all_transcripts:
                    if t.language_code == preferred_lang and not t.is_generated:
                        transcript, source = t, preferred_lang
                        break

                # 2) Auto/ASR-Spur in gewünschter Sprache
                if not transcript:
                    for t in all_transcripts:
                        if t.language_code == preferred_lang:
                            transcript, source = t, f"{preferred_lang} (auto)"
                            break

                # 3) Englische Spur
                if not transcript:
                    for t in all_transcripts:
                        if t.language_code == 'en':
                            transcript, source = t, "en (Fallback)"
                            break

                # 4) Erste verfügbare Spur
                if not transcript:
                    transcript = all_transcripts[0]
                    source = f"{transcript.language_code} (Fallback)"

                transcript_data = transcript.fetch()
                self.logger.info(f"Transcript fetched for {video_id} [{source}]")
                return self._format_transcript(transcript_data), upload_date, None

            except TranscriptsDisabled:
                return None, upload_date, "Transkripte vom Kanal deaktiviert"
            except VideoUnavailable:
                return None, upload_date, "Video nicht verfügbar (privat oder gelöscht)"
            except Exception as e:
                err = str(e)
                if "Too Many Requests" in err or "rate limit" in err.lower():
                    if attempt < MAX_RETRIES - 1:
                        continue
                    return None, upload_date, "Rate Limit erreicht — IP temporär gesperrt"
                if "No transcripts were found" in err:
                    return None, upload_date, "Kein Transkript in dieser Sprache verfügbar"
                self.logger.error(f"Error fetching transcript for {video_id}: {err}")
                return None, upload_date, f"Fehler: {err[:120]}"

        return None, upload_date, "Max. Versuche erreicht"

    def _format_transcript(self, transcript_data: List[Dict]) -> str:
        formatted_lines = []
        for entry in transcript_data:
            if hasattr(entry, 'start') and hasattr(entry, 'text'):
                timestamp = format_timestamp(entry.start)
                text = entry.text.strip()
            elif isinstance(entry, dict):
                timestamp = format_timestamp(entry['start'])
                text = entry['text'].strip()
            else:
                text = str(entry).strip()
                timestamp = ""
            formatted_lines.append(f"{timestamp} {text}" if timestamp else text)
        return '\n'.join(formatted_lines)

    def process_batch(self, urls: List[str], output_dir: Union[str, Path]) -> Dict[str, str]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {}
        for url in tqdm(urls, desc="Downloading transcripts"):
            video_id = extract_video_id(url)
            if not video_id:
                results[url] = ERROR_MESSAGES['invalid_url']
                continue
            existing = list(output_dir.glob(f"*{video_id}.txt"))
            if existing:
                results[url] = f"Skipped - already exists: {existing[0].name}"
                continue
            transcript, upload_date, _ = self.get_transcript(url)
            if transcript:
                try:
                    filename = f"{upload_date}_{video_id}.txt" if upload_date else f"transcript_{video_id}.txt"
                    (output_dir / filename).write_text(transcript, encoding='utf-8')
                    results[url] = f"Success - Saved to {filename}"
                except Exception as e:
                    results[url] = f"Error saving file: {str(e)}"
            else:
                results[url] = ERROR_MESSAGES['no_transcript']
            time.sleep(2)
        return results

    def save_to_excel(self, results: Dict[str, str], output_file: Union[str, Path]):
        pd.DataFrame(list(results.items()), columns=['URL', 'Status']).to_excel(output_file, index=False)
        self.logger.info(f"Results saved to {output_file}")
