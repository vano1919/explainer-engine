"""What a phone needs to know about the cloud (master brief 2026-10-22, stage B): one command, short answers.

    python -m explainer_engine.cloud status            # pods, jobs, what changed since the last look
    python -m explainer_engine.cloud logs <job|pod>    # the job's events and, for a live pod, its last log lines
    python -m explainer_engine.cloud doctor [text]     # known causes and fixes for what is failing (incident log)
    python -m explainer_engine.cloud budget            # ceilings, the last 24 h, the balance, live estimates
    python -m explainer_engine.cloud incidents [grep]  # the incident log; `incidents add --symptom .. --cause .. --fix ..`
    python -m explainer_engine.cloud stop-all --yes    # the creator's STOP ALL (stops, never deletes)

No invented percentages: a job shows its state, the stage, how long, and the last confirmed sign of life.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from explainer_engine.cloud import incidents, jobs, runpod as R, watchdog
from explainer_engine.core import spend_caps

JOBS_ROOT = R.ROOT / "jobs" / "cloud"
LAST_LOOK = R.RP / "last_look.json"


def _last_look(update, now):
    try:
        last = json.loads(LAST_LOOK.read_text(encoding="utf-8")).get("ts")
    except (OSError, ValueError):
        last = None
    if update:
        LAST_LOOK.parent.mkdir(parents=True, exist_ok=True)
        LAST_LOOK.write_text(json.dumps({"ts": now}), encoding="utf-8")
    return last


def status(api, *, now=None, jobs_root=None, update=True, out=print):
    now = time.time() if now is None else now
    jobs_root = Path(jobs_root or JOBS_ROOT)
    since = _last_look(update, now)
    res = R.check(api, now)
    out(f"RunPod: {len(res['problems'])} problem(s)" + (f"; last look {(now - since) / 60:.0f} min ago" if since else ""))
    for line in res["problems"]:
        out("PROBLEM " + line)
    for line in res["info"]:
        out("ok      " + line)
    all_jobs = jobs.Job.list(jobs_root) if jobs_root.exists() else []
    open_jobs = [j for j in all_jobs if j.state["state"] not in jobs.TERMINAL]
    changed = [j for j in all_jobs if j.state["state"] in jobs.TERMINAL and since and j.state["updated"] > since]
    out(f"jobs: {len(open_jobs)} open, {len(changed)} finished since the last look, {len(all_jobs)} on record")
    for j in open_jobs + changed:
        for line in j.summary(now, since):
            out(line)
    return res, open_jobs


def logs(api, ref, *, tail=60, out=print, jobs_root=None):
    jobs_root = Path(jobs_root or JOBS_ROOT)
    job = next((j for j in jobs.Job.list(jobs_root) if j.state["id"] == ref or j.state.get("resource") == ref), None) \
        if jobs_root.exists() else None
    pid = job.state.get("resource") if job else ref
    if job:
        for r in job.events()[-tail:]:
            out(f"{time.strftime('%m-%d %H:%M', time.gmtime(r['ts']))} {r['kind']:8} {r['text']}")
    p = api.pod(pid) if pid else None
    if p and p.get("status") == "RUNNING":
        for ts, source, line in api.logs(pid, tail=tail):
            out(f"{ts} {source} {line}")
    elif pid:
        out(f"pod {pid}: {'gone' if p is None else p.get('status')}; no live log")


def doctor(api, text=None, *, out=print, jobs_root=None, now=None):
    now = time.time() if now is None else now
    jobs_root = Path(jobs_root or JOBS_ROOT)
    found = False
    if text:
        found = True
        for line in incidents.doctor(text):
            out(line)
    for j in (jobs.Job.list(jobs_root) if jobs_root.exists() else []):
        if j.state["state"] in ("FAILED", "STALLED", "RECOVERY_REQUIRED") or (j.state["state"] in jobs.LIVE and jobs.stall(j, now)):
            found = True
            out(f"--- {j.state['id']} {j.state['state']}: {j.state.get('reason', '')}")
            reason = j.state.get("reason") or ""
            stage = j.state.get("stage") or ("create" if reason.startswith("create") else "any")
            for line in incidents.doctor(reason, stage=stage):
                out("  " + line)
            if j.unstored_outputs():
                out(f"  {len(j.unstored_outputs())} output(s) not in the store: do not release {j.state.get('resource')}")
    for p in api.pods():
        if p.get("status") == "ERROR":
            found = True
            out(f"--- pod {p['id']} {p.get('name')} in ERROR")
            for line in incidents.doctor("pod in ERROR state", stage="any"):
                out("  " + line)
    for line in R.check(api, now)["problems"]:
        found = True
        out("PROBLEM " + line)
    if not found:
        out("nothing is failing; nothing bills without a guard")
    return found


def budget(api, *, now=None, out=print):
    now = time.time() if now is None else now
    caps = spend_caps.load()
    out("ceilings (config/spend_caps.json): " + json.dumps(caps["runpod"]) + " per episode " + json.dumps(caps["per_episode"]))
    try:
        usd, totals = api.billing_total(now - 86400)
        bal = api.balance()
        parts = ", ".join(f"{k.replace('Amount', '')} ${float(v):.2f}" for k, v in totals.items() if k != "totalAmount" and float(v or 0) > 0)
        out(f"last 24 h: ${usd:.2f} of ${caps['runpod']['per_24h_usd']} (every resource{'; ' + parts if parts else ''}; the newest hour may lag); "
            f"balance ${float(bal['clientBalance']):.2f}; spending ${float(bal.get('currentSpendPerHr') or 0):.3f}/h now")
    except R.RunPodError as e:
        out(f"billing not read: {str(e)[:80]}")
    for p in api.pods():
        if p.get("status") in watchdog.LIVE_POD:
            sess = R.sess_read(p["id"])
            est = f"estimate ${R.spent_estimate(sess, now, p)} of ${sess['max_usd']}" if sess else "no session here"
            out(f"live {p['id']} {p.get('name')} ${p.get('costPerHr')}/h: {est}")
        elif p.get("status") in R.ENDED:
            out(f"disk {p['id']} {p.get('name')}: ${R.disk_per_hour(p, False) * 24:.2f}/day")


def incidents_cmd(argv, out=print):
    if argv and argv[0] == "add":
        opts = {argv[i].lstrip("-"): argv[i + 1] for i in range(1, len(argv) - 1, 2) if argv[i].startswith("--")}
        if not opts.get("symptom") or not opts.get("cause") or not opts.get("fix"):
            raise SystemExit("incidents add needs --symptom, --cause and --fix (a fix that lives only in chat does not count)")
        fp = incidents.fingerprint(opts.get("provider", "runpod"), opts.get("resource", "pod"), opts.get("stage", "any"),
                                   opts.get("class", "unknown"), text=opts["symptom"])
        row = incidents.record(fp, opts["symptom"], cause=opts["cause"], fix=opts["fix"], cost_usd=float(opts.get("cost", 0)),
                               source="creator" if opts.get("by") == "creator" else "session")
        out(f"recorded {row['id']} {row['fingerprint']['error_class']}" + (f"; repeats {row['repeat_of']}" if row["repeat_of"] else ""))
        return
    needle = (argv[0] if argv else "").lower()
    for i in incidents.all_incidents():
        line = f"{i['id']} {i.get('date', '')} [{i['fingerprint'].get('error_class')}] {i.get('symptom', '')[:90]} | fix: {i.get('fix', '')[:90]}"
        if not needle or needle in line.lower():
            out(line)


def main(argv=None, api=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    cmd, rest = argv[0], argv[1:]
    if cmd == "incidents":
        return incidents_cmd(rest)
    api = api or R.Api(retries=2, timeout=30)
    if cmd == "status":
        res, _ = status(api)
        return 1 if res["problems"] else 0
    if cmd == "logs":
        if not rest:
            raise SystemExit("logs needs a job id or a pod id")
        logs(api, rest[0], tail=int(rest[rest.index("--tail") + 1]) if "--tail" in rest else 60)
    elif cmd == "doctor":
        return 1 if doctor(api, " ".join(a for a in rest if not a.startswith("--")) or None) else 0
    elif cmd == "budget":
        budget(api)
    elif cmd == "stop-all":
        if "--yes" not in rest:
            raise SystemExit("refused: stop-all needs --yes (the creator's word)")
        done, failed = watchdog.kill_all(api)
        for j in (jobs.Job.list(JOBS_ROOT) if JOBS_ROOT.exists() else []):
            if j.state["state"] in jobs.LIVE:
                j.move("STOPPED", "STOP ALL by the creator", force=True)
        return 1 if failed else 0
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
