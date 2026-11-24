"""FastAPI backend for the static dashboard."""

import os
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.diff_parser import parse_diff
from src.embedder import create_embedder
from src.planner import TestPlanner

app = FastAPI(title="E5 Diff-to-Test Planner API")
origins = os.environ.get(
    "E5_ALLOWED_ORIGINS",
    "https://ankita-sathya.github.io,http://localhost:3000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins if origin.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_planner: TestPlanner | None = None
_initialization_lock = Lock()


def _get_planner() -> TestPlanner:
    """Load catalog embeddings once per process."""
    global _planner
    with _initialization_lock:
        if _planner is None:
            planner = TestPlanner(create_embedder(mock=os.getenv("E5_MOCK_EMBEDDINGS") == "1"))
            catalog_path = Path(__file__).resolve().parent.parent / "data" / "sample_test_catalog.json"
            planner.load_test_catalog(str(catalog_path))
            _planner = planner
        return _planner


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze_diff(request: dict) -> dict:
    diff_content = request.get("diff_content", "")
    if not isinstance(diff_content, str) or not diff_content.strip():
        raise HTTPException(status_code=400, detail="diff_content is required")
    defect = request.get("defect_description")
    if defect is not None and not isinstance(defect, str):
        raise HTTPException(status_code=400, detail="defect_description must be text")
    thresholds = []
    for key, default in (("high_threshold", 0.78), ("medium_threshold", 0.65), ("gap_threshold", 0.62)):
        value = request.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise HTTPException(status_code=400, detail=f"{key} must be a number between 0 and 1")
        thresholds.append(float(value))
    high, medium, gap = thresholds
    if medium > high:
        raise HTTPException(status_code=400, detail="medium_threshold cannot exceed high_threshold")

    shared = _get_planner()
    planner = TestPlanner(shared.embedder)
    planner.test_catalog = shared.test_catalog
    planner.embeddings_cache = shared.embeddings_cache
    planner.HIGH_RISK_THRESHOLD = high
    planner.MEDIUM_RISK_THRESHOLD = medium
    planner.GAP_DETECTION_THRESHOLD = gap
    return planner.plan(parse_diff(diff_content), defect_description=defect).to_dict()


@app.get("/api/sample-diff")
def get_sample_diff() -> dict[str, str]:
    sample_path = Path(__file__).resolve().parent.parent / "data" / "sample_pr_diff.patch"
    return {"content": sample_path.read_text(encoding="utf-8")}


@app.get("/api/sample-catalog")
def get_sample_catalog() -> list[dict]:
    import json

    catalog_path = Path(__file__).resolve().parent.parent / "data" / "sample_test_catalog.json"
    return json.loads(catalog_path.read_text(encoding="utf-8"))
