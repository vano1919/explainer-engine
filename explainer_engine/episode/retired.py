"""The retired tools of the old era (Q10 answer A, D-131): kept as code, refused inside a v4.3 episode.

``config/retired_era.json`` lists the tools (Qwen pictures, the xworld LoRA, LTX, the Blender scene route, RunPod pods, the
legacy paint plans) with their entry points and what replaced them. ``refuse(tool, *paths)`` raises ``ConfigError`` when any of
the paths, the working directory or ``$EXPLAINER_EPISODE`` lies inside a v4.3 episode (a folder whose ``episode.json`` has
schema ``episode_manifest/1``); outside one it returns quietly, so the episodes made before 2026-11-12 keep their tools.
``retired_routes_in(script)`` lists the shots of a script that name a retired route (the runner's G1 row ``no_retired_route``).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from explainer_engine.core.errors import ConfigError

DATA = Path(__file__).resolve().parents[2] / "config" / "retired_era.json"
MANIFEST_SCHEMA = "episode_manifest/1"


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def v43_episode_of(path) -> Path | None:
    """The v4.3 episode folder that holds ``path`` (the path itself or a parent with an episode manifest), else None."""
    if not path:
        return None
    p = Path(path).resolve()
    for d in [p, *p.parents]:
        m = d / "episode.json"
        if m.is_file():
            try:
                if json.loads(m.read_text(encoding="utf-8")).get("schema") == MANIFEST_SCHEMA:
                    return d
            except (OSError, ValueError):
                return None
    return None


def refuse(tool: str, *paths, env=None, cwd=None) -> None:
    """Stop a retired tool inside a v4.3 episode (Q10, D-131); nothing happens outside one."""
    tools = load()["tools"]
    if tool not in tools:
        raise ValueError(f"unknown retired tool {tool!r}; known: {sorted(tools)}")
    env = os.environ if env is None else env
    for where in (*paths, env.get("EXPLAINER_EPISODE"), cwd or os.getcwd()):
        ep = v43_episode_of(where)
        if ep is not None:
            t = tools[tool]
            raise ConfigError(f"{tool} ({t['what']}) is retired for a v4.3 episode (Q10, D-131) and {ep.name} is one; "
                              f"use {t['replacement']}. Nothing was started.")


def retired_routes_in(script: dict) -> list[str]:
    """``shot_id: value`` for every shot whose route, generation mode or engine names a retired route."""
    bad = {r.lower() for r in load()["retired_routes"]}
    out = []
    for s in script.get("shots", []):
        for k in ("route", "generation_mode", "engine", "visual_route"):
            v = s.get(k)
            if isinstance(v, str) and v.lower() in bad:
                out.append(f"{s.get('shot_id')}: {k} {v}")
    return out


ACTIVE_ROOTS = ("explainer_engine.episode.run", "explainer_engine.aivideo.wan_adapter",
                "explainer_engine.training.pods.wan.modal_wan_jobs")


def _module_file(mod: str, root: Path) -> Path | None:
    base = root.joinpath(*mod.split("."))
    for p in (base.with_suffix(".py"), base / "__init__.py"):
        if p.is_file():
            return p
    return None


V43_PACKAGES = ("explainer_engine.episode", "explainer_engine.aivideo.wan_adapter", "explainer_engine.training.pods.wan",
                "explainer_engine.maps", "explainer_engine.audio.stems", "explainer_engine.production.layers25d",
                "explainer_engine.imagegen.turn_pack")


def _nodes(tree, lazy: bool):
    """The import statements of a module: all of them (``lazy``: imports inside functions too) or only those run when the
    module loads (module level, class bodies, ``if``/``try`` blocks; not function bodies)."""
    import ast
    if lazy:
        yield from ast.walk(tree)
        return
    stack = list(tree.body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        yield n
        stack.extend(ast.iter_child_nodes(n))


def _imports(path: Path, mod: str, lazy: bool) -> set[str]:
    import ast
    out = set()
    pkg = mod.rsplit(".", 1)[0] if not path.name == "__init__.py" else mod
    for n in _nodes(ast.parse(path.read_text(encoding="utf-8")), lazy):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            if n.level:
                parts = pkg.split(".")
                base = ".".join(parts[:len(parts) - n.level + 1] + ([base] if base else []))
            out.add(base)
            out |= {f"{base}.{a.name}" for a in n.names}
    return {m for m in out if m.startswith("explainer_engine")}


def active_path(roots=ACTIVE_ROOTS) -> dict[str, list[str]]:
    """Every explainer_engine module the v4.3 path imports, transitively (static, from the source), with the module that
    first pulled it in. Inside the v4.3 packages (``V43_PACKAGES``) an import inside a function counts (the runner's stages
    import their tools lazily); elsewhere only what a module imports when it loads (core/store's approval checks import
    their tools inside the check that needs them, and that is not a use by the v4.3 path)."""
    root = DATA.parents[1]
    seen: dict[str, list[str]] = {}
    todo = [(r, "root") for r in roots]
    while todo:
        mod, by = todo.pop()
        f = _module_file(mod, root)
        if f is None or mod in seen:
            continue
        seen[mod] = [by]
        parent = mod.rsplit(".", 1)[0]
        if parent != mod and parent.startswith("explainer_engine"):
            todo.append((parent, mod))   # importing a module runs its package's __init__ first
        lazy = any(mod == p or mod.startswith(p + ".") for p in V43_PACKAGES)
        todo += [(m, mod) for m in sorted(_imports(f, mod, lazy))]
    return seen


def retired_on_active_path(roots=ACTIVE_ROOTS) -> list[str]:
    """``module <- importer`` for every retired entry module (``config/retired_era.json`` ``entry``) the v4.3 path imports.
    A module listed under ``loaded_not_used`` (with the reason it is read but never run) is reported apart, not as a hit."""
    data = load()
    entries = [e.replace("/", ".").removesuffix(".py").rstrip(".") for t in data["tools"].values() for e in t["entry"]]
    allowed = data.get("loaded_not_used") or {}
    hits = []
    for mod, by in sorted(active_path(roots).items()):
        if mod not in allowed and any(mod == e or mod.startswith(e + ".") for e in entries):
            hits.append(f"{mod} <- {by[0]}")
    return hits


if __name__ == "__main__":   # python -m explainer_engine.episode.retired: the OR-34 audit's free first check
    hits = retired_on_active_path()
    print(json.dumps({"active_modules": len(active_path()), "retired_on_active_path": hits,
                      "loaded_not_used": sorted(set(load().get("loaded_not_used") or {}) & set(active_path()))}, indent=1))
    raise SystemExit(1 if hits else 0)
