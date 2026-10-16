import base64, json, os, sys, time, urllib.request
MODEL = "gemini-3.1-flash-image"
KEY = os.environ["GEMINI_API_KEY"]
LEDGER = "ledger.jsonl"
PRICE = 0.067

def gen(name, prompt, refs=(), aspect="1:1"):
    parts = [{"text": prompt}]
    for r in refs:
        parts.append({"inline_data": {"mime_type": "image/jpeg" if r.endswith(".jpg") else "image/png",
                                      "data": base64.b64encode(open(r, "rb").read()).decode()}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        d = json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:
        print(name, "HTTP", e.code, e.read()[:400]); return None
    img = None
    for c in d.get("candidates", []):
        for p in c.get("content", {}).get("parts", []):
            x = p.get("inlineData") or p.get("inline_data")
            if x: img = base64.b64decode(x["data"])
    ok = img is not None
    with open(LEDGER, "a") as f:
        f.write(json.dumps({"name": name, "model": MODEL, "ok": ok, "est_usd": PRICE if ok else 0,
                            "secs": round(time.time() - t, 1), "refs": list(refs), "prompt": prompt}) + "\n")
    if not ok:
        print(name, "no image", json.dumps(d)[:400]); return None
    open(f"{name}.png", "wb").write(img)
    print(name, "ok", len(img))
    return f"{name}.png"

if __name__ == "__main__":
    name, prompt, *refs = sys.argv[1:]
    gen(name, prompt, refs)
