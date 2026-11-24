"""Tests for Git change input, embedding model choice and sample scenarios."""

import json
import subprocess
from pathlib import Path

import numpy as np
from click.testing import CliRunner

from src.cli import cli
from src.diff_parser import parse_diff
from src.planner import TestPlanner as Planner


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "sample_test_catalog.json"


def test_changed_code_reaches_embedding_query():
    class RecordingEmbedder:
        def embed_passage(self, text):
            return np.array([1.0])

        def embed_query(self, text):
            self.query = text
            return np.array([1.0])

    embedder = RecordingEmbedder()
    planner = Planner(embedder)
    planner.load_test_catalog(str(CATALOG))
    diff = parse_diff(
        "diff --git a/app/player.kt b/app/player.kt\n"
        "--- a/app/player.kt\n+++ b/app/player.kt\n"
        "@@ -1 +1 @@\n-oldVolume = 10\n+newVolume = 20\n"
    )
    planner.plan(diff)
    assert "-oldVolume = 10" in embedder.query
    assert "+newVolume = 20" in embedder.query


def test_low_maximum_similarity_creates_one_gap():
    class LowSimilarityEmbedder:
        def embed_passage(self, text):
            return np.array([1.0, 0.0])

        def embed_query(self, text):
            return np.array([0.3, np.sqrt(1 - 0.3**2)])

    planner = Planner(LowSimilarityEmbedder())
    planner.load_test_catalog(str(CATALOG))
    result = planner.plan(parse_diff(
        "diff --git a/new/file.kt b/new/file.kt\n"
        "--- a/new/file.kt\n+++ b/new/file.kt\n@@ -1 +1 @@\n-old\n+new\n"
    ))
    assert not result.ranked_tests
    assert len(result.gap_tickets) == 1
    assert result.gap_tickets[0].similarity_max == 0.3
    assert "not evidence" in result.execution_summary


def test_gap_threshold_is_strict():
    class BoundaryEmbedder:
        def embed_passage(self, text):
            return np.array([1.0, 0.0])

        def embed_query(self, text):
            return np.array([0.62, np.sqrt(1 - 0.62**2)])

    planner = Planner(BoundaryEmbedder())
    planner.load_test_catalog(str(CATALOG))
    result = planner.plan(parse_diff(
        "diff --git a/new/file.kt b/new/file.kt\n"
        "--- a/new/file.kt\n+++ b/new/file.kt\n@@ -1 +1 @@\n-old\n+new\n"
    ))
    assert not result.gap_tickets


def test_cli_analyzes_local_git_revisions(tmp_path):
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True, capture_output=True, text=True,
        )

    git("init")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    source = tmp_path / "media.kt"
    source.write_text("volume = 10\n", encoding="utf-8")
    git("add", "media.kt")
    git("commit", "-m", "base")
    source.write_text("volume = 20\n", encoding="utf-8")
    git("commit", "-am", "change")
    report = tmp_path / "report.json"
    result = CliRunner().invoke(cli, [
        "analyze", "--git-repo", str(tmp_path), "--git-base", "HEAD~1",
        "--catalog", str(CATALOG), "--mock-embeddings", "--output", str(report),
    ])
    assert result.exit_code == 0, result.output
    assert "Files changed: 1" in result.output
    assert "test_selection" in json.loads(report.read_text(encoding="utf-8"))


def test_cli_rejects_missing_or_invalid_git_input(tmp_path):
    runner = CliRunner()
    base_args = ["analyze", "--catalog", str(CATALOG), "--mock-embeddings"]
    missing = runner.invoke(cli, base_args)
    assert missing.exit_code != 0
    assert "Provide a --diff" in missing.output
    invalid = runner.invoke(cli, base_args + ["--git-repo", str(tmp_path), "--git-base", "missing"])
    assert invalid.exit_code != 0
    assert "Git diff failed" in invalid.output


def test_cli_applies_and_validates_thresholds(tmp_path):
    args = [
        "analyze", "--diff", str(ROOT / "data" / "media_audio_focus.patch"),
        "--catalog", str(CATALOG), "--mock-embeddings", "--high-threshold", "0.2",
        "--medium-threshold", "0.1", "--gap-threshold", "0.05",
        "--output", str(tmp_path / "report.json"),
    ]
    runner = CliRunner()
    result = runner.invoke(cli, args)
    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert data["test_selection"]["test_count"] > 0
    assert "HIGH RISK (≥0.2)" in result.output
    invalid = runner.invoke(cli, args + ["--medium-threshold", "0.3"])
    assert invalid.exit_code != 0
    assert "cannot exceed" in invalid.output


def test_scenario_catalog_has_runnable_cross_app_cases():
    cases = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert len({case["id"] for case in cases}) == len(cases)
    added = [case for case in cases if case["id"] in {f"XRAY-{n}" for n in range(1036, 1048)}]
    assert len(added) == 12
    assert {case["domain"] for case in added} >= {
        "Climate_Control", "Parking_Assistance", "Phone_Connectivity",
        "Media_Playback", "Navigation", "Charging", "Vehicle_Settings", "Display_Settings",
    }
    assert all(len(case["steps"]) >= 3 and case["expected_result"] for case in added)
