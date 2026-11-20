"""Pack a judge batch folder (``batch.json`` + the pictures it names) into the sha256-NAMED tar the container fetches.

    python -m explainer_engine.training.pods.judge.pack_batch <batch folder> <out dir>

Checks ``judge_core.batch_problems`` first (3-5 creator-chosen style examples, anchors, files present). Prints the tar path and its sha256;
upload it to HF ``code/judge/batch-<sha>.tar.gz`` (free) before the L3 rung. The tar is reproducible (sorted members, zeroed times)."""
from __future__ import annotations

import hashlib
import json
import sys
import tarfile
from pathlib import Path

from explainer_engine.training.pods.judge import judge_core as J


def pack(folder: Path, out_dir: Path) -> tuple[Path, str]:
    folder, out_dir = Path(folder), Path(out_dir)
    batch = json.loads((folder / "batch.json").read_text(encoding="utf-8"))
    bad = J.batch_problems(batch, folder)
    if bad:
        raise SystemExit("batch refused:\n" + "\n".join(bad))
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "batch.tmp.tar.gz"
    import gzip
    with gzip.GzipFile(tmp, "wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tf:
        for p in sorted(x for x in folder.rglob("*") if x.is_file()):
            ti = tf.gettarinfo(str(p), str(p.relative_to(folder)))
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname = 0, 0, 0, "", ""
            with open(p, "rb") as f:
                tf.addfile(ti, f)
    sha = hashlib.sha256(tmp.read_bytes()).hexdigest()
    final = out_dir / f"batch-{sha}.tar.gz"
    tmp.replace(final)
    return final, sha


if __name__ == "__main__":
    path, sha = pack(Path(sys.argv[1]), Path(sys.argv[2]))
    print(path, sha)
