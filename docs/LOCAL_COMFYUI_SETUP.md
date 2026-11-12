# Local ComfyUI Setup & Model Verification Guide (`LOCAL_COMFYUI_SETUP.md`)

> **Route-scoped since D-116 (2026-11-06); created 2026-11-09 by D-123 (Local Hybrid B -> C Rebuild).**
> **Canonical Registry:** `config/local_models.json`
> **Preflight Module:** `explainer_engine/production/local_preflight.py`

## 1. Local-Only Default Policy (`EXPLAINER_LOCAL_ONLY=1`)

By default, Explainer Engine executes all Stage 2 keyframe and Stage 3 video/2.5D renders locally against a running ComfyUI server (`http://127.0.0.1:8188`). Outbound requests to non-localhost inference endpoints are blocked in `explainer_engine/vault.py` unless `--allow-paid-cloud` (`EXPLAINER_LOCAL_ONLY=0`) is explicitly passed.

---

## 2. Environment Variables (`.env` Names Only)

Set the following variable names in your local `.env` (never commit `.env` or model weights to Git):

| Variable Name | Purpose | Default Value |
| :--- | :--- | :--- |
| `EXPLAINER_LOCAL_ONLY` | Enforces localhost-only ComfyUI execution and blocks paid cloud endpoints | `"1"` |
| `COMFY_SERVER_ADDRESS` | Local ComfyUI host and port | `"127.0.0.1:8188"` |
| `COMFYUI_API_ENDPOINT` | Full HTTP URL for local ComfyUI API calls | `"http://127.0.0.1:8188"` |
| `COMFYUI_MODELS_DIR` | Local filesystem path to ComfyUI `models/` directory | `<repo_root>/models` |
| `EXPLAINER_ENGINE_ENV` | Execution profile (`local_default`, `ci_dry_run`, `opt_in_cloud`) | `"local_default"` |
| `HF_TOKEN` / `HUGGING_FACE_HUB_TOKEN` | Optional Hugging Face token for one-time local weight downloads only | `""` |

---

## 3. Required Local Model Weights (`$COMFYUI_MODELS_DIR/`)

All weights reside outside Git under `$COMFYUI_MODELS_DIR/` and are mapped in `config/local_models.json`:

1. **Stage 2 Keyframe Models (Benchmarked in `T-ABL-01` & `T-ABL-02`):**
   - `diffusion_models/qwen_image_edit_2511_fp8_e4m3fn.safetensors` (`Qwen/Qwen-Image-Edit-2511`, Apache-2.0)
   - `loras/qwen-image-edit-2511-multiple-angles-lora.safetensors` (`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`, `licence_status: "verify_card"`)
   - `diffusion_models/qwen_image_2_1_bf16.safetensors` + `loras/xworld_v2.safetensors` (`qwen_image_2_1_xworld_v2`, `licence_status: "commercial_ok"`)
2. **Stage 3 Video Models (Benchmarked in `T-ABL-03` & `T-ABL-04`):**
   - `diffusion_models/Wan2.2-Fun-5B-InP.safetensors` (`alibaba-pai/Wan2.2-Fun-5B-InP`, Apache-2.0, primary default candidate)
   - `vae/Wan2.2_VAE.safetensors` & `text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors`
   - `diffusion_models/Wan2.2-Fun-5B-Control.safetensors` (`alibaba-pai/Wan2.2-Fun-5B-Control`, Apache-2.0, selective control fallback)
   - Optional 14B escalation tier: `wan2.2_fun_inp_high_noise_14B_fp8_scaled.safetensors` & `low_noise_14B_fp8_scaled.safetensors`
3. **Stage 3 Deterministic 2.5D Parallax:**
   - `depthanything/depth_anything_v2_vitb_fp16.safetensors` (`depth-anything/Depth-Anything-V2-Base`, Apache-2.0 `commercial_ok`). *Note:* `Depth-Anything-V2-Large` (`vitl`) is CC-BY-NC-4.0 (`non_commercial_research`) and triggers a preflight warning if selected for commercial runs.

---

## 4. Required ComfyUI Nodes

`local_preflight.py` queries `GET http://127.0.0.1:8188/object_info` to verify:
- **Core Nodes:** `WanFunInpaintToVideo`, `WanImageToVideo`, `Wan22FunControlToVideo`, `TextEncodeQwenImageEditPlus`.
- **Custom Nodes:**
  - `jtydhr88/ComfyUI-qwenmultiangle` (`QwenMultiangleCameraNode`)
  - `akatz-ai/ComfyUI-Depthflow-Nodes` (`DepthflowPresetDolly`, `DepthflowPresetOrbital`, `DepthflowPresetZoom`, `DepthflowPresetHorizontal`, `DepthflowPresetVertical`) — automatically falls back to `explainer_engine/production/parallax.py` if absent.
  - `Fannovel16/comfyui_controlnet_aux` (`DWPreprocessor`, `CannyEdgePreprocessor`, `DepthAnythingV2Preprocessor`).

---

## 5. Verification Commands

```sh
# Check local ComfyUI reachability, custom nodes, .env keys (boolean names only), and model files:
python -m explainer_engine.production --check-local --config config/local_models.json

# Run Phase 1 compatibility & ablation checks (dry-run or live local ComfyUI):
python scripts/run_phase1_ablations.py --dry-run
```
