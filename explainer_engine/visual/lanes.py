"""The lane planner of the Ink Chronicle path (roadmap 7.1-7.3 and 11, ICW-03; D-97, D-98): allocates every shot of a
``film_shots/3`` episode to VIDEO_3D, STILL_3D or HELPER so the runtime shares meet BP-109 (60 / 30 / 10, within its
tolerance), and assigns each shot one of the 20 archetypes (``visual/archetypes_ic.json``).

    python -m explainer_engine.visual.lanes plan <film_shots.json> [--write] [--report <lane_plan.md>]
    python -m explainer_engine.visual.lanes report <film_shots.json>

The order (roadmap 7.3, "allocate by beat intensity first, then swap at the margin until KP-37 passes"):

1. A seen spoken line longer than BP-108's dialogue cap is split into its lip-sync close-up and an off-screen cover shot
   (the words are divided, never dropped: the speech mix of BP-105 does not move).
2. The shot designer gives each shot its visual archetype, its intensity, the lanes it may take (a seen line is VIDEO_3D
   only; chase, cold open and climax are VIDEO_3D only; aftermath and ending STILL_3D only) and, when the narration could
   be carried by a Python visual, a helper candidate (archetype 12, 13 or 17).
3. Every shot starts on its archetype's default lane. HELPER takes the best helper candidates, never two side by side,
   until it holds BP-109's helper share.
4. Margin swaps between VIDEO_3D and STILL_3D: while the video share is over its target the least intense movable VIDEO
   shot becomes a still (a played scene shot last, a shot inside a long VIDEO run first); while it is under, the most intense
   movable still becomes video. A swap is kept only if it brings both shares nearer their targets.
5. Anti-monotony (roadmap 7.2, KP-48): a VIDEO_3D run longer than the registry's ``video_run_max`` is split by turning a
   movable shot inside it into a still and a still elsewhere into video, only while both shares stay inside the band.

What it cannot fix it reports and leaves (REVIEW, never a silent rewrite): a script whose seen dialogue alone is over the
video band goes back to the writers' room; a run of locked VIDEO shots (a long exchange) stays a KP-48 REVIEW.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.store import write_json_atomic, write_text_atomic
from explainer_engine.scripting import film_shots as F
from explainer_engine.visual import shot_design as SD

EPS = 1e-9


def _f(rule: str, where: str, detail: str, severity: str = "REVIEW") -> dict:
    return {"rule": rule, "severity": severity, "where": where, "detail": detail}


def video_runs(lanes: list[str]) -> list[tuple[int, int]]:
    """``(first index, length)`` of every run of consecutive VIDEO_3D shots."""
    out, start = [], None
    for i, lane in enumerate([*lanes, None]):
        if lane == "VIDEO_3D" and start is None:
            start = i
        elif lane != "VIDEO_3D" and start is not None:
            out.append((start, i - start))
            start = None
    return out


class LanePlanner:
    """Plans one ``film_shots/3`` document. ``plan()`` returns ``(planned document, report)``; the input is never edited."""

    def __init__(self, doc: dict, *, climax_scene: str | None = None):
        if doc.get("schema") != F.V3:
            raise ValueError(f"the lane planner reads {F.V3}, not {doc.get('schema')!r}")
        self.src = doc
        self.share = dict(F.LANE_SHARE)
        self.tol = F.LANE_TOLERANCE
        self.run_max = SD.registry()["planner"]["video_run_max"]
        self.still_penalty = SD.registry()["planner"]["scene_mode_still_penalty"]
        self.climax_scene = climax_scene

    # --- the plan --------------------------------------------------------------------------------------------------------
    def plan(self) -> tuple[dict, dict]:
        doc = copy.deepcopy(self.src)
        designer = SD.ShotDesigner(doc, climax_scene=self.climax_scene)
        shots: list[dict] = []
        split = []
        for s in doc["shots"]:
            parts = designer.split_voiced(s)
            if len(parts) > 1:
                split.append(s["id"])
            shots += parts
        doc["shots"] = shots
        designer = SD.ShotDesigner(doc, climax_scene=self.climax_scene)
        self.shots = shots
        self.secs = [float(s["seconds"]) for s in shots]
        self.total = sum(self.secs)
        self.aid = [designer.visual_archetype(s) for s in shots]
        self.allowed = [designer.lanes(s, a) for s, a in zip(shots, self.aid)]
        self.heat = [designer.intensity(s, a) for s, a in zip(shots, self.aid)]
        self.helper = [designer.helper_candidate(s) for s in shots]
        self.scene_mode = [s.get("mode") == "scene" for s in shots]
        before = F.lane_shares(self.src["shots"], F.V3)
        lanes = [SD.archetype(a)["default_lane"] if SD.archetype(a)["default_lane"] in ok else ok[0]
                 for a, ok in zip(self.aid, self.allowed)]
        lanes = self._helpers(lanes)
        lanes, swaps = self._margin(lanes)
        lanes, pairs = self._monotony(lanes)
        planned, rows = [], []
        for i, (s, lane) in enumerate(zip(shots, lanes)):
            if lane == "HELPER":
                aid, visual, _score = self.helper[i]
            else:
                aid, visual = self.aid[i], None
            card = designer.design(s, aid, lane, visual)
            planned.append(card)
            rows.append({"id": s["id"], "scene": s["scene"], "seconds": self.secs[i], "was": s["lane"], "lane": lane,
                         "archetype": aid, "title": SD.archetype(aid)["title"], "intensity": self.heat[i],
                         "helper_score": None if self.helper[i] is None else self.helper[i][2],
                         "still_mode": card.get("still_mode"), "helper_archetype": card.get("helper_archetype"),
                         "camera_rig": designer.camera_rig(s, lane, card.get("still_mode")),
                         "allowed": self.allowed[i] + (["HELPER"] if self.helper[i] else [])})
        doc["shots"] = planned
        shares = F.lane_shares(planned, F.V3)
        report = {"episode": doc.get("episode"), "shots": len(planned), "total_s": self.total, "split_voiced": split,
                  "shares_before": before, "shares": shares, "target": self.share, "tolerance": self.tol,
                  "margin_swaps": swaps, "monotony_swaps": pairs, "climax_scene": designer.climax,
                  "cold_open_scene": designer.cold_open, "rows": rows, "findings": self.findings(planned)}
        return doc, report

    def _share(self, lanes: list[str], lane: str) -> float:
        return sum(x for x, ln in zip(self.secs, lanes) if ln == lane) / self.total if self.total else 0.0

    def _distance(self, lanes: list[str]) -> float:
        return sum(abs(self._share(lanes, k) - self.share[{"VIDEO_3D": "video", "STILL_3D": "still", "HELPER": "helper"}[k]])
                   for k in SD.LANES)

    def _overruns(self, lanes: list[str]) -> int:
        """VP-07's family overruns of the helper visuals (BP-141's rotation window), counted by variant_plan.dynamics, the
        one function that counts them, on blocks of this plan."""
        from explainer_engine.edit import visual_compensator as VC
        from explainer_engine.scripting import variant_plan as VP

        segs: dict[str, dict] = {}
        for i, (s, lane) in enumerate(zip(self.shots, lanes)):
            seg = segs.setdefault(s["scene"], {"id": s["scene"], "blocks": []})
            block = {"seconds": self.secs[i], "category": "scene" if lane == "VIDEO_3D" else "hold"}
            if lane == "HELPER":
                visual = VC.archetype(self.helper[i][1])
                block = {"seconds": self.secs[i], "category": "map_pure" if visual["lane"] == "MAP" else "compensator",
                         "archetype": visual["number"]}
            seg["blocks"].append(block)
        return len(VP.dynamics(list(segs.values()), VP.profile("D"))["family_overruns"])

    def _helpers(self, lanes: list[str]) -> list[str]:
        """The best helper candidates up to BP-109's helper share: never the same visual twice in a row (VP-06), at most two
        helper visuals side by side, and none that adds a family overrun of BP-141's rotation window (VP-07)."""
        target = self.share["helper"] * self.total
        order = sorted((i for i, h in enumerate(self.helper) if h is not None),
                       key=lambda i: (-self.helper[i][2], self.heat[i], i))
        got, over = 0.0, self._overruns(lanes)
        for i in order:
            if got + self.secs[i] > target + 0.5 * self.secs[i] + EPS:
                continue
            near = [j for j in (i - 1, i + 1) if 0 <= j < len(lanes) and lanes[j] == "HELPER"]
            if len(near) > 1 or any(self.helper[j][1] == self.helper[i][1] for j in near):
                continue
            trial = list(lanes)
            trial[i] = "HELPER"
            n = self._overruns(trial)
            if n > over:
                continue
            lanes, got, over = trial, got + self.secs[i], n
        return lanes

    def _in_long_run(self, lanes: list[str]) -> set[int]:
        return {k for start, n in video_runs(lanes) if n > self.run_max for k in range(start, start + n)}

    def _margin(self, lanes: list[str]) -> tuple[list[str], int]:
        swaps = 0
        while True:
            video = self._share(lanes, "VIDEO_3D")
            want = self.share["video"]
            long_run = self._in_long_run(lanes)
            if video > want + EPS:
                cand = [i for i, ln in enumerate(lanes) if ln == "VIDEO_3D" and "STILL_3D" in self.allowed[i]]
                key = lambda i: (self.heat[i] + self.still_penalty * self.scene_mode[i] - 2 * (i in long_run), i)  # noqa: E731
                new = "STILL_3D"
            else:
                cand = [i for i, ln in enumerate(lanes) if ln == "STILL_3D" and "VIDEO_3D" in self.allowed[i]]
                key = lambda i: (-self.heat[i], i)  # noqa: E731
                new = "VIDEO_3D"
            if not cand:
                return lanes, swaps
            i = min(cand, key=key)
            trial = list(lanes)
            trial[i] = new
            if self._distance(trial) >= self._distance(lanes) - EPS:
                return lanes, swaps
            lanes, swaps = trial, swaps + 1

    def _in_band(self, lanes: list[str]) -> bool:
        return all(abs(self._share(lanes, k) - self.share[v]) <= self.tol + EPS
                   for k, v in (("VIDEO_3D", "video"), ("STILL_3D", "still"), ("HELPER", "helper")))

    def _excess(self, lanes: list[str]) -> int:
        return sum(n - self.run_max for _s, n in video_runs(lanes) if n > self.run_max)

    def _monotony(self, lanes: list[str]) -> tuple[list[str], int]:
        """Split long VIDEO runs by pair swaps that keep the shares in the band; never makes the excess worse."""
        pairs = 0
        if not self._in_band(lanes):
            return lanes, pairs
        tried: set[int] = set()
        for _ in range(len(lanes)):
            runs = [(s, n) for s, n in video_runs(lanes) if n > self.run_max]
            best = None
            base = self._excess(lanes)
            for start, n in sorted(runs, key=lambda r: -r[1]):
                inside = [i for i in range(start, start + n) if "STILL_3D" in self.allowed[i] and i not in tried]
                inside.sort(key=lambda i: (abs(i - (start + n / 2 - 0.5)), self.heat[i] + self.still_penalty * self.scene_mode[i]))
                for i in inside[:3]:
                    for j in sorted((j for j, ln in enumerate(lanes) if ln == "STILL_3D" and "VIDEO_3D" in self.allowed[j]),
                                    key=lambda j: (abs(self.secs[j] - self.secs[i]), -self.heat[j])):
                        trial = list(lanes)
                        trial[i], trial[j] = "STILL_3D", "VIDEO_3D"
                        if self._in_band(trial) and self._excess(trial) < base:
                            best = trial
                            break
                    if best:
                        break
                    tried.add(i)
                if best:
                    break
            if best is None:
                return lanes, pairs
            lanes, pairs = best, pairs + 1
        return lanes, pairs

    # --- findings --------------------------------------------------------------------------------------------------------
    def findings(self, shots: list[dict]) -> list[dict]:
        """KP-37 (a share the plan could not bring into BP-109's band, with the reason) and KP-48 (a VIDEO_3D run over the
        registry's ``video_run_max``). REVIEW only: the planner never rewrites the script to pass."""
        out: list[dict] = []
        shares = F.lane_shares(shots, F.V3)
        seen = sum(float(s["seconds"]) for s in shots if s.get("lipsync")) / self.total if self.total else 0.0
        for lane, detail in F.lane_share_findings(shares):
            why = ""
            if lane == "video" and shares["video"] > self.share["video"] and seen > self.share["video"] + self.tol:
                why = (f"; seen spoken lines alone are {seen:.0%} of the runtime and need VIDEO_3D lip-sync: the script goes back "
                       "to the writers' room (fewer or shorter seen lines, or lines covered off screen), never a silent rewrite")
            out.append(_f("KP-37", "episode", detail + why))
        for start, n in video_runs([s["lane"] for s in shots]):
            if n > self.run_max:
                run = range(start, start + n)
                locked = all(self.allowed[k] == ["VIDEO_3D"] for k in run)
                why = ("; every shot of it may only be VIDEO_3D (a seen spoken line, the cold open, the climax or a chase): a "
                       "reaction, an insert or a cutaway written into the script breaks it") if locked else ""
                out.append(_f("KP-48", f"{shots[start]['id']}..{shots[start + n - 1]['id']}",
                              f"{n} VIDEO_3D shots in a row with no STILL_3D or HELPER between (at most {self.run_max}, "
                              "visual/archetypes_ic.json planner.video_run_max, roadmap 7.2)" + why))
        return out


