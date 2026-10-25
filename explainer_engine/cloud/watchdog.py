"""The watchdog that does not live in the Claude session (master brief 2026-10-22, stage B): pure rules over what the
provider shows, run by any machine with the RunPod key: the GitHub Actions cron (``.github/workflows/watchdog.yml``, every
30 min and a kill-all button in GitHub Mobile), a Cloudflare Worker later, or this session's hooks.

    python -m explainer_engine.cloud.watchdog            # report only (exit 1 when something needs a hand)
    python -m explainer_engine.cloud.watchdog --apply    # stop what the rules say; alert through ntfy
    python -m explainer_engine.cloud.watchdog --kill-all --yes   # the creator's STOP ALL: every live pod is stopped

Rules (``decide``): a live pod past the lifetime in its name, or without one, is stopped (nobody approved it, or the
approval ran out); a pod in ERROR is reported; when the last 24 h of billing reach the creator's ceiling every live pod is
stopped; a balance under the floor is reported; a stopped disk is listed with its $/day; a job record that has gone quiet
(``jobs.stall``) is reported, and its pod is stopped only when every output is already in the store (never a sole copy).
The rules need no session file, so they hold after the sandbox is gone. Stops go through ``runpod.stop`` (verified);
nothing here deletes.
"""
from __future__ import annotations

import json
import sys
import time

from explainer_engine.cloud import incidents, jobs, runpod as R
from explainer_engine.core import spend_caps

LIVE_POD = ("RUNNING", "PROVISIONING", "STARTING")
GITHUB_ACTIONS = "https://github.com/vano1919/explainer-engine/actions/workflows/watchdog.yml"


def decide(pods, *, now, caps, billed_24h=None, balance=None, job_list=(), stall_limits=None, volumes=(), global_volumes=(),
           endpoints=(), listing_errors=()):
    """{"stop": [(pod id, why)], "alerts": [...], "info": [...], "jobs": [(job, new state, why)]} from one look.
    ``billed_24h`` is the WHOLE account (``Api.billing_total``): pods, serverless, storage. Volumes and endpoints cannot be
    stopped by a rule (deleting is the creator's word), so they are alerts with their price."""
    out = {"stop": [], "alerts": [], "info": [], "jobs": []}
    keep = set(caps.get("keep_network_volumes", []))
    for v in volumes:
        day = float(v.get("size") or 0) * R.GB_MONTH_NETWORK_VOLUME / R.HOURS_PER_MONTH * 24
        (out["info"] if v["id"] in keep else out["alerts"]).append(f"network volume {v['id']} {v.get('name', '')} {v.get('size')} GB bills ${day:.2f}/day with no pod")
    for v in global_volumes:
        (out["info"] if v["id"] in keep else out["alerts"]).append(f"global volume {v['id']} {v.get('name', '')} exists (price not modelled)")
    for e in endpoints:
        if (e.get("workersMin") or 0) > 0:
            out["alerts"].append(f"serverless endpoint {e['id']} {e.get('name', '')} keeps {e['workersMin']} worker(s) on while idle")
    for err in listing_errors:
        out["alerts"].append(f"could not list {err}: something may bill unseen")
    live = [p for p in pods if p.get("status") in LIVE_POD]
    for p in pods:
        st, pid, name = p.get("status"), p["id"], p.get("name") or ""
        label = f"{pid} {name} {st} ${p.get('costPerHr')}/h"
        if st in LIVE_POD:
            if R.until_of(name) is None:
                out["stop"].append((pid, "no approved lifetime in its name (made outside the manager)"))
            elif R.expired(name, now):
                out["stop"].append((pid, f"its approved lifetime ended {(now - R.until_of(name)) / 60:.0f} min ago"))
            else:
                out["info"].append(f"{label}, approved until {time.strftime('%H:%M UTC', time.gmtime(R.until_of(name)))}")
        elif st == "ERROR":
            out["alerts"].append(f"{label}: the pod is in ERROR; its disk ({p.get('volumeInGb')} GB) still bills; the creator decides")
        elif st == "EXITED":
            out["info"].append(f"{pid} {name} stopped: disk {p.get('volumeInGb')} GB bills ${R.disk_per_hour(p, False) * 24:.2f}/day")
    if billed_24h is not None and billed_24h >= caps["per_24h_usd"] - 1e-9 and live:
        for p in live:
            out["stop"].append((p["id"], f"24 h billing ${billed_24h:.2f} reached per_24h_usd {caps['per_24h_usd']}"))
    if billed_24h is not None and billed_24h >= 0.8 * caps["per_24h_usd"]:
        out["alerts"].append(f"24 h billing ${billed_24h:.2f} is at {billed_24h / caps['per_24h_usd'] * 100:.0f} % of per_24h_usd {caps['per_24h_usd']}")
    if balance is not None and balance < caps["min_balance_left_usd"]:
        out["alerts"].append(f"balance ${balance:.2f} is under min_balance_left_usd {caps['min_balance_left_usd']}")
    live_ids = {p["id"] for p in live}
    for job in job_list:
        st = job.state["state"]
        if st not in jobs.LIVE:
            continue
        pid = job.state.get("resource")
        if pid and pid not in live_ids and st != "STOPPING":
            out["jobs"].append((job, "RECOVERY_REQUIRED" if job.unstored_outputs() else "FAILED",
                                f"the record says {st} but pod {pid} is not live"))
            continue
        why = jobs.stall(job, now, stall_limits)
        if why or st == "STALLED":
            quiet = now - (job.last_heartbeat() or {"ts": job.state["since"]})["ts"]
            limit = (stall_limits or {}).get(st) or jobs.STALL_AFTER.get(st, jobs.STALL_AFTER["RUNNING"])
            if st != "STALLED":
                out["jobs"].append((job, "STALLED", why))
                out["alerts"].append(f"{job.state['id']}: {why}")
            if pid in live_ids and quiet > 2 * limit:
                if job.safe_to_release():
                    out["stop"].append((pid, f"job {job.state['id']} quiet for {quiet / 60:.0f} min and every output is stored"))
                    out["jobs"].append((job, "STOPPING", "stopped by the watchdog after a long stall; outputs are stored"))
                else:
                    out["jobs"].append((job, "RECOVERY_REQUIRED", f"quiet for {quiet / 60:.0f} min with {len(job.unstored_outputs())} unstored output(s): not stopped"))
                    out["alerts"].append(f"{job.state['id']}: stalled with unstored outputs on {pid}; a person must push or decide")
    seen = set()
    out["stop"] = [(pid, why) for pid, why in out["stop"] if not (pid in seen or seen.add(pid))]
    return out


