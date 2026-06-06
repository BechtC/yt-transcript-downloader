"""Configuration for YouTube Transcript Tool"""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from typing import Optional

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)

# API Key wird aus .env geladen — niemals hardcoden
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

def get_default_input_file() -> Optional[Path]:
    csv_files = list(INPUT_DIR.glob("*.csv"))
    return csv_files[0] if csv_files else None

DEFAULT_INPUT_FILE = get_default_input_file()
DEFAULT_OUTPUT_FORMAT = "txt"
DEFAULT_TRANSCRIPT_LANG = "de"
BATCH_SIZE = 10
MAX_RETRIES = 3
TIMESTAMP_FORMAT = "[%H:%M:%S]"
OUTPUT_FILE_TEMPLATE = "transcript_{video_id}.{ext}"
ERROR_MESSAGES = {
    "no_transcript": "Kein Transkript verfügbar",
    "invalid_url": "Ungültige YouTube-URL",
    "network_error": "Netzwerkfehler beim Abrufen des Transkripts",
    "rate_limit": "YouTube-API Ratenlimit erreicht",
    "no_input_file": "Keine CSV-Datei im Eingabeverzeichnis gefunden",
    "api_error": "Fehler bei der YouTube API-Anfrage",
    "date_error": "Fehler beim Abrufen des Upload-Datums",
}
