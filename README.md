# YouTube Transcript Downloader

FastAPI Web App zum Batch-Download von Transkripten ganzer YouTube-Kanäle. Läuft lokal auf Port 8765.

## Features

- Kanal-URL eingeben → alle Videos scannen → bestätigen → Transkripte herunterladen
- Live-Fortschrittsbalken via Server-Sent Events
- Pause / Fortsetzen / Abbrechen
- Skip-existing: beim erneuten Start werden bereits vorhandene Dateien übersprungen
- Sprach-Fallback: manuell → auto/ASR → Englisch → beliebige verfügbare Sprache
- Spezifische Fehlermeldungen pro Video (Rate Limit, deaktiviert, privat, ...)
- Ausgabe: `output/KanalName/YYYYMMDD_videoID.txt`

## Setup

```bash
git clone https://github.com/BechtC/yt-transcript-downloader.git
cd yt-transcript-downloader

cp .env.example .env
# YOUTUBE_API_KEY in .env eintragen

# Windows:
start.bat
```

Dann im Browser: http://localhost:8765

## YouTube Data API Key

Benötigt für Upload-Datum im Dateinamen (`YYYYMMDD_videoID.txt`).

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) öffnen
2. **YouTube Data API v3** aktivieren
3. API-Schlüssel erstellen → in `.env` eintragen: `YOUTUBE_API_KEY=dein_key`

## Tests

```bash
pytest tests/
```

## Stack

- **Backend:** FastAPI + uvicorn
- **Frontend:** Tailwind CSS (CDN), vanilla JS, Server-Sent Events
- **YouTube:** yt-dlp (Kanal-Scan) + youtube_transcript_api (Transkripte)