def run(api, *, now=None, apply=False, push=R.notify, jobs_root=None, log=print):
    """One watchdog pass: look, decide, (stop), record, alert. Returns the decision plus what was done."""
    now = time.time() if now is None else now
    caps = spend_caps.runpod()
    pods = api.pods()
    billed = balance = None
    errors = []
    try:
        billed, _ = api.billing_total(now - 86400)
        balance = float(api.balance()["clientBalance"])
    except R.RunPodError as e:
        errors.append(f"billing/balance ({str(e)[:60]})")
    listings = {}
    for what, call in (("network volumes", api.network_volumes), ("global volumes", api.global_volumes), ("serverless endpoints", api.endpoints)):
        rows, err = R._quiet(call)
        listings[what] = rows
        if err:
            errors.append(f"{what} ({err})")
    job_list = jobs.Job.list(jobs_root) if jobs_root else []
    d = decide(pods, now=now, caps=caps, billed_24h=billed, balance=balance, job_list=job_list, volumes=listings["network volumes"],
               global_volumes=listings["global volumes"], endpoints=listings["serverless endpoints"], listing_errors=errors)
    d["stopped"], d["failed"] = [], []
    for pid, why in d["stop"]:
        line = f"stop {pid}: {why}"
        if not apply:
            log("WOULD " + line)
            continue
        try:
            st = R.stop(api, pid)
            d["stopped"].append(f"{pid} -> {st}: {why}")
            log(line + f" -> {st}")
            incidents.record(incidents.fingerprint("runpod", "pod", "any", text=why), f"watchdog stopped {pid}: {why}",
                             cause="see why", fix="stopped by the watchdog", source="watchdog")
        except (R.RunPodError, TimeoutError) as e:
            d["failed"].append(f"{pid}: {str(e)[:120]}")
            log(f"FAILED {line}: {str(e)[:120]}")
    for job, state, why in d["jobs"]:
        if apply and job.state["state"] != state:
            try:
                job.move(state, why, now=now, force=True)
            except jobs.IllegalMove as e:
                log(str(e))
        log(f"job {job.state['id']}: {state}: {why}")
    for line in d["alerts"]:
        log("ALERT " + line)
    for line in d["info"]:
        log("ok    " + line)
    if apply and (d["stopped"] or d["failed"] or d["alerts"]):
        text = "; ".join(d["stopped"] + d["failed"] + d["alerts"])[:600]
        push("Watchdog: " + ("pods stopped" if d["stopped"] else "needs a hand" if d["failed"] else "warning"), text,
             "urgent" if d["failed"] else "high")
    return d


def kill_all(api, *, push=R.notify, log=print):
    """The creator's STOP ALL from a phone: every live pod is stopped (never deleted); the result is pushed."""
    done, failed = [], []
    for p in api.pods():
        if p.get("status") in LIVE_POD:
            try:
                done.append(f"{p['id']} -> {R.stop(api, p['id'])}")
            except (R.RunPodError, TimeoutError) as e:
                failed.append(f"{p['id']}: {str(e)[:100]}")
    log("\n".join(done + failed) or "nothing was running")
    push("STOP ALL done" if not failed else "STOP ALL: a pod did not stop", "; ".join(done + failed)[:600] or "nothing was running",
         "high" if not failed else "urgent")
    return done, failed


def main(argv=None, api=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    api = api or R.Api(retries=2, timeout=30)
    if "--kill-all" in argv:
        if "--yes" not in argv:
            raise SystemExit("refused: --kill-all needs --yes (the creator's word)")
        done, failed = kill_all(api)
        return 1 if failed else 0
    jobs_root = R.ROOT / "jobs" / "cloud"
    d = run(api, apply="--apply" in argv, jobs_root=jobs_root if jobs_root.exists() else None)
    if "--json" in argv:
        print(json.dumps({k: v for k, v in d.items() if k != "jobs"}, default=str))
    return 1 if d["failed"] or d["alerts"] or (d["stop"] and "--apply" not in argv) else 0


if __name__ == "__main__":
    sys.exit(main())
