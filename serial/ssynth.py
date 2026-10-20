import os, subprocess
import tts as T                       # src/tts.py helpers (retry, sanitize, durations)
import sconfig as S
T.EDGE_VOICE = S.VOICE                # narrator voice for this channel

def _one(lines, outdir, tag, fn, tries):
    paths = []
    for i, ln in enumerate(lines):
        p = f"{outdir}/{tag}_{i}.mp3"
        if not T._try(fn, T._sanitize(ln), p, tries): return None
        paths.append(p)
    times, t = [], 0.0
    for p in paths:
        d = T.dur(p); times.append((t, t + d)); t += d
    lst = f"{outdir}/{tag}_a.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in paths))
    out = f"{outdir}/{tag}.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "libmp3lame", "-b:a", "160k", out], check=True)
    return out, times

def synth_all(segments, outdir):
    """segments: [{'tag','lines'}]. One voice engine for the whole video; falls back for ALL segments if one fails."""
    for name, fn, tries in (("edge-tts", T._edge, 4), ("gtts", T._gtts, 3)):
        res, ok = [], True
        for s in segments:
            r = _one(s["lines"], outdir, s["tag"], fn, tries)
            if r is None: print(f"  {name} failed on {s['tag']}; switching engine for the whole video"); ok = False; break
            res.append(r)
        if ok:
            print("  voice:", name, "|", S.VOICE if name == "edge-tts" else "gTTS")
            for s, (a, t) in zip(segments, res): s["audio"], s["times"] = a, t
            return
    raise SystemExit("All voice engines failed")
