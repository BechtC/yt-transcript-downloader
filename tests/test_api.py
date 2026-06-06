"""API behavior tests for YouTube Transcript Downloader."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
MOCK_CHANNEL = "test_kanal"
MOCK_URLS = [f"https://www.youtube.com/watch?v=video{i:03d}" for i in range(5)]


def test_scan_returns_job_id_and_video_count():
    with patch("app.ChannelExtractor") as MockExtractor:
        MockExtractor.return_value.get_video_urls.return_value = (MOCK_CHANNEL, MOCK_URLS)
        response = client.get("/api/channels/scan", params={"url": "https://www.youtube.com/@testkanal"})
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["channel_name"] == MOCK_CHANNEL
    assert data["video_count"] == len(MOCK_URLS)


def test_confirm_job_starts_download():
    with patch("app.ChannelExtractor") as MockExtractor:
        MockExtractor.return_value.get_video_urls.return_value = (MOCK_CHANNEL, MOCK_URLS)
        scan = client.get("/api/channels/scan", params={"url": "https://www.youtube.com/@testkanal"})
        job_id = scan.json()["job_id"]
    with patch("app._download_transcripts"):
        response = client.post(f"/api/jobs/{job_id}/confirm", json={"language": "de"})
    assert response.status_code == 200
    assert client.get(f"/api/jobs/{job_id}/status").json()["state"] == "DOWNLOADING"


def test_job_status_returns_progress():
    with patch("app.ChannelExtractor") as MockExtractor:
        MockExtractor.return_value.get_video_urls.return_value = (MOCK_CHANNEL, MOCK_URLS)
        scan = client.get("/api/channels/scan", params={"url": "https://www.youtube.com/@testkanal"})
        job_id = scan.json()["job_id"]
    with patch("app._download_transcripts"):
        client.post(f"/api/jobs/{job_id}/confirm", json={"language": "de"})
    data = client.get(f"/api/jobs/{job_id}/status").json()
    assert "state" in data and "current" in data
    assert data["video_count"] == len(MOCK_URLS)


def test_channel_list_returns_downloaded_channels(tmp_path, monkeypatch):
    monkeypatch.setattr("app.OUTPUT_DIR", tmp_path)
    kanal_dir = tmp_path / "mein_kanal"
    kanal_dir.mkdir()
    (kanal_dir / "20240101_abc123.txt").write_text("transcript")
    (kanal_dir / "20240102_def456.txt").write_text("transcript")
    channels = client.get("/api/channels").json()["channels"]
    assert any(c["name"] == "mein_kanal" and c["transcript_count"] == 2 for c in channels)


@pytest.mark.parametrize("url,expected_name", [
    ("https://www.youtube.com/@SalehM", "SalehM"),
    ("https://www.youtube.com/@SalehM/videos", "SalehM"),
    ("https://www.youtube.com/channel/UCxxxxxx", "UCxxxxxx"),
    ("https://www.youtube.com/c/SalehM", "SalehM"),
])
def test_channel_name_extracted_from_url(url, expected_name):
    from channel_extractor import ChannelExtractor
    assert ChannelExtractor.extract_channel_name(url) == expected_name


def test_scan_invalid_url_returns_400():
    with patch("app.ChannelExtractor") as MockExtractor:
        MockExtractor.return_value.get_video_urls.side_effect = Exception("Ungültige URL")
        response = client.get("/api/channels/scan", params={"url": "keine-echte-url"})
    assert response.status_code == 400
