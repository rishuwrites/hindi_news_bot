import functools, os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import visuals as sv
import bconfig as B
from config import CHANNEL_NAME
W, H, FPS = B.W, B.H, B.FPS
PANEL_Y, CAP_Y = 790, 890

@functools.lru_cache(None)
def _fp(): return sv.find_font()
@functools.lru_cache(None)
def font(size): return ImageFont.truetype(_fp(), size, layout_engine=ImageFont.Layout.RAQM)
_dummy = ImageDraw.Draw(Image.new("RGB", (8, 8)))

def comp_wide(img, out):
    """Blurred full-frame background + sharp photo; always fills the screen (no blank areas)."""
    im = Image.open(img).convert("RGB")
    r = max(W / im.width, H / im.height)
    bg = im.resize((int(im.width * r) + 1, int(im.height * r) + 1)).filter(ImageFilter.GaussianBlur(30))
    l, t = (bg.width - W) // 2, (bg.height - H) // 2
    canvas = Image.eval(bg.crop((l, t, l + W, t + H)), lambda v: int(v * 0.5))
    fr = min(1800 / im.width, 740 / im.height)
    fg = im.resize((max(int(im.width * fr), 1), max(int(im.height * fr), 1)))
    canvas.paste(fg, ((W - fg.width) // 2, 30 + (740 - fg.height) // 2))
    canvas.save(out, quality=90)

def text_card(headline, category, out):
    """Used only if a story has no photo at all: designed card with the headline, not a blank screen."""
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    seed = sum(map(ord, category)) % 5
    c0 = [(11, 27, 58), (40, 12, 50), (10, 45, 50), (50, 25, 10), (20, 20, 60)][seed]
    for y in range(H):
        k = y / H; d.line([(0, y), (W, y)], fill=tuple(int(c0[i] * (1 - k * 0.6)) for i in range(3)))
    f = font(96); ls = sv.wrap(d, headline, f, 1500)[:4]
    y0 = 380 - len(ls) * 55
    for i, l in enumerate(ls):
        d.text(((W - d.textlength(l, font=f)) / 2, y0 + i * 120), l, font=f, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    im.save(out, quality=90)

def panel_png(tagtext, headline, out):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((0, PANEL_Y, W, H), fill=(8, 10, 24, 232)); d.rectangle((0, PANEL_Y, W, PANEL_Y + 6), fill=(255, 200, 0, 255))
    ft = font(40); tw = int(d.textlength(tagtext, font=ft)); bx = 50 + tw + 56
    d.rounded_rectangle((50, PANEL_Y + 22, bx, PANEL_Y + 84), 14, fill=(200, 0, 20, 255))
    d.text((78, PANEL_Y + 24), tagtext, font=ft, fill=(255, 255, 255))
    size = 54
    while size > 36 and d.textlength(headline, font=font(size)) > W - bx - 30 - 50: size -= 2
    d.text((bx + 30, PANEL_Y + 14), headline, font=font(size), fill=(255, 215, 0))
    fc = font(38); cw = int(d.textlength(CHANNEL_NAME, font=fc))
    d.rounded_rectangle((W - cw - 80, 28, W - 30, 92), 14, fill=(0, 0, 0, 170))
    d.text((W - cw - 55, 30), CHANNEL_NAME, font=fc, fill=(255, 255, 255))
    im.save(out)

def caption_chunks(text, a, b):
    ls = sv.wrap(_dummy, text, font(50), 1780)
    groups = [ls[i:i + 2] for i in range(0, len(ls), 2)]
    tot = sum(len(" ".join(g)) for g in groups) or 1; t = a; res = []
    for g in groups:
        w = len(" ".join(g)) / tot * (b - a); res.append((g, t, t + w)); t += w
    return res

def caption_png(lines, out):
    im = Image.new("RGBA", (W, 190), (0, 0, 0, 0)); d = ImageDraw.Draw(im); f = font(50)
    y = (190 - 70 * len(lines)) // 2
    for l in lines:
        d.text(((W - d.textlength(l, font=f)) / 2, y), l, font=f, fill=(255, 255, 255)); y += 70
    im.save(out)

def clip(comp, frames, path, idx):
    z = "min(1+0.00045*on,1.18)" if idx % 2 == 0 else "max(1.18-0.00045*on,1.0)"
    vf = f"scale=2400:1350,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", comp, "-vf", vf, "-frames:v", str(frames),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-an", path], check=True)

def render_segment(tag, tagtext, headline, lines, times, audio, comps, tmp, out, per_line=False):
    D = times[-1][1]
    if per_line: bounds = [times[0][0]] + [b for a, b in times]
    else:
        n = max(1, round(D / 12)); bounds = [D * k / n for k in range(n + 1)]
    paths = []
    for k in range(len(bounds) - 1):
        fr = round(bounds[k + 1] * FPS) - round(bounds[k] * FPS)
        p = f"{tmp}/{tag}_c{k}.mp4"; clip(comps[k % len(comps)], max(fr, 2), p, k); paths.append(p)
    open(f"{tmp}/{tag}_c.txt", "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in paths))
    bg = f"{tmp}/{tag}_bg.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/{tag}_c.txt", "-c", "copy", bg], check=True)
    panel_png(tagtext, headline, f"{tmp}/{tag}_panel.png")
    ins = ["-i", bg, "-i", audio, "-i", f"{tmp}/{tag}_panel.png"]; flt = "[0:v][2:v]overlay=0:0[v0];"; n_ov = 0
    for li, (ln, (a, b)) in enumerate(zip(lines, times)):
        for gi, (g, ta, tb) in enumerate(caption_chunks(ln, a, b)):
            cp = f"{tmp}/{tag}_cap{li}_{gi}.png"; caption_png(g, cp); ins += ["-i", cp]
            flt += f"[v{n_ov}][{3 + n_ov}:v]overlay=0:{CAP_Y}:enable='between(t,{ta:.3f},{tb:.3f})'[v{n_ov + 1}];"; n_ov += 1
    flt = flt.rstrip(";")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + ins + ["-filter_complex", flt, "-map", f"[v{n_ov}]", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-maxrate", "4000k", "-bufsize", "8000k", "-r", str(FPS), "-g", str(FPS * 2),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", "-t", f"{D:.3f}", out], check=True)
    for p in paths + [bg]: os.remove(p)   # keep disk small
    return D

def concat(segments, tmp, out):
    open(f"{tmp}/final.txt", "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in segments))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/final.txt",
                    "-c", "copy", "-movflags", "+faststart", out], check=True)

def thumbnail(img, line1, line2, out):
    im = Image.open(img).convert("RGB"); r = max(1280 / im.width, 720 / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1)); l, t = (im.width - 1280) // 2, (im.height - 720) // 2
    im = Image.eval(im.crop((l, t, l + 1280, t + 720)), lambda v: int(v * 0.6)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1280, 110), fill=(200, 0, 20)); d.text((40, 12), line2, font=font(70), fill=(255, 255, 255))
    f = font(96); ls = sv.wrap(d, line1, f, 1200)[:3]
    for i, l_ in enumerate(ls):
        d.text((40, 170 + i * 135), l_, font=f, fill=(255, 215, 0), stroke_width=5, stroke_fill=(0, 0, 0))
    d.text((40, 640), CHANNEL_NAME, font=font(56), fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    im.save(out, quality=88)
