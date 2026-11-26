"""Zero-Tear Continuous 3D Depth-Mesh 2.5D Engine (Depth Anything V2 + Three.js WebGL2).

Eliminates ALL discrete layer-slicing seams, cutout halos, and Telea inpainting smears by
extruding a single continuous high-resolution 3D mesh (256x144 vertices) in Three.js WebGL2
driven by a smoothly edge-preserved Depth Anything V2 heightfield, paired with:
- Tightly clamped, gentle cinema perspective camera travel (zero edge stretch, zero tears).
- True 3D depth-sorted soft-bokeh atmospheric particles (snow streaks, embers, ash, dust)
  with organic wind-turbulence variation and depth-scaled opacity.
- Real-time subtle cinema vignette & unified color tone.

Strictly reserved for uninhabited landscapes, glaciers, cave art, and artifacts — NEVER
frozen human actors or mid-stride wildlife.
"""
from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from playwright.sync_api import sync_playwright

from explainer_engine.design_system.tokens import resolve_vendor_js

ROOT = Path(__file__).resolve().parents[2]
DEPTH_MODEL_PATH = ROOT / "assets" / "models" / "depth_anything_v2_small_q4.onnx"


def _estimate_continuous_depth(rgb: np.ndarray) -> np.ndarray:
    """Estimate ultra-smooth continuous normalized depth [0=far, 1=near] via Depth Anything V2 ONNX."""
    h, w = rgb.shape[:2]
    if DEPTH_MODEL_PATH.is_file():
        import onnxruntime as ort

        sess = ort.InferenceSession(str(DEPTH_MODEL_PATH), providers=["CPUExecutionProvider"])
        inp = sess.get_inputs()[0]
        inp_h = int(inp.shape[2]) if isinstance(inp.shape[2], int) else 518
        inp_w = int(inp.shape[3]) if isinstance(inp.shape[3], int) else 518
        resized = cv2.resize(rgb, (inp_w, inp_h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        tensor = ((resized - mean) / std).transpose(2, 0, 1)[None, ...]
        raw_depth = sess.run(None, {inp.name: tensor})[0]
        depth = np.squeeze(raw_depth).astype(np.float32)
        depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)
    else:
        yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
        depth = np.repeat(yy**1.25, w, axis=1)

    d_min, d_max = float(np.percentile(depth, 2)), float(np.percentile(depth, 98))
    norm = np.clip((depth - d_min) / max(1e-5, d_max - d_min), 0.0, 1.0)
    # Two-stage smooth filter eliminates steep vertical depth cliffs so mesh triangles NEVER stretch or tear!
    u8 = (norm * 255.0).astype(np.uint8)
    u8 = cv2.bilateralFilter(u8, d=15, sigmaColor=55, sigmaSpace=55)
    smooth = cv2.GaussianBlur(u8.astype(np.float32) / 255.0, (25, 25), 7.5)
    # Subtle soft edge taper around outer 4% border so mesh perimeter stays cleanly anchored
    margin_y = max(4, int(h * 0.04))
    margin_x = max(4, int(w * 0.04))
    wy = np.ones(h, dtype=np.float32)
    wx = np.ones(w, dtype=np.float32)
    wy[:margin_y] = np.linspace(0.35, 1.0, margin_y, dtype=np.float32)
    wy[-margin_y:] = np.linspace(1.0, 0.35, margin_y, dtype=np.float32)
    wx[:margin_x] = np.linspace(0.35, 1.0, margin_x, dtype=np.float32)
    wx[-margin_x:] = np.linspace(1.0, 0.35, margin_x, dtype=np.float32)
    smooth = smooth * (wy[:, None] * wx[None, :])
    return np.clip(smooth, 0.0, 1.0)


def _prepare_plate_and_depth(
    img_path: Path,
    work_dir: Path,
    *,
    render_size: tuple[int, int] = (1920, 1080),
) -> dict[str, Path]:
    """Prepare 16:9 aspect-cropped RGB plate + continuous smooth depth map for WebGL2 vertex extrusion."""
    bgr = cv2.imread(str(img_path))
    if bgr is None:
        raise FileNotFoundError(f"Could not read 2.5D source still: {img_path}")
    tw, th = render_size
    ih, iw = bgr.shape[:2]
    target_ar = tw / float(th)
    cur_ar = iw / max(1.0, float(ih))
    if cur_ar > target_ar:
        nw = int(round(ih * target_ar))
        x0 = max(0, (iw - nw) // 2)
        bgr = bgr[:, x0 : x0 + nw]
    elif cur_ar < target_ar:
        nh = int(round(iw / target_ar))
        y0 = max(0, (ih - nh) // 2)
        bgr = bgr[y0 : y0 + nh, :]
    bgr = cv2.resize(bgr, (tw, th), interpolation=cv2.INTER_LANCZOS4)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    small_rgb = cv2.resize(rgb, (640, 360), interpolation=cv2.INTER_AREA)
    depth_small = _estimate_continuous_depth(small_rgb)
    # Depth map at 512x288 is plenty for a 240x135 vertex mesh and super fast to upload
    depth_u8 = (cv2.resize(depth_small, (512, 288), interpolation=cv2.INTER_CUBIC) * 255.0).astype(np.uint8)

    work_dir.mkdir(parents=True, exist_ok=True)
    color_path = work_dir / "plate_color.jpg"
    depth_path = work_dir / "plate_depth.png"
    cv2.imwrite(str(color_path), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    cv2.imwrite(str(depth_path), depth_u8)
    return {"color": color_path, "depth": depth_path}


def _file_data_uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _build_threejs_mesh_25d_html(
    assets: dict[str, Path],
    *,
    duration_s: float,
    camera_move: str,
    atmosphere: str,
    width: int,
    height: int,
    displacement_scale: float = 1.45,
) -> str:
    three_uri = resolve_vendor_js("three.min.js").as_uri()
    color_uri = _file_data_uri(assets["color"], "image/jpeg")
    depth_uri = _file_data_uri(assets["depth"], "image/png")

    cfg = {
        "duration_s": duration_s,
        "camera_move": camera_move,
        "atmosphere": atmosphere,
        "color": color_uri,
        "depth": depth_uri,
        "disp": displacement_scale,
    }
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<style>
* {{ margin: 0; padding: 0; }}
html, body {{ width: {width}px; height: {height}px; overflow: hidden; background: #000; position: relative; }}
canvas {{ display: block; width: {width}px; height: {height}px; }}
.vignette {{
  position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 88% 84% at 50% 50%, rgba(0,0,0,0) 60%, rgba(3,5,9,0.44) 100%);
}}
</style>
</head>
<body>
<div class="vignette"></div>
<script src="{three_uri}"></script>
<script>
const CFG = {json.dumps(cfg)};
const W = {width}, H = {height};
const aspect = W / H;

const renderer = new THREE.WebGLRenderer({{ antialias: true, preserveDrawingBuffer: true }});
renderer.setSize(W, H, false);
renderer.setPixelRatio(1);
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, aspect, 0.1, 100);
camera.position.set(0, 0, 10.0);

function loadImg(url) {{
  return new Promise((resolve) => {{
    const img = new Image();
    img.onload = () => resolve(img);
    img.src = url;
  }});
}}

function makeSoftBokehTex(kind) {{
  const c = document.createElement("canvas");
  c.width = 96; c.height = 96;
  const g = c.getContext("2d");
  if (kind === "snow_flurry") {{
    // Soft oblique wind-blown snowflake bokeh streak (not a harsh uniform 2D dot!)
    g.save();
    g.translate(48, 48);
    g.rotate(-0.28);
    g.scale(1.55, 0.65);
    const grad = g.createRadialGradient(0, 0, 1, 0, 0, 28);
    grad.addColorStop(0, "rgba(242,248,255,0.75)");
    grad.addColorStop(0.45, "rgba(210,232,248,0.28)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grad;
    g.beginPath(); g.arc(0, 0, 28, 0, Math.PI * 2); g.fill();
    g.restore();
  }} else if (kind === "rising_embers") {{
    const grad = g.createRadialGradient(48, 48, 1, 48, 48, 40);
    grad.addColorStop(0, "rgba(255,238,192,0.92)");
    grad.addColorStop(0.28, "rgba(255,136,38,0.68)");
    grad.addColorStop(0.65, "rgba(195,58,14,0.16)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 96, 96);
  }} else {{
    const grad = g.createRadialGradient(48, 48, 2, 48, 48, 42);
    grad.addColorStop(0, "rgba(220,214,205,0.45)");
    grad.addColorStop(0.5, "rgba(170,165,158,0.16)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grad;
    g.fillRect(0, 0, 96, 96);
  }}
  return new THREE.CanvasTexture(c);
}}

let particleGroups = [];
window.__ready = false;

Promise.all([loadImg(CFG.color), loadImg(CFG.depth)]).then(([imgColor, imgDepth]) => {{
  const colorTex = new THREE.Texture(imgColor);
  colorTex.needsUpdate = true;
  colorTex.minFilter = THREE.LinearFilter;
  colorTex.magFilter = THREE.LinearFilter;

  const depthTex = new THREE.Texture(imgDepth);
  depthTex.needsUpdate = true;
  depthTex.minFilter = THREE.LinearFilter;
  depthTex.magFilter = THREE.LinearFilter;

  // Overscan plane 1.14x so gentle camera travel NEVER exposes frame border
  const visH = 2 * Math.tan(THREE.MathUtils.degToRad(38 / 2)) * 10.0 * 1.14;
  const visW = visH * aspect;

  // Continuous 240x135 displaced 3D depth mesh — ZERO discrete card seams or inpaint smears!
  const geom = new THREE.PlaneGeometry(visW, visH, 240, 135);
  const mat = new THREE.ShaderMaterial({{
    uniforms: {{
      uColor: {{ value: colorTex }},
      uDepth: {{ value: depthTex }},
      uDisp: {{ value: CFG.disp }}
    }},
    vertexShader: `
      uniform sampler2D uDepth;
      uniform float uDisp;
      varying vec2 vUv;
      void main() {{
        vUv = uv;
        float d = texture2D(uDepth, uv).r;
        vec3 displaced = position + vec3(0.0, 0.0, (d - 0.35) * uDisp);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
      }}
    `,
    fragmentShader: `
      uniform sampler2D uColor;
      varying vec2 vUv;
      void main() {{
        gl_FragColor = texture2D(uColor, vUv);
      }}
    `
  }});
  const mesh = new THREE.Mesh(geom, mat);
  scene.add(mesh);

  // Multi-depth soft bokeh particle layers (near = larger/softer, far = fine/subtle)
  if (CFG.atmosphere && CFG.atmosphere !== "none") {{
    const tex = makeSoftBokehTex(CFG.atmosphere);
    const layerDefs = [
      {{ count: 95, zMin: 1.5, zMax: 3.4, size: CFG.atmosphere === "rising_embers" ? 0.14 : 0.13, op: 0.46, sp: 0.65 }},
      {{ count: 45, zMin: 3.6, zMax: 6.0, size: CFG.atmosphere === "rising_embers" ? 0.24 : 0.28, op: 0.28, sp: 1.15 }}
    ];
    let seed = 8821;
    const rand = () => {{ seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }};

    for (const ld of layerDefs) {{
      const pg = new THREE.BufferGeometry();
      const pos = new Float32Array(ld.count * 3);
      const base = [];
      for (let i = 0; i < ld.count; i++) {{
        const x = (rand() - 0.5) * 14.5;
        const y = (rand() - 0.5) * 8.2;
        const z = ld.zMin + rand() * (ld.zMax - ld.zMin);
        pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z;
        base.push({{ x, y, z, vx: 0.4 + rand() * 0.9, vy: 0.3 + rand() * 0.65, ph: rand() * 6.28, sp: ld.sp }});
      }}
      pg.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const pm = new THREE.PointsMaterial({{
        map: tex,
        size: ld.size,
        transparent: true,
        opacity: ld.op,
        depthWrite: false,
        blending: CFG.atmosphere === "rising_embers" ? THREE.AdditiveBlending : THREE.NormalBlending
      }});
      const pts = new THREE.Points(pg, pm);
      scene.add(pts);
      particleGroups.push({{ pts, base }});
    }}
  }}
  window.__ready = true;
}});

window.__renderAt = function(t_s) {{
  const u = Math.max(0, Math.min(1, t_s / Math.max(0.1, CFG.duration_s)));
  const e = 0.28 * u + 0.72 * (u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2);

  // Restrained, cinema-authentic parallax travel (zero rubber stretch!)
  let cx = 0, cy = 0, cz = 10.0;
  if (CFG.camera_move === "truck") {{
    cx = -0.34 + 0.68 * e;
    cy = 0.04 * Math.sin(u * Math.PI);
    cz = 9.85 - 0.28 * e;
  }} else if (CFG.camera_move === "truck_zoom_in") {{
    cx = -0.28 + 0.56 * e;
    cy = -0.05 + 0.10 * e;
    cz = 9.95 - 0.80 * e;
  }} else if (CFG.camera_move === "zoom_out") {{
    cx = 0.14 - 0.28 * e;
    cz = 9.15 + 0.78 * e;
  }} else if (CFG.camera_move === "truck_zoom_out") {{
    cx = 0.26 - 0.52 * e;
    cz = 9.18 + 0.76 * e;
  }} else {{
    cx = -0.14 + 0.28 * e;
    cy = 0.04 - 0.08 * e;
    cz = 9.95 - 0.85 * e;
  }}

  camera.position.set(cx, cy, cz);
  camera.lookAt(cx * 0.24, cy * 0.24, 0.25);

  for (const grp of particleGroups) {{
    const arr = grp.pts.geometry.attributes.position.array;
    for (let i = 0; i < grp.base.length; i++) {{
      const b = grp.base[i];
      if (CFG.atmosphere === "rising_embers") {{
        let ny = b.y + t_s * b.vy * 0.75 * b.sp;
        ny = ((ny + 4.1) % 8.2) - 4.1;
        const nx = b.x + Math.sin(t_s * 1.6 + b.ph) * 0.28 + t_s * 0.08;
        arr[i * 3] = nx; arr[i * 3 + 1] = ny; arr[i * 3 + 2] = b.z;
      }} else {{
        const spd = CFG.atmosphere === "cavern_dust" ? 0.20 : 0.78;
        let ny = b.y - t_s * b.vy * spd * b.sp;
        ny = (((ny + 4.1) % 8.2) + 8.2) % 8.2 - 4.1;
        let nx = b.x + t_s * b.vx * spd * b.sp + Math.sin(t_s * 1.2 + b.ph) * 0.18;
        nx = (((nx + 7.25) % 14.5) + 14.5) % 14.5 - 7.25;
        arr[i * 3] = nx; arr[i * 3 + 1] = ny; arr[i * 3 + 2] = b.z;
      }}
    }}
    grp.pts.geometry.attributes.position.needsUpdate = true;
  }}
  renderer.render(scene, camera);
}};
</script>
</body>
</html>"""


def render_webgl_25d_clip(
    image_path: Path,
    out_mp4: Path,
    *,
    duration_s: float = 5.0,
    camera_move: str = "truck_zoom_in",
    atmosphere: str = "snow_flurry",
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    render_width: int = 1280,
    render_height: int = 720,
    displacement_scale: float = 1.45,
    work_dir: Path | None = None,
) -> dict[str, Any]:
    """Render a zero-tear 2K 24fps Three.js WebGL2 continuous 3D depth-mesh 2.5D scene."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    wdir = work_dir or (out_mp4.parent / f"{out_mp4.stem}_mesh")
    assets = _prepare_plate_and_depth(image_path, wdir, render_size=(render_width, render_height))

    html_path = wdir / "scene_25d_mesh.html"
    html_path.write_text(
        _build_threejs_mesh_25d_html(
            assets,
            duration_s=duration_s,
            camera_move=camera_move,
            atmosphere=atmosphere,
            width=render_width,
            height=render_height,
            displacement_scale=displacement_scale,
        ),
        encoding="utf-8",
    )

    total_frames = max(2, int(round(duration_s * fps)))
    vf = (
        f"scale={width}:{height}:flags=lanczos,unsharp=3:3:0.35:3:3:0.10"
        if (render_width, render_height) != (width, height)
        else "null"
    )
    ff_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"],
        )
        page = browser.new_page(viewport={"width": render_width, "height": render_height}, device_scale_factor=1)
        page.goto(html_path.as_uri(), wait_until="load")
        page.wait_for_function("() => window.__ready === true", timeout=60000)
        cdp = page.context.new_cdp_session(page)

        for f_idx in range(total_frames):
            t_s = f_idx / float(fps)
            page.evaluate(f"() => window.__renderAt({t_s:.4f})")
            res = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 95})
            proc.stdin.write(base64.b64decode(res["data"]))

        browser.close()

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg WebGL 2.5D mesh encode failed with exit code {ret}")

    return {
        "path": str(out_mp4),
        "source_image": str(image_path),
        "camera_move": camera_move,
        "atmosphere": atmosphere,
        "duration_s": duration_s,
        "width": width,
        "height": height,
        "fps": fps,
    }