def plan(doc: dict, *, climax_scene: str | None = None) -> tuple[dict, dict]:
    return LanePlanner(doc, climax_scene=climax_scene).plan()


def report_md(report: dict, *, title: str = "Lane plan") -> str:
    """The plan for a reader: shares before and after, the findings, one row per shot."""
    pct = lambda d: ", ".join(f"{k} {v:.1%}" for k, v in d.items())  # noqa: E731
    lines = [f"# {title}", "",
             "Generated by `python -m explainer_engine.visual.lanes` (ICW-03, roadmap 7.3): lanes by BP-109 runtime share, "
             "archetypes from `explainer_engine/visual/archetypes_ic.json`.", "",
             f"- {report['shots']} shots, {report['total_s']:g} s; cold open {report['cold_open_scene']}, "
             f"climax {report['climax_scene']}",
             f"- shares before: {pct(report['shares_before'])}",
             f"- shares after: {pct(report['shares'])} (BP-109: {pct(report['target'])} +- {report['tolerance']:.0%})",
             f"- margin swaps {report['margin_swaps']}, anti-monotony pair swaps {report['monotony_swaps']}, voiced lines "
             f"split {len(report['split_voiced'])}", ""]
    if report["findings"]:
        lines += ["## Findings", ""] + [f"- {f['severity']} {f['rule']} {f['where']}: {f['detail']}" for f in report["findings"]]
        lines.append("")
    lines += ["## Shots", "", "| shot | s | was | lane | archetype | intensity | helper | still / visual | rig |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in report["rows"]:
        extra = r["still_mode"] or r["helper_archetype"] or ""
        hs = "" if r["helper_score"] is None else f"{r['helper_score']:g}"
        lines.append(f"| {r['id']} | {r['seconds']:g} | {r['was']} | {r['lane']} | {r['archetype']} {r['title']} | "
                     f"{r['intensity']:g} | {hs} | {extra} | {r['camera_rig'] or ''} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in ("plan", "report"):
        print(__doc__)
        return 2
    cmd, path = argv[0], Path(argv[1])
    doc = json.loads(path.read_text(encoding="utf-8"))
    planned, report = plan(doc)
    contracts.validate(planned)
    for f in report["findings"]:
        print(f"{f['severity']} {f['rule']} {f['where']}: {f['detail']}")
    print(", ".join(f"{k} {v:.1%}" for k, v in report["shares"].items()))
    if cmd == "plan" and "--write" in argv:
        write_json_atomic(path, planned)
    if "--report" in argv:
        write_text_atomic(Path(argv[argv.index("--report") + 1]), report_md(report))
    if cmd == "report":
        print(report_md(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
