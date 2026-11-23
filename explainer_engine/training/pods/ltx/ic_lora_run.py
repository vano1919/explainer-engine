"""Runs ``python -m <module> <args>`` in THIS process and, whatever happens, writes what only this process can know when it ends:
torch's peak GPU memory (``torch.cuda.max_memory_allocated``) and this process' peak host memory.

    python ic_lora_run.py <module> <facts.json> <the module's own arguments ...>

Why a wrapper: the Layout-To-Render worker runs the LTX-2 CLI as a child process (``subprocess.run(timeout=)``, so the clean deadline
holds), and a parent cannot read the child's torch counters. The brief (item 7) wants ``torch.cuda.max_memory_allocated()`` and the
offload mode measured on the A100; this is where. Stdlib only at import; torch is looked at only if the module already loaded it."""
from __future__ import annotations

import json
import os
import resource
import runpy
import sys
import time

GIB = 2 ** 30


def facts(t0: float, status: str, error: str | None = None) -> dict:
    out = {"status": status, "error": error, "wall_s": round(time.time() - t0, 1),
           "host_rss_peak_gib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 2), 2)}   # Linux: KiB
    torch = sys.modules.get("torch")
    try:
        if torch is not None and torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            out.update(max_allocated_gib=round(torch.cuda.max_memory_allocated() / GIB, 2),
                       max_reserved_gib=round(torch.cuda.max_memory_reserved() / GIB, 2), total_gib=round(p.total_memory / GIB, 2),
                       device=torch.cuda.get_device_name(0))
    except Exception as exc:  # noqa: BLE001 - facts only, never a reason to hide the run's own result
        out["torch_error"] = f"{type(exc).__name__}: {str(exc)[:100]}"
    return out


def write(path: str, data: dict) -> None:
    tmp = os.path.join(os.path.dirname(path) or ".", "." + os.path.basename(path))   # keep the suffix, then rename: never half a file
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def main(argv: list[str]) -> int:
    module, out = argv[0], argv[1]
    sys.argv = [module, *argv[2:]]
    t0, status, error = time.time(), "ok", None
    try:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    except SystemExit as exc:                     # argparse errors and the module's own exits keep their code
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        status = "ok" if code == 0 else "exit"
        error = None if code == 0 else str(exc.code)[:200]
        write(out, facts(t0, status, error))
        return code
    except BaseException as exc:                  # noqa: BLE001 - OOM and everything else: the facts first, then the traceback
        write(out, facts(t0, "raised", f"{type(exc).__name__}: {str(exc)[:200]}"))
        raise
    write(out, facts(t0, status, error))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
