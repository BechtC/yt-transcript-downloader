"""YouTube Transcript Downloader — FastAPI Web App
Runs on http://localhost:8765
"""
import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from channel_extractor import ChannelExtractor
from transcript_handler import TranscriptHandler
from utils import extract_video_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="YouTube Transcript Downloader")

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

jobs: Dict[str, Dict[str, Any]] = {}


class ConfirmRequest(BaseModel):
    language: str = "de"


@app.get("/", response_class=HTMLResponse)
async def index():
    template = Path("templates/index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=template)


@app.get("/api/channels/scan")
async def scan_channel(url: str = Query(...)):
    try:
        extractor = ChannelExtractor(url)
        channel_name, video_urls = extractor.get_video_urls()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not video_urls:
        raise HTTPException(status_code=404, detail="Keine Videos gefunden. Bitte URL prüfen.")
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "state": "SCANNED", "channel_name": channel_name, "video_urls": video_urls,
        "video_count": len(video_urls), "current": 0, "success_count": 0,
        "failed_videos": [], "last_file": None, "error": None,
    }
    return {"job_id": job_id, "channel_name": channel_name, "video_count": len(video_urls)}


@app.post("/api/jobs/{job_id}/confirm")
async def confirm_job(job_id: str, body: ConfirmRequest):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    if job["state"] != "SCANNED":
        raise HTTPException(status_code=400, detail=f"Job ist im Zustand '{job['state']}'")
    job["state"] = "DOWNLOADING"
    job["language"] = body.language
    job["paused"] = False
    job["cancelled"] = False
    asyncio.create_task(_download_transcripts(job_id))
    return {"status": "started"}


@app.post("/api/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    if job["state"] == "DOWNLOADING":
        job["paused"] = True
        job["state"] = "PAUSED"
    return {"state": job["state"]}


@app.post("/api/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    if job["state"] == "PAUSED":
        job["paused"] = False
        job["state"] = "DOWNLOADING"
    return {"state": job["state"]}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    job["cancelled"] = True
    job["state"] = "CANCELLED"
    return {"state": job["state"]}


@app.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    async def event_generator():
        while True:
            job = jobs.get(job_id, {})
            data = {
                "state": job.get("state"), "current": job.get("current", 0),
                "total": job.get("video_count", 0), "success_count": job.get("success_count", 0),
                "failed_videos": job.get("failed_videos", []), "last_file": job.get("last_file"),
                "error": job.get("error"),
            }
            yield f"data: {json.dumps(data)}\n\n"
            if job.get("state") in ("DONE", "ERROR"):
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/status")
async def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return {k: v for k, v in job.items() if k != "video_urls"}


@app.get("/api/channels")
async def list_channels():
    channels = []
    if OUTPUT_DIR.exists():
        for folder in sorted(OUTPUT_DIR.iterdir()):
            if folder.is_dir():
                count = len(list(folder.glob("*.txt")))
                channels.append({"name": folder.name, "transcript_count": count})
    return {"channels": channels}


async def _download_transcripts(job_id: str):
    job = jobs[job_id]
    video_urls = job["video_urls"]
    channel_name = job["channel_name"]
    language = job.get("language", "de")
    output_dir = OUTPUT_DIR / channel_name
    output_dir.mkdir(parents=True, exist_ok=True)
    handler = TranscriptHandler(language=language)
    for i, url in enumerate(video_urls):
        if job.get("cancelled"):
            break
        while job.get("paused"):
            await asyncio.sleep(0.5)
        try:
            video_id = extract_video_id(url)
            existing = list(output_dir.glob(f"*{video_id}.txt"))
            if existing:
                job["current"] = i + 1
                job["success_count"] += 1
                continue
            transcript, upload_date, error_reason = handler.get_transcript(url)
            if transcript:
                filename = f"{upload_date}_{video_id}.txt" if upload_date else f"transcript_{video_id}.txt"
                (output_dir / filename).write_text(transcript, encoding="utf-8")
                job["success_count"] += 1
                job["last_file"] = filename
            else:
                job["failed_videos"].append({"id": video_id, "reason": error_reason or "Kein Transkript verfügbar"})
        except Exception as e:
            video_id = extract_video_id(url) if url else "unbekannt"
            job["failed_videos"].append({"id": video_id, "reason": str(e)[:120]})
        job["current"] = i + 1
        await asyncio.sleep(2)
    job["state"] = "CANCELLED" if job.get("cancelled") else "DONE"
    logger.info(f"Job {job_id} done: {job['success_count']} OK, {len(job['failed_videos'])} failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8765, reload=False)
