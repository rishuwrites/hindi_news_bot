import glob, io, os, re, time, html as _html, requests, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import *

def find_font():
    for pat in ["/usr/share/fonts/**/NotoSansDevanagari-Bold.ttf", "/usr/share/fonts/**/NotoSansDevanagari*Bold*.ttf",
                "/usr/share/fonts/**/Mukta*Bold*.ttf", "/usr/share/fonts/**/*Devanagari*.ttf"]:
        f = glob.glob(pat, recursive=True)
        if f: return f[0]
    raise SystemExit("No Devanagari font found (apt install fonts-noto-core)")

def font(size):
    return ImageFont.truetype(find_font(), size, layout_engine=ImageFont.Layout.RAQM)

def wrap(draw, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]

def caption_png(text, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = font(78); ls = wrap(d, text, f, W - 160); lh = 120
    y0 = 1180
    d.rounded_rectangle((50, y0 - 30, W - 50, y0 + lh * len(ls) + 10), 40, fill=(0, 0, 0, 150))
    for i, l in enumerate(ls):
        x = (W - d.textlength(l, font=f)) / 2
        d.text((x, y0 + i * lh), l, font=f, fill=(255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0))
    im.save(path)

def header_png(headline, path):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((0, 150, W, 330), fill=(200, 0, 20, 235))
    d.rectangle((0, 330, W, 520), fill=(10, 10, 20, 215))
    d.text((50, 175), "ब्रेकिंग न्यूज़", font=font(64), fill=(255, 255, 255))
    f = font(76); ls = wrap(d, headline, f, W - 100)[:2]
    for i, l in enumerate(ls):
        d.text((50, 345 + i * 95), l, font=f, fill=(255, 215, 0))
    d.text((50, 1700), CHANNEL_NAME, font=font(60), fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    im.save(path)

UA = {"User-Agent": "DeshKiNabzBot/1.0 (news shorts automation; github actions)"}
_last = [0.0]

def _clean(t):
    return _html.unescape(re.sub("<[^>]+>", "", t or "")).strip()

def _fetch(url):
    """Polite download (Wikimedia rate-limits hard): spacing + Retry-After handling."""
    for _ in range(4):
        wait = 1.0 - (time.time() - _last[0])
        if wait > 0: time.sleep(wait)
        r = requests.get(url, headers=UA, timeout=60); _last[0] = time.time()
        if r.status_code == 429:
            d = min(int(r.headers.get("Retry-After", 5) or 5), 20); print(f"  429, waiting {d}s"); time.sleep(d); continue
        r.raise_for_status()
        return r.content
    raise RuntimeError("rate-limited")

def commons_images(query):
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrsearch": query + " filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1024}).json()
    out = []
    for pg in (r.get("query", {}).get("pages", {}) or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png") or ii.get("width", 0) < 800: continue
        t = pg.get("title", "").lower()
        if any(x in t for x in ("logo", "flag", "map", "symbol", "icon", "poster", "diagram", "signature", "coat of arms", "screenshot")): continue
        md = ii.get("extmetadata", {})
        credit = f'{_clean(md.get("Artist", {}).get("value", "Unknown"))[:60]} / Wikimedia Commons ({_clean(md.get("LicenseShortName", {}).get("value", "CC"))})'
        out.append({"url": ii.get("thumburl") or ii["url"], "credit": credit, "id": pg.get("title")})
    return out

def openverse_images(query):
    r = requests.get("https://api.openverse.org/v1/images/", headers=UA, timeout=30,
                     params={"q": query, "page_size": 12, "license_type": "commercial", "mature": "false", "size": "large"}).json()
    return [{"url": x["url"], "credit": f'{_clean(x.get("creator") or "Unknown")[:60]} / {x.get("source", "Openverse")} ({x.get("license", "cc").upper()})',
             "id": x["url"]} for x in r.get("results", [])]

def person_images(name):
    """Only files whose title contains every word of the name (avoids 'Tiger Shroff' -> tiger)."""
    toks = [t.lower() for t in re.findall(r"\w+", name) if len(t) > 1]
    return [c for c in commons_images(f'"{name}"') if all(t in (c["id"] or "").lower() for t in toks)]

def collect_candidates(line, state, tmp, idx, k=4):
    """Download up to k candidate photos for one scene (person first, then specific, then general queries)."""
    plan = []
    if line.get("person"): plan.append(("person", line["person"]))
    for q in [line.get("visual", "")] + list(line.get("visual_alt", [])):
        if q: plan.append(("place", q))
    out, seen = [], set()
    for kind, q in plan:
        for fn in ((person_images,) if kind == "person" else (commons_images, openverse_images)):
            if len(out) >= k: break
            try: found = fn(q)
            except Exception as e: print("  search fail", fn.__name__, str(e)[:100]); continue
            for c in found:
                if len(out) >= k: break
                if c["id"] in state["used"] or c["id"] in seen: continue
                seen.add(c["id"])
                try:
                    im = Image.open(io.BytesIO(_fetch(c["url"]))).convert("RGB")
                    if im.width < 700 or not (0.4 < im.width / im.height < 3.2): continue
                    path = f"{tmp}/c{idx}_{len(out)}.jpg"; im.save(path, quality=92)
                    th = im.copy(); th.thumbnail((384, 384)); b = io.BytesIO(); th.save(b, "JPEG", quality=70)
                    out.append({**c, "path": path, "thumb": b.getvalue(), "q": q})
                except Exception as e:
                    print("  img fail", str(e)[:100])
    return out

def compose_still(imgpath, out):
    """Blurred full-screen background + sharp photo in the middle (classic news-reel look)."""
    im = Image.open(imgpath).convert("RGB")
    bg = im.copy(); r = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * r) + 1, int(bg.height * r) + 1)).filter(ImageFilter.GaussianBlur(35))
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    canvas = bg.crop((l, t, l + W, t + H)); canvas = Image.eval(canvas, lambda v: int(v * 0.55))
    fr = W / im.width
    if im.height * fr < 900:
        fg = im.resize((int(im.width * 900 / im.height), 900)); l = (fg.width - W) // 2; fg = fg.crop((l, 0, l + W, 900))
    else:
        fg = im.resize((W, int(im.height * fr)))
        if fg.height > 1100: t = int((fg.height - 1100) * 0.2); fg = fg.crop((0, t, W, t + 1100))
    canvas.paste(fg, (0, 560 + (1100 - fg.height) // 2 if fg.height < 1100 else 560))
    canvas.save(out, quality=92)

def still_clip(png, seconds, path, idx):
    n = max(int(seconds * FPS), 2)
    z = "min(1.0+0.0007*on,1.22)" if idx % 2 == 0 else "max(1.22-0.0007*on,1.0)"
    vf = f"scale=1620:2880,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},format=yuv420p"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-vf", vf, "-frames:v", str(n),
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", path], check=True)

def gradient_clip(seconds, path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"gradients=s={W}x{H}:c0=0x0b1b3a:c1=0x3a0b2a:speed=0.02:d={seconds:.2f}", "-t", f"{seconds:.3f}", "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-an", path], check=True)
