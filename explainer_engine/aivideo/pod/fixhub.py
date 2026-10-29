"""Night-run hot fix: pod.sh upgraded huggingface_hub to 2.x, which transformers refuses (needs >=1.5,<2). Pin it back."""
import subprocess, sys
import importlib.metadata as md


def ensure():
    v = md.version("huggingface_hub")
    if int(v.split(".")[0]) >= 2:
        for extra in (["--break-system-packages"], []):
            r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub>=1.5,<2", *extra])
            if r.returncode == 0:
                break
        print("huggingface_hub", v, "->", md.version("huggingface_hub"), flush=True)
