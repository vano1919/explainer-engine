"""Speed as a finishing step (ED-06): the finished video is time-compressed (picture and sound together, pitch kept), the
voice is never re-synthesised. ``excerpts`` makes short samples of 1.05 / 1.10 / 1.15 of the same places for the creator to
compare; ``retime`` makes the full file at the chosen rate. ffmpeg only, no cost."""
from __future__ import annotations

import subprocess
from pathlib import Path

RATES = (1.05, 1.10, 1.15)


def _filter(rate: float) -> str:
    return f"[0:v]setpts=PTS/{rate},fps=30[v];[0:a]atempo={rate}[a]"


def retime(src: Path, dst: Path, rate: float, *, start: float | None = None, length: float | None = None,
           crf: int = 18, scale: str | None = None) -> Path:
    if not 1.0 < rate <= 1.5:
        raise ValueError("rate must be above 1.0 and at most 1.5 (atempo stays clean in that range)")
    cut = (["-ss", f"{start}"] if start is not None else []) + (["-t", f"{length}"] if length is not None else [])
    graph = _filter(rate) if not scale else f"[0:v]scale={scale},setpts=PTS/{rate},fps=30[v];[0:a]atempo={rate}[a]"
    part = dst.with_suffix(".part.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *cut, "-i", str(src), "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", str(part)], check=True)
    part.replace(dst)
    return dst


def excerpts(src: Path, out_dir: Path, places: list[tuple[float, float]], rates=RATES, scale: str = "1280:720") -> list[Path]:
    """One 720p sample per place and rate; ``places`` are (start s, length s) on the original clock."""
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for k, (a, n) in enumerate(places, 1):
        for r in rates:
            made.append(retime(src, out_dir / f"p{k}_x{r:.2f}.mp4", r, start=a, length=n, crf=23, scale=scale))
    return made


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("video")
    p.add_argument("--out", required=True, help="a folder for --places, the output file for --final")
    p.add_argument("--places", help="start:length pairs in seconds, e.g. 240:45,780:45")
    p.add_argument("--final", type=float, help="make the full file at this rate")
    a = p.parse_args(argv)
    if a.final:
        print(retime(Path(a.video), Path(a.out), a.final))
    else:
        pairs = [tuple(float(x) for x in t.split(":")) for t in a.places.split(",")]
        for f in excerpts(Path(a.video), Path(a.out), pairs):
            print(f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
