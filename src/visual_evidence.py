"""Local image and video evidence matching using SigLIP image embeddings."""

import io
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np
from PIL import Image, ImageOps

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES
MAX_MEDIA_BYTES = 100 * 1024 * 1024
MAX_VIDEO_SECONDS = 600
VIDEO_FRAME_COUNT = 5


@dataclass(frozen=True)
class Evidence:
    """Local media path and a human-readable source label."""

    path: Path
    label: str


@dataclass(frozen=True)
class VisualMatch:
    score: float
    query: str
    reference: str


class ImageEmbedder(Protocol):
    def embed_image(self, image: Image.Image) -> np.ndarray: ...


class SiglipImageEmbedder:
    """Apache-2.0 SigLIP image encoder; model inference is local."""

    MODEL_NAME = "google/siglip-base-patch16-224"

    def __init__(self) -> None:
        from transformers import AutoImageProcessor, SiglipModel

        self.processor = AutoImageProcessor.from_pretrained(self.MODEL_NAME)
        self.model = SiglipModel.from_pretrained(self.MODEL_NAME)
        self.model.eval()

    def embed_image(self, image: Image.Image) -> np.ndarray:
        import torch

        inputs = self.processor(images=image, return_tensors="pt")
        with torch.inference_mode():
            features = self.model.vision_model(pixel_values=inputs["pixel_values"]).pooler_output
        vector = features[0].detach().cpu().numpy()
        norm = np.linalg.norm(vector)
        if not np.isfinite(norm) or norm == 0:
            raise ValueError("Vision model returned an invalid image embedding")
        return vector / norm


def resolve_attachments(value: object, base_dir: Path, source: str) -> list[Evidence]:
    """Resolve attachment paths relative to their owning JSON file."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{source} attachments must be a list of local paths")
    evidence = []
    for item in value:
        if not isinstance(item, str) or not item or "://" in item:
            raise ValueError(f"{source} attachment must be a local path string: {item!r}")
        path = (base_dir / item).resolve()
        evidence.append(Evidence(path, f"{source}: {item}"))
    return evidence


def _run(command: list[str], description: str) -> bytes:
    try:
        return subprocess.run(command, capture_output=True, check=True, timeout=60).stdout
    except FileNotFoundError as exc:
        raise RuntimeError(f"{description} requires ffmpeg and ffprobe on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{description} timed out") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"{description} failed: {detail}") from exc


def load_frames(evidence: Evidence) -> list[tuple[str, Image.Image]]:
    """Load an image or sample up to five evenly spaced video frames."""
    path = evidence.path
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {evidence.label} ({path})")
    if path.stat().st_size > MAX_MEDIA_BYTES:
        raise ValueError(f"Media exceeds 100 MiB limit: {evidence.label}")
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        with Image.open(path) as image:
            return [(evidence.label, ImageOps.exif_transpose(image).convert("RGB"))]
    if suffix not in VIDEO_SUFFIXES:
        raise ValueError(f"Unsupported visual media type: {evidence.label}")

    probe = _run(
        ["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
         "-show_entries", "format=duration",
         "-of", "json", str(path)],
        f"Reading video {evidence.label}",
    )
    try:
        duration = float(json.loads(probe)["format"]["duration"])
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Video has no usable duration: {evidence.label}") from exc
    if not np.isfinite(duration) or duration <= 0 or duration > MAX_VIDEO_SECONDS:
        raise ValueError(f"Video duration must be between 0 and {MAX_VIDEO_SECONDS} seconds: {evidence.label}")

    frames = []
    for index in range(VIDEO_FRAME_COUNT):
        timestamp = duration * (index + 0.5) / VIDEO_FRAME_COUNT
        frame = _run(
            ["ffmpeg", "-v", "error", "-protocol_whitelist", "file,pipe",
             "-ss", str(timestamp), "-i", str(path),
             "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
            f"Extracting video frame {evidence.label}",
        )
        if not frame:
            raise ValueError(f"No frame at {timestamp:.2f}s in {evidence.label}")
        with Image.open(io.BytesIO(frame)) as image:
            frames.append((f"{evidence.label} @ {timestamp:.2f}s", image.convert("RGB")))
    return frames


def score_visual_matches(
    query_media: Sequence[Evidence],
    catalog: list[dict],
    catalog_dir: Path,
    embedder: ImageEmbedder,
) -> dict[str, VisualMatch]:
    """Compare query frames with each test's attached frames; keep the best pair."""
    cache: dict[Path, list[tuple[str, np.ndarray]]] = {}

    def encode(evidence: Evidence) -> list[tuple[str, np.ndarray]]:
        if evidence.path not in cache:
            cache[evidence.path] = [
                (label.removeprefix(evidence.label), embedder.embed_image(image))
                for label, image in load_frames(evidence)
            ]
        return [(evidence.label + suffix, vector) for suffix, vector in cache[evidence.path]]

    queries = [frame for item in query_media for frame in encode(item)]
    matches = {}
    for test in catalog:
        references = resolve_attachments(test.get("attachments"), catalog_dir, test["id"])
        best: VisualMatch | None = None
        for item in references:
            for ref_label, ref_vector in encode(item):
                for query_label, query_vector in queries:
                    score = float(np.clip(np.dot(query_vector, ref_vector), 0.0, 1.0))
                    if best is None or score > best.score:
                        best = VisualMatch(score, query_label, ref_label)
        if best is not None:
            matches[test["id"]] = best
    return matches


def extract_git_evidence(repo: Path, base: str, head: str, directory: Path) -> list[Evidence]:
    """Extract changed media from the head revision, never from the working tree."""
    names = _run(
        ["git", "-C", str(repo), "diff", "--no-ext-diff", "--no-textconv",
         "--name-only", "-z", "--diff-filter=AMR",
         f"{base}..{head}", "--"],
        "Reading changed Git media paths",
    )
    evidence = []
    for raw_path in names.split(b"\0"):
        if not raw_path:
            continue
        path = raw_path.decode("utf-8")
        suffix = Path(path).suffix.lower()
        if suffix not in MEDIA_SUFFIXES:
            continue
        obj = f"{head}:{path}"
        size = int(_run(["git", "-C", str(repo), "cat-file", "-s", obj], f"Reading Git blob size {path}"))
        if size > MAX_MEDIA_BYTES:
            raise ValueError(f"Git media exceeds 100 MiB limit: {path}")
        content = _run(["git", "-C", str(repo), "cat-file", "blob", obj], f"Reading Git blob {path}")
        if content.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
            raise ValueError(f"Git LFS pointer is not media; supply the downloaded file with --media: {path}")
        target = directory / f"{len(evidence)}{suffix}"
        target.write_bytes(content)
        evidence.append(Evidence(target, f"git {head}:{path}"))
    return evidence
