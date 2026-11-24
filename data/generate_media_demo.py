"""Generate synthetic screenshots and a short local video for the media demo."""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    directory = Path(__file__).resolve().parent / "sample_media"
    directory.mkdir(exist_ok=True)
    paths = [directory / name for name in ("climate.png", "media.png", "incident.png", "incident.mp4")]
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing demo media: {', '.join(existing)}")

    def climate(path: Path, incident: bool) -> None:
        image = Image.new("RGB", (640, 360), "#121f32")
        draw = ImageDraw.Draw(image)
        draw.rectangle((30, 30, 610, 330), outline="#8cbfe0", width=4)
        draw.text((65, 60), "CLIMATE CONTROL", fill="white")
        draw.text((65, 115), "DRIVER", fill="#b9d8ec")
        draw.text((350, 115), "PASSENGER", fill="#b9d8ec")
        draw.text((65, 165), "21 C", fill="white", stroke_width=1)
        draw.text((350, 165), "ERROR" if incident else "23 C", fill="#ff7777" if incident else "white")
        draw.rectangle((65, 240, 570, 275), fill="#284c6e")
        draw.text((80, 250), "ZONE TEMPERATURE", fill="white")
        image.save(path)

    climate(paths[0], False)
    climate(paths[2], True)
    image = Image.new("RGB", (640, 360), "#24162e")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 610, 330), outline="#d0a6de", width=4)
    draw.text((65, 60), "MEDIA PLAYER", fill="white")
    draw.rectangle((65, 110, 220, 260), fill="#7c4c89")
    draw.text((260, 145), "RADIO", fill="white")
    draw.text((260, 200), "FM 101.5", fill="white")
    image.save(paths[1])
    subprocess.run(
        ["ffmpeg", "-v", "error", "-n", "-loop", "1", "-i", str(paths[2]),
         "-t", "2", "-pix_fmt", "yuv420p", str(paths[3])],
        check=True,
    )
    print(f"Generated synthetic demo media in {directory}")


if __name__ == "__main__":
    main()
