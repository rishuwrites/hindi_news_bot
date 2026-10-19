import os, subprocess
import tts as T          # shared helpers from src/tts.py (retry, sanitize, durations)

def synth(lines, outdir, tag, engine):
    """Voice one segment with the given engine ('edge-tts' or 'gtts'). Returns (mp3, [(start,end)]) or None if any line fails."""
    fn = {"edge-tts": (T._edge, 4), "gtts": (T._gtts, 3)}[engine]
    paths = []
    for i, ln in enumerate(lines):
        p = f"{outdir}/{tag}_{i}.mp3"
        if not T._try(fn[0], T._sanitize(ln), p, fn[1]): return None
        paths.append(p)
    times, t = [], 0.0
    for p in paths:
        d = T.dur(p); times.append((t, t + d)); t += d
    lst = f"{outdir}/{tag}_a.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in paths))
    out = f"{outdir}/{tag}.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-b:a", "160k", out], check=True)
    return out, times
