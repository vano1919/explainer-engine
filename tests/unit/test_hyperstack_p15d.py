"""Hyperstack p15d fallback (prepared, not enabled): header, cloud-init, name = deadline, the delete-only guard, RP-11 at the proposed caps."""
import copy
import json

import pytest

from explainer_engine.cloud import schedule as S
from explainer_engine.cloud.providers import hyperstack as H
from explainer_engine.cloud.providers import hyperstack_p15d as P
from explainer_engine.cloud.providers.base import ApprovalRequiredError, GpuCapacityOffer, ProviderError

IMG = "ghcr.io/vano1919/tmr-pod@sha256:" + "ab" * 32


def adapter(vms=None, sent=None):
    def tr(method, url, body, headers, timeout):
        if sent is not None:
            sent.append((method, url, body, headers))
        if method == "GET" and url.endswith("/core/virtual-machines"):
            return 200, json.dumps({"instances": vms or []}), {}
        return 200, json.dumps({"instances": [{"id": 7}]}), {}
    return H.HyperstackAdapter(api_key="k" * 8, transport=tr, clock=lambda: 1000.0)


def test_requests_carry_a_user_agent_because_cloudflare_blocks_the_default_signature():
    sent = []
    adapter(sent=sent).list_vms()
    assert sent[0][3]["User-Agent"] == "explainer-engine/0.1" and sent[0][0] == "GET"


def test_the_name_carries_the_deadline_and_only_ee_vms_are_ours():
    n = P.vm_name("p15d", 1794030000)
    assert n == "ee-p15d-until-1794030000" and len(n) <= 50 and P.deadline_of(n) == 1794030000
    assert P.deadline_of("someone-elses-vm") is None and P.deadline_of("ee-x-until-12") is None


def test_cloud_init_pins_the_image_keeps_secrets_out_of_env_and_refuses_unpinned_or_foreign_secrets():
    ci = P.cloud_init(IMG, {"EE_SCRIPT_URL": "https://hf/x.sh", "EE_LIFETIME_S": "9000"}, secrets={"HF_TOKEN": "hf_SECRET"})
    assert ci.startswith("#cloud-config") and IMG in ci and "EE_SCRIPT_URL=" in ci and "--gpus all" in ci
    assert "permissions: '0600'" in ci and ci.count("hf_SECRET") == 1   # only in the root-only env file
    with pytest.raises(ProviderError):
        P.cloud_init("ghcr.io/vano1919/tmr-pod:latest", {})
    with pytest.raises(ProviderError):
        P.cloud_init(IMG, {"HF_TOKEN": "x"})
    with pytest.raises(ProviderError):
        P.cloud_init(IMG, {}, secrets={"HYPERSTACK_API_KEY": "x"})   # the account key never goes on the VM


def test_submit_sends_user_data_only_with_a_full_approval_and_never_by_default():
    offer = GpuCapacityOffer(provider="hyperstack", gpu_type="A100-80G-PCIe", flavor_name="n3-A100x1", region="CANADA-1", vram_gb=80,
                             cpu_cores=28, ram_gb=120, root_disk_gb=100, ephemeral_disk_gb=750, gpu_count=1, available=True,
                             availability_tier="HIGH", fetched_at=1000.0, price_per_hour_usd=1.35)
    sent = []
    a = adapter(sent=sent)
    r = a.submit_job(P.P15D_WORKLOAD, offer, vm_name="ee-p15d-until-1794030000", idempotency_key="k1")   # dry run by default
    assert r["mode"] == "dry_run" and not [s for s in sent if s[0] == "POST"]
    with pytest.raises(ApprovalRequiredError):
        a.submit_job(P.P15D_WORKLOAD, offer, vm_name="ee-p15d-until-1794030000", idempotency_key="k2", dry_run=False, user_data="x")


def test_the_guard_deletes_overdue_ended_and_shutoff_vms_and_leaves_everything_else():
    now = 2_000_000_000
    vms = [{"id": 1, "name": f"ee-p15d-until-{now - 500}", "status": "ACTIVE"},      # past the deadline
           {"id": 2, "name": f"ee-p15d-until-{now + 5000}", "status": "ACTIVE"},     # running
           {"id": 3, "name": f"ee-p15d-until-{now + 5000}", "status": "ACTIVE"},     # ended
           {"id": 4, "name": f"ee-p15d-until-{now + 5000}", "status": "SHUTOFF"},    # billing trap
           {"id": 5, "name": "creators-own-vm", "status": "ACTIVE"}]
    deleted = []

    class A:
        def list_vms(self):
            return vms

        def cancel_job(self, vm_id, mode):
            deleted.append((vm_id, mode))

    rows = P.sweep(A(), now, lambda n: None, dry_run=True)
    assert deleted == [] and {r["id"]: r["verdict"] for r in rows} == {"1": "delete", "2": "keep", "3": "keep", "4": "delete"}   # dry run reports only
    rows = P.sweep(A(), now, lambda n: None, dry_run=False)
    assert sorted(d[0] for d in deleted) == ["1", "4"] and all(m == "delete" for _, m in deleted)   # never "stop"
    assert P.decision(vms[2], "uploads ok\nDONE 0", now) == ("delete", "the job ended: DONE (uploads are verified before the end word)")
    assert P.decision(vms[1], "RUNNING", now)[0] == "keep"


def test_p15d_passes_rp11_on_a_hyperstack_a100_at_3_1_dollars_and_2_5_hours_but_not_at_the_proposed_3_0():
    sch = S.load("explainer_engine/training/pods/p15/p15qc1_schedule.json")
    sch["cards"] = [{"name": "Hyperstack A100 PCIe", "cloud": "COMMUNITY", "price_h": 1.357, "gpu_speed": 0.57}]
    ok, bad = copy.deepcopy(sch), copy.deepcopy(sch)
    ok["limits"].update(max_usd=3.1, max_hours=2.5)
    bad["limits"].update(max_usd=3.0, max_hours=2.5)
    assert S.check(ok) == []
    assert any("RP-11" in x for x in S.check(bad))   # worst case $3.07: the proposed per-VM cap of $3.0 is 7 cents short
