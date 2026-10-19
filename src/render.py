import os, subprocess
from config import *
from visuals import *
import picker

def build_scenes(lines, times, tmp):
    """1) collect candidate photos per scene 2) Gemini vision picks the best/safest 3) clip per scene."""
    state = {"used": set(), "credits": []}
    scenes = []
    for i, ln in enumerate(lines):
        c = collect_candidates(ln, state, tmp, i)
        print(f"  scene {i}: {len(c)} candidates ({ln.get('visual')})")
        for x in c: state["used"].add(x["id"])
        scenes.append({"line": ln["text"], "want": ln.get("visual", ""), "person": ln.get("person", ""), "cands": c})
    picks = picker.pick(scenes)
    chosen_ids = set(); choice = []
    for i in range(len(lines)):
        c = scenes[i]["cands"]
        if picks is None:  # picker unavailable: first candidate not already used
            j = next((k for k, x in enumerate(c) if x["id"] not in chosen_ids), -1)
        else:
            j = picks[i] if 0 <= picks[i] < len(c) and c[picks[i]]["id"] not in chosen_ids else -1
        if j >= 0: chosen_ids.add(c[j]["id"])
        choice.append(c[j] if j >= 0 else None)
    pool = [x for x in choice if x]                      # approved photos in this video
    paths = []; r = 0
    for i in range(len(lines)):
        seconds = times[i][1] - times[i][0]; p = f"{tmp}/s{i}.mp4"
        x = choice[i]
        if x is None and pool:                            # reuse an approved photo (different zoom) instead of a gradient
            x = pool[r % len(pool)]; r += 1; reused = True
        else: reused = False
        if x is not None:
            if not reused: state["credits"].append(x["credit"])
            compose_still(x["path"], f"{tmp}/img{i}.jpg"); still_clip(f"{tmp}/img{i}.jpg", seconds, p, i)
            print(f"  scene {i}: {'reused ' if reused else ''}photo -> {x['id'][:70]}")
        else:
            gradient_clip(seconds, p); print(f"  scene {i}: gradient (no approved photo in whole video)")
        paths.append(p)
    return paths, state["credits"]

def render(headline, lines, audio, times, out, tmp):
    scenes, credits = build_scenes(lines, times, tmp)
    open(f"{tmp}/c.txt", "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in scenes))
    bg = f"{tmp}/bg.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/c.txt", "-c", "copy", bg], check=True)
    header_png(headline, f"{tmp}/h.png")
    ins = ["-i", bg, "-i", audio, "-i", f"{tmp}/h.png"]; flt = "[0:v][2:v]overlay=0:0[v0];"
    for i, (ln, (a, b)) in enumerate(zip(lines, times)):
        caption_png(ln["text"], f"{tmp}/cap{i}.png"); ins += ["-i", f"{tmp}/cap{i}.png"]
        flt += f"[v{i}][{i+3}:v]overlay=0:0:enable='between(t,{a:.3f},{b:.3f})'[v{i+1}];"
    flt = flt.rstrip(";")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + ins + ["-filter_complex", flt, "-map", f"[v{len(lines)}]", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    return credits
