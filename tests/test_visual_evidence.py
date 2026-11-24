"""Tests for local visual evidence and visual-assisted selection."""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner
from PIL import Image

from src.cli import cli
from src.diff_parser import parse_diff
from src.embedder import MockEmbedder
from src.planner import TestPlanner as Planner
from src.visual_evidence import Evidence, load_frames, resolve_attachments, score_visual_matches


class ColorEmbedder:
    """Simple deterministic image encoder for testing plumbing, not relevance."""

    def embed_image(self, image):
        vector = np.asarray(image.resize((1, 1)), dtype=np.float64).reshape(3)
        return vector / np.linalg.norm(vector)


def save_image(path, color):
    Image.new("RGB", (32, 32), color).save(path)


def test_visual_similarity_can_select_test_independently(tmp_path):
    save_image(tmp_path / "defect.png", "red")
    save_image(tmp_path / "same.png", "red")
    save_image(tmp_path / "different.png", "blue")
    catalog = [
        {"id": "red", "title": "Heating", "domain": "climate", "steps": ["check"], "attachments": ["same.png"]},
        {"id": "blue", "title": "Radio", "domain": "media", "steps": ["check"], "attachments": ["different.png"]},
    ]
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    matches = score_visual_matches(
        [Evidence(tmp_path / "defect.png", "defect")], catalog, tmp_path, ColorEmbedder()
    )
    assert matches["red"].score == pytest.approx(1.0)
    assert matches["blue"].score == pytest.approx(0.0)
    planner = Planner(MockEmbedder())
    planner.load_test_catalog(str(path))
    planner.HIGH_RISK_THRESHOLD = 1.0
    planner.MEDIUM_RISK_THRESHOLD = 1.0
    result = planner.plan(parse_diff(""), visual_matches=matches, visual_threshold=0.9)
    assert [test.test_id for test in result.ranked_tests] == ["red"]
    assert result.ranked_tests[0].visual_query == "defect"
    assert result.ranked_tests[0].visual_reference == "red: same.png"
    assert result.ranked_tests[0].similarity_score == 0.0
    assert not result.gap_tickets


def test_invalid_or_remote_attachments_fail(tmp_path):
    with pytest.raises(ValueError, match="local path"):
        resolve_attachments(["https://example.com/image.png"], tmp_path, "defect")
    with pytest.raises(FileNotFoundError, match="Media file not found"):
        load_frames(Evidence(tmp_path / "missing.png", "missing"))
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    with pytest.raises(ValueError, match="Unsupported"):
        load_frames(Evidence(audio, "audio.wav"))


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg required")
def test_video_samples_frames(tmp_path):
    image = tmp_path / "frame.png"
    video = tmp_path / "recording.mp4"
    save_image(image, "red")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-loop", "1", "-i", str(image), "-t", "1",
         "-pix_fmt", "yuv420p", str(video)],
        check=True, capture_output=True,
    )
    frames = load_frames(Evidence(video, "recording.mp4"))
    assert len(frames) == 5
    assert frames[0][0] == "recording.mp4 @ 0.10s"
    assert frames[-1][0] == "recording.mp4 @ 0.90s"


def test_cli_defect_attachment_matches_catalog(tmp_path, monkeypatch):
    save_image(tmp_path / "incident.png", "red")
    save_image(tmp_path / "expected.png", "red")
    catalog = [{"id": "T-1", "title": "Climate", "domain": "climate", "steps": ["check"],
                "attachments": ["expected.png"]}]
    (tmp_path / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    (tmp_path / "defect.json").write_text(json.dumps(
        {"summary": "screen", "description": "error", "attachments": ["incident.png"]}
    ), encoding="utf-8")
    monkeypatch.setattr("src.cli.SiglipImageEmbedder", ColorEmbedder)
    report = tmp_path / "report.json"
    result = CliRunner().invoke(cli, [
        "analyze", "--defect", str(tmp_path / "defect.json"), "--catalog", str(tmp_path / "catalog.json"),
        "--mock-embeddings", "--high-threshold", "1", "--medium-threshold", "1",
        "--output", str(report),
    ])
    assert result.exit_code == 0, result.output
    ranked = json.loads(report.read_text())["test_selection"]["ranked_tests"]
    assert ranked[0]["test_id"] == "T-1"
    assert ranked[0]["visual_similarity_score"] == pytest.approx(1)
    assert "incident.png" in ranked[0]["visual_query"]


def test_cli_detects_changed_git_image(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)

    git("init")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    (repo / "code.txt").write_text("before")
    git("add", "code.txt")
    git("commit", "-m", "base")
    save_image(repo / "screen.png", "red")
    git("add", "screen.png")
    git("commit", "-m", "add screenshot")
    save_image(tmp_path / "expected.png", "red")
    (tmp_path / "catalog.json").write_text(json.dumps([
        {"id": "T-1", "title": "Screen", "domain": "display", "steps": ["check"],
         "attachments": ["expected.png"]}
    ]), encoding="utf-8")
    monkeypatch.setattr("src.cli.SiglipImageEmbedder", ColorEmbedder)
    report = tmp_path / "report.json"
    result = CliRunner().invoke(cli, [
        "analyze", "--git-base", "HEAD~1", "--git-repo", str(repo),
        "--catalog", str(tmp_path / "catalog.json"), "--mock-embeddings",
        "--output", str(report),
    ])
    assert result.exit_code == 0, result.output
    ranked = json.loads(report.read_text())["test_selection"]["ranked_tests"]
    assert ranked[0]["visual_similarity_score"] == pytest.approx(1)
    assert ranked[0]["visual_query"] == "git HEAD:screen.png"
