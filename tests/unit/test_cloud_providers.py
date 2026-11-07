"""Unit tests for provider-neutral cloud GPU adapters (Hyperstack, Modal, RunPod) and selector.

Covers all 18 required test scenarios from Section 13 of the RunPod Alternatives Research & Adapter spec:
1. Provider inventory response parsing (Hyperstack, Modal, RunPod)
2. Empty stock (`status == "no_safe_option"`)
3. Stale stock data (`StaleStockError`)
4. Unsupported GPU (`UnsupportedGpuError`)
5. Insufficient VRAM (`InsufficientVramError`)
6. Region mismatch (`RegionMismatchError`)
7. Price lookup failure (`PriceLookupError`)
8. Cost estimate exceeding proposed budget (`BudgetExceededError`)
9. Missing approval (`ApprovalRequiredError`)
10. Dry-run selection (`ProviderSelector.select` and `submit_job(dry_run=True)`)
11. Provisioning timeout without duplicate create (`UnclearProvisionError`, `reconcile_existing`)
12. Provider rate limiting (`RateLimitError` on HTTP 429)
13. Authentication failure without secret leakage (`AuthenticationError` + `redact_secrets`)
14. Provider lifecycle mapping (including Hyperstack `SHUTOFF` billing-trap warning and `sync_job_from_view`)
15. Cancellation mapping (`cancel_job` refusing `mode="stop"` on Hyperstack, allowing `hibernate`/`delete`)
16. Artifact persistence and hash verification (`verify_and_mark_stored` with `cloud.jobs.Job`)
17. Recovery from a partially completed job (`RECOVERY_REQUIRED` when unstored outputs exist on failure)
18. Existing RunPod regression checks (`runpod.norm`, `runpod.disk_per_hour`, `config/spend_caps.json` untouched)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from explainer_engine.cloud import jobs, runpod
from explainer_engine.cloud.providers import (
    ApprovalGate,
    ApprovalRequiredError,
    AuthenticationError,
    BudgetExceededError,
    DuplicateRequestError,
    GpuCapacityOffer,
    HyperstackAdapter,
    InsufficientVramError,
    ModalAdapter,
    PriceLookupError,
    ProviderError,
    ProviderSelector,
    RateLimitError,
    RegionMismatchError,
    RunPodProviderAdapter,
    StaleStockError,
    UnclearProvisionError,
    UnsupportedGpuError,
    WORKLOAD_PRESETS,
    redact_secrets,
    sync_job_from_view,
    verify_and_mark_stored,
)


def _sample_hyperstack_flavors() -> dict:
    return {
        "data": [
            {
                "gpu": "A100-80G-PCIe",
                "region_name": "CANADA-1",
                "flavors": [
                    {
                        "name": "n3-A100x1",
                        "cpu": 28,
                        "ram": 120.0,
                        "disk": 100,
                        "ephemeral": 750,
                        "gpu_count": 1,
                        "stock_available": True,
                    }
                ],
            },
            {
                "gpu": "H100-80G-PCIe",
                "region_name": "CANADA-1",
                "flavors": [
                    {
                        "name": "n3-H100x1",
                        "cpu": 28,
                        "ram": 180.0,
                        "disk": 100,
                        "ephemeral": 750,
                        "gpu_count": 1,
                        "stock_available": True,
                    }
                ],
            },
            {
                "gpu": "L40",
                "region_name": "CANADA-1",
                "flavors": [
                    {
                        "name": "n3-L40x1",
                        "cpu": 28,
                        "ram": 58.0,
                        "disk": 100,
                        "ephemeral": 725,
                        "gpu_count": 1,
                        "stock_available": False,
                    }
                ],
            },
        ]
    }


def _sample_hyperstack_pricebook() -> list:
    return [
        {"name": "A100-80G-PCIe", "value": "1.35", "original_value": "1.60"},
        {"name": "H100-80G-PCIe", "value": "1.90", "original_value": "2.50"},
        {"name": "L40", "value": "1.00", "original_value": "1.20"},
    ]


class _FakeRunPodApi:
    def catalog(self, cloud: str) -> list[dict]:
        if cloud == "SECURE":
            return [
                {
                    "id": "NVIDIA A100 80GB PCIe",
                    "memory": 80,
                    "availability": "HIGH",
                    "price": {"secure": 1.39, "community": 1.19},
                }
            ]
        return []


class TestCloudProviders(unittest.TestCase):
    """Comprehensive unit tests for all 18 provider adapter and selector scenarios."""

    def test_01_provider_inventory_response_parsing(self) -> None:
        now = 1_760_000_000.0

        def fake_transport(
            method: str, url: str, body: bytes | None, headers: dict[str, str], timeout: int
        ) -> tuple[int, str, dict[str, str]]:
            if url.endswith("/pricebook"):
                return 200, json.dumps(_sample_hyperstack_pricebook()), {}
            if url.endswith("/core/flavors"):
                return 200, json.dumps(_sample_hyperstack_flavors()), {}
            raise AssertionError(f"Unexpected URL: {url}")

        hs = HyperstackAdapter(api_key="hs-test-key", transport=fake_transport, clock=lambda: now)
        hs_offers = hs.list_gpu_capacity(fetched_at=now)
        self.assertEqual(len(hs_offers), 3)
        by_gpu = {o.gpu_type: o for o in hs_offers}
        self.assertTrue(by_gpu["A100-80G-PCIe"].available)
        self.assertEqual(by_gpu["A100-80G-PCIe"].flavor_name, "n3-A100x1")
        self.assertAlmostEqual(by_gpu["A100-80G-PCIe"].price_per_hour_usd or 0.0, 1.35)
        self.assertEqual(by_gpu["A100-80G-PCIe"].ephemeral_disk_gb, 750)
        self.assertFalse(by_gpu["L40"].available)

        md = ModalAdapter(token_id="ak-test", token_secret="as-test", clock=lambda: now)
        md_offers = md.list_gpu_capacity(gpu_types=("A100-80GB", "H100"), fetched_at=now)
        self.assertEqual({o.gpu_type for o in md_offers}, {"A100-80GB", "H100"})
        self.assertEqual(md_offers[0].vram_gb, 80)

        rp = RunPodProviderAdapter(api=_FakeRunPodApi(), clock=lambda: now)
        rp_offers = rp.list_gpu_capacity(clouds=("SECURE",), fetched_at=now)
        self.assertEqual(len(rp_offers), 1)
        self.assertEqual(rp_offers[0].gpu_type, "NVIDIA A100 80GB PCIe")
        self.assertTrue(rp_offers[0].available)
        self.assertAlmostEqual(rp_offers[0].price_per_hour_usd or 0.0, 1.39)

    def test_02_empty_stock_returns_no_safe_option(self) -> None:
        now = 1_760_000_000.0
        hs = HyperstackAdapter(api_key="hs-test")
        md = ModalAdapter()
        selector = ProviderSelector({"hyperstack": hs, "modal": md})
        workload = WORKLOAD_PRESETS["workload_c_j5_minimised_p12_p14"]
        empty_offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=False,
            availability_tier="NONE",
            fetched_at=now,
            price_per_hour_usd=1.35,
        )
        res = selector.select(workload, [empty_offer], now=now)
        self.assertEqual(res["status"], "no_safe_option")
        self.assertEqual(res["candidates"], [])
        self.assertIn("out of stock", res["rejected"][0]["reason"])

    def test_03_stale_stock_raises_stale_stock_error(self) -> None:
        now = 1_760_000_500.0
        stale_offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now - 300.0,
            price_per_hour_usd=1.35,
        )
        hs = HyperstackAdapter(api_key="hs-test")
        with self.assertRaises(StaleStockError):
            hs.estimate_cost(WORKLOAD_PRESETS["workload_b_ltx_30s"], stale_offer, now=now)

    def test_04_unsupported_gpu_raises_unsupported_gpu_error(self) -> None:
        now = 1_760_000_000.0
        bad_offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="UNKNOWN-GPU-9999",
            flavor_name="n3-unknown",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=16,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=500,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=1.00,
        )
        hs = HyperstackAdapter(api_key="hs-test")
        with self.assertRaises(UnsupportedGpuError):
            hs.estimate_cost(WORKLOAD_PRESETS["workload_b_ltx_30s"], bad_offer, now=now)
        md = ModalAdapter()
        with self.assertRaises(UnsupportedGpuError):
            md.list_gpu_capacity(gpu_types=("NONEXISTENT_MODAL_GPU",), fetched_at=now)

    def test_05_insufficient_vram_raises_insufficient_vram_error(self) -> None:
        now = 1_760_000_000.0
        l40_offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="L40",
            flavor_name="n3-L40x1",
            region="CANADA-1",
            vram_gb=48,
            cpu_cores=28,
            ram_gb=58,
            root_disk_gb=100,
            ephemeral_disk_gb=725,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=1.00,
        )
        hs = HyperstackAdapter(api_key="hs-test")
        with self.assertRaises(InsufficientVramError):
            hs.estimate_cost(WORKLOAD_PRESETS["workload_b_ltx_30s"], l40_offer, now=now)

    def test_06_region_mismatch_raises_region_mismatch_error(self) -> None:
        now = 1_760_000_000.0
        offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="APAC-TOKYO-9",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=1.35,
        )
        hs = HyperstackAdapter(api_key="hs-test")
        with self.assertRaises(RegionMismatchError):
            hs.estimate_cost(WORKLOAD_PRESETS["workload_b_ltx_30s"], offer, now=now)

    def test_07_price_lookup_failure_raises_price_lookup_error(self) -> None:
        now = 1_760_000_000.0
        unpriced_offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=None,
        )
        hs = HyperstackAdapter(api_key="hs-test")
        with self.assertRaises(PriceLookupError):
            hs.estimate_cost(WORKLOAD_PRESETS["workload_b_ltx_30s"], unpriced_offer, now=now)

    def test_08_cost_estimate_exceeding_budget_raises_budget_exceeded_error(self) -> None:
        now = 1_760_000_000.0
        offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="H100-80G-PCIe",
            flavor_name="n3-H100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=180,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=2.50,
        )
        hs = HyperstackAdapter(api_key="hs-test")
        with self.assertRaises(BudgetExceededError):
            hs.estimate_cost(WORKLOAD_PRESETS["workload_c_combined_p12_p14"], offer, now=now)

    def test_09_missing_approval_blocks_live_submit(self) -> None:
        now = 1_760_000_000.0
        offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=1.35,
        )
        hs = HyperstackAdapter(api_key="hs-test", clock=lambda: now)
        with self.assertRaises(ApprovalRequiredError):
            hs.submit_job(
                WORKLOAD_PRESETS["workload_c_j5_minimised_p12_p14"],
                offer,
                vm_name="ee-test-vm",
                idempotency_key="idem-unapproved-1",
                dry_run=False,
                approval=None,
            )

    def test_10_dry_run_selection_and_submit_without_network(self) -> None:
        now = 1_760_000_000.0
        hs = HyperstackAdapter(api_key="hs-offline", clock=lambda: now)
        md = ModalAdapter(token_id="md-offline", token_secret="md-secret", clock=lambda: now)
        selector = ProviderSelector({"hyperstack": hs, "modal": md})

        hs_a100 = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=1.35,
        )
        md_offers = md.list_gpu_capacity(gpu_types=("H100", "A100-80GB"), fetched_at=now)
        res_short = selector.select(
            WORKLOAD_PRESETS["workload_d_short_calibration"],
            [hs_a100, *md_offers],
            now=now,
        )
        self.assertEqual(res_short["status"], "ok")
        top = res_short["candidates"][0]
        self.assertEqual(top.offer.provider, "modal")
        self.assertEqual(top.cost.net_after_credits_usd, 0.0)

        dry = hs.submit_job(
            WORKLOAD_PRESETS["workload_c_j5_minimised_p12_p14"],
            hs_a100,
            vm_name="ee-dry-vm",
            idempotency_key="idem-dry-1",
            dry_run=True,
        )
        self.assertEqual(dry["mode"], "dry_run")
        self.assertEqual(dry["provider"], "hyperstack")

    def test_11_provisioning_timeout_reconciles_without_duplicate_create(self) -> None:
        now = 1_760_000_000.0
        calls: list[tuple[str, str]] = []
        get_count = 0

        def fake_transport(
            method: str, url: str, body: bytes | None, headers: dict[str, str], timeout: int
        ) -> tuple[int, str, dict[str, str]]:
            nonlocal get_count
            path = "/" + url.split("/v1/", 1)[1]
            calls.append((method, path))
            if method == "GET" and path == "/core/virtual-machines":
                get_count += 1
                if get_count == 1:
                    return 200, json.dumps({"instances": []}), {}
                return (
                    200,
                    json.dumps(
                        {
                            "instances": [
                                {
                                    "id": 98765,
                                    "name": "ee-idem-timeout-1",
                                    "status": "CREATING",
                                    "flavor": {"gpu": "A100-80G-PCIe"},
                                }
                            ]
                        }
                    ),
                    {},
                )
            if method == "POST" and path == "/core/virtual-machines":
                return 504, "Gateway Timeout", {}
            raise AssertionError(f"Unexpected call {method} {path}")

        hs = HyperstackAdapter(api_key="hs-key", transport=fake_transport, clock=lambda: now)
        offer = GpuCapacityOffer(
            provider="hyperstack",
            gpu_type="A100-80G-PCIe",
            flavor_name="n3-A100x1",
            region="CANADA-1",
            vram_gb=80,
            cpu_cores=28,
            ram_gb=120,
            root_disk_gb=100,
            ephemeral_disk_gb=750,
            gpu_count=1,
            available=True,
            availability_tier="HIGH",
            fetched_at=now,
            price_per_hour_usd=1.35,
        )
        gate = ApprovalGate(
            or22_creator_word_ref="creator-msg-1",
            or23_plan_path="docs/providers/PROVIDER_DECISION.md",
            or24_opus_verdict_ref="opus-verdict-1",
            or34_fable_audit_ref="fable-audit-1",
            provider_enabled=True,
        )
        out = hs.submit_job(
            WORKLOAD_PRESETS["workload_c_j5_minimised_p12_p14"],
            offer,
            vm_name="ee-idem-timeout-1",
            idempotency_key="idem-timeout-1",
            dry_run=False,
            approval=gate,
        )
        self.assertEqual(out["mode"], "adopted_after_timeout")
        self.assertEqual(out["resource_id"], "98765")
        self.assertEqual(
            calls,
            [
                ("GET", "/core/virtual-machines"),
                ("POST", "/core/virtual-machines"),
                ("GET", "/core/virtual-machines"),
            ],
        )

        with self.assertRaises(DuplicateRequestError):
            hs.submit_job(
                WORKLOAD_PRESETS["workload_c_j5_minimised_p12_p14"],
                offer,
                vm_name="ee-idem-timeout-1",
                idempotency_key="idem-timeout-1",
                dry_run=False,
                approval=gate,
            )

    def test_12_provider_rate_limiting_raises_rate_limit_error(self) -> None:
        def fake_429(
            method: str, url: str, body: bytes | None, headers: dict[str, str], timeout: int
        ) -> tuple[int, str, dict[str, str]]:
            return 429, "Too Many Requests", {"Retry-After": "45"}

        hs = HyperstackAdapter(api_key="hs-key", transport=fake_429)
        with self.assertRaises(RateLimitError) as ctx:
            hs.list_gpu_capacity()
        self.assertEqual(ctx.exception.status, 429)
        self.assertEqual(ctx.exception.retry_after_s, 45)

    def test_13_authentication_failure_redacts_secrets(self) -> None:
        secret_key = "sk-live-SUPER-SECRET-TOKEN-99887766"
        err = AuthenticationError(
            f"Auth failed with header api_key: {secret_key} and Bearer {secret_key}",
            status=401,
            secrets=(secret_key,),
        )
        msg = str(err)
        self.assertNotIn(secret_key, msg)
        self.assertIn("[REDACTED]", msg)
        self.assertEqual(
            redact_secrets("token=rpa_1234567890ABCDEF", ()),
            "token=[REDACTED]",
        )

    def test_14_provider_lifecycle_mapping_and_shutoff_billing_trap(self) -> None:
        hs = HyperstackAdapter(api_key="hs-key")
        view = hs.normalize_status(
            {
                "id": 4242,
                "name": "ee-vm-shutoff",
                "status": "SHUTOFF",
                "flavor": {"name": "n3-A100x1", "gpu": "A100-80G-PCIe", "disk": 100},
            }
        )
        self.assertEqual(view.provider_state, "SHUTOFF")
        self.assertEqual(view.normalized_state, "FAILED")
        self.assertTrue(view.billing_active)
        self.assertIn("SHUTOFF", view.billing_trap_warning)
        self.assertIn("100%", view.billing_trap_warning)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = jobs.Job.create(
                root,
                "j-hs-4242",
                kind="combined_p12_p14",
                provider="hyperstack",
                now=1000.0,
            )
            moved = sync_job_from_view(job, view, now=1010.0)
            self.assertEqual(moved, "FAILED")
            self.assertEqual(job.state["resource"], "4242")
            self.assertIn("SHUTOFF", job.state["reason"])
            self.assertTrue(any("SHUTOFF" in e["text"] for e in job.events()))

    def test_15_cancellation_mapping_blocks_hyperstack_stop_and_allows_hibernate_delete(self) -> None:
        called_paths: list[tuple[str, str]] = []

        def fake_cancel_transport(
            method: str, url: str, body: bytes | None, headers: dict[str, str], timeout: int
        ) -> tuple[int, str, dict[str, str]]:
            path = "/" + url.split("/v1/", 1)[1]
            called_paths.append((method, path))
            return 200, json.dumps({"status": True}), {}

        hs = HyperstackAdapter(api_key="hs-key", transport=fake_cancel_transport)
        with self.assertRaises(ProviderError) as ctx:
            hs.cancel_job("4242", mode="stop")
        self.assertIn("SHUTOFF", str(ctx.exception))

        v_hib = hs.cancel_job("4242", mode="hibernate")
        self.assertEqual(v_hib.provider_state, "HIBERNATING")
        self.assertEqual(v_hib.normalized_state, "STOPPING")

        v_del = hs.cancel_job("4242", mode="delete")
        self.assertEqual(v_del.provider_state, "DELETED")
        self.assertEqual(v_del.normalized_state, "CANCELLED")
        self.assertFalse(v_del.billing_active)

        md = ModalAdapter()
        md_cancel = md.cancel_job("fc-modal-123")
        self.assertEqual(md_cancel.normalized_state, "CANCELLED")
        self.assertFalse(md_cancel.billing_active)

    def test_16_artifact_persistence_and_hash_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "outputs"
            out_dir.mkdir()
            clip_file = out_dir / "clip_01.mp4"
            payload = b"verified-video-bytes-2026" * 64
            clip_file.write_bytes(payload)
            sha = hashlib.sha256(payload).hexdigest()

            job = jobs.Job.create(
                root,
                "j-store-test",
                kind="ltx_video",
                provider="modal",
                now=2000.0,
            )
            row = job.record_output(clip_file, now=2010.0)
            self.assertEqual(row['sha256'], sha)
            self.assertEqual(len(job.unstored_outputs()), 1)

            problems = verify_and_mark_stored(
                job, out_dir, "hf://vano1919/tmr-artifacts/clip_01.mp4", now=2020.0
            )
            self.assertEqual(problems, [])
            self.assertEqual(job.unstored_outputs(), [])

    def test_17_recovery_from_partially_completed_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = jobs.Job.create(
                root,
                "j-partial-fail",
                kind="ltx_video",
                provider="hyperstack",
                now=3000.0,
            )
            job.attach("vm-777", now=3005.0, provider_state="ACTIVE")
            job.move("PROVISIONING", "created", now=3005.0)
            job.move("STARTING", "booting", now=3010.0)
            job.move("RUNNING", "generating", now=3020.0)
            shot1 = root / "shot_01.mp4"
            shot1.write_bytes(b"partial-clip-bytes" * 32)
            job.record_output(shot1, now=3050.0)

            md = ModalAdapter()
            failed_view = md.normalize_status({"call_id": "vm-777", "status": "FAILURE"})
            new_state = sync_job_from_view(job, failed_view, now=3060.0)
            self.assertEqual(new_state, "RECOVERY_REQUIRED")
            self.assertEqual(job.state["state"], "RECOVERY_REQUIRED")

    def test_18_existing_runpod_regression_and_spend_caps_untouched(self) -> None:
        caps_path = Path("config/spend_caps.json")
        caps = json.loads(caps_path.read_text(encoding="utf-8"))
        self.assertIn("runpod", caps)
        self.assertNotIn("hyperstack", caps)
        self.assertNotIn("modal", caps)

        fake_pod = {
            "id": "pod-reg-1",
            "name": "ee-reg-1",
            "desiredStatus": "EXITED",
            "costPerHr": 1.39,
            "containerDiskInGb": 40,
            "volumeInGb": 60,
            "gpuCount": 1,
            "uptimeSeconds": 0,
            "machine": {"gpuDisplayName": "A100 PCIe", "location": "CA"},
        }
        normed = runpod.norm(fake_pod)
        self.assertEqual(normed["id"], "pod-reg-1")
        self.assertEqual(normed["desiredStatus"], "EXITED")
        self.assertGreater(runpod.disk_per_hour(normed, running=False), 0.0)


if __name__ == "__main__":
    unittest.main()


def test_proposed_provider_caps_come_from_config_and_stay_disabled():
    """The proposed caps are read from config/provider_caps_proposed.json and every provider is disabled (D-56)."""
    import json as _json
    from pathlib import Path as _Path

    from explainer_engine.cloud.providers.base import PROPOSED_PROVIDER_CAPS

    raw = _json.loads((_Path(__file__).resolve().parents[2] / "config" / "provider_caps_proposed.json").read_text("utf-8"))
    assert set(PROPOSED_PROVIDER_CAPS) == {k for k in raw if not k.startswith("_")}
    assert all(v["enabled"] is False and v["approved_by"] is None for v in PROPOSED_PROVIDER_CAPS.values())
