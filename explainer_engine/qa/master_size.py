"""Is the master video the size the episode declared? (OR-E02; default = the delivery frame, BP-167)

The adapter reads the master's pixel size with ffprobe (a rotation flag of 90/270 swaps width and height, as in
``short_format.probe``) and compares it with the episode's declared size. No declared size = the delivery default
(``core/delivery.size()``, BP-167 via the registry; BP-167 says a job that names its own size keeps it). A mismatch is a FAIL;
a file that cannot be probed, or has no video stream, is NOT_RUN, never a pass.

    python -m explainer_engine.qa.master_size <master.mp4> [WIDTHxHEIGHT]     # exit 1 on FAIL, 2 on NOT_RUN
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from explainer_engine.core import delivery
from explainer_engine.qa.short_format import probe


def _declared(declared: tuple[int, int] | list[int] | str | None) -> tuple[int, int]:
    if declared is None:
        return delivery.size()
    if isinstance(declared, str):
        try:
            w, h = (int(x) for x in declared.lower().split("x"))
        except ValueError as exc:
            raise ValueError(f"declared size must look like 2560x1440, got {declared!r}") from exc
        return w, h
    if len(declared) != 2 or not all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in declared):
        raise ValueError(f"declared size must be two positive integers, got {declared!r}")
    return int(declared[0]), int(declared[1])


def check_master_size(path: str | Path, declared: tuple[int, int] | list[int] | str | None = None) -> dict:
    """{status, value, detail}; value is 'WxH' as probed (None when not run)."""
    want_w, want_h = _declared(declared)
    p = Path(path)
    if not p.is_file():
        return {"status": "NOT_RUN", "value": None, "detail": f"not run: {p} does not exist"}
    try:
        info = probe(p)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        return {"status": "NOT_RUN", "value": None, "detail": f"not run: ffprobe could not read {p}: {exc.__class__.__name__}"}
    w, h = info["width"], info["height"]
    if not (w and h):
        return {"status": "NOT_RUN", "value": None, "detail": f"not run: {p} has no video stream"}
    if (w, h) != (want_w, want_h):
        return {"status": "FAIL", "value": f"{w}x{h}", "detail": f"master is {w}x{h}, the episode declares {want_w}x{want_h}"}
    return {"status": "PASS", "value": f"{w}x{h}", "detail": f"master is {w}x{h} as declared"}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or len(argv) > 2:
        print(__doc__)
        return 2
    res = check_master_size(argv[0], argv[1] if len(argv) == 2 else None)
    print(f"{res['status']}: {res['detail']}")
    return {"PASS": 0, "FAIL": 1}.get(res["status"], 2)


if __name__ == "__main__":
    sys.exit(main())
