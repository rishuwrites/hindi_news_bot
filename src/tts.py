import asyncio, os, re, subprocess, time, requests
from config import *

def _sanitize(t):
    t = t.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("—", ", ").replace("–", ", ").replace("…", ".")
    t = re.sub(r"[^\u0900-\u097F\x20-\x7E।]", " ", t)  # keep Devanagari, ASCII, danda
    return re.sub(r"\s+", " ", t).strip()

def _eleven(text, path):
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        params={"output_format": "mp3_44100_128"},
        json={"text": text, "model_id": ELEVEN_MODEL,
              "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}},
        timeout=120)
    r.raise_for_status(); open(path, "wb").write(r.content)

def _edge(text, path):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, EDGE_VOICE, rate="+5%").save(path))

def _gtts(text, path):  # last-resort free fallback (works from cloud IPs, robotic voice)
    from gtts import gTTS
    gTTS(text=text, lang="hi", tld="co.in").save(path)

def _try(fn, text, path, tries):
    for i in range(tries):
        try:
            if os.path.exists(path): os.remove(path)
            fn(text, path)
            if os.path.getsize(path) > 1000: return True
        except Exception as e:
            print(f"    {fn.__name__} try {i + 1}/{tries}: {type(e).__name__}: {str(e)[:90]}")
        time.sleep(1.5 * (i + 1))
    return False

def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode())

def synth_lines(lines, outdir):
    """Whole video uses ONE voice. If any line fails after retries, redo every line with the next engine."""
    engines = []
    if os.getenv("ELEVENLABS_API_KEY"): engines.append(("elevenlabs", _eleven, 2))
    engines += [("edge-tts", _edge, 4), ("gtts", _gtts, 3)]
    for name, fn, tries in engines:
        paths, ok = [], True
        for i, ln in enumerate(lines):
            p = f"{outdir}/l{i}.mp3"
            if not _try(fn, _sanitize(ln["text"]), p, tries):
                print(f"  {name} failed on line {i}; switching engine so the voice stays consistent"); ok = False; break
            paths.append(p)
        if ok: print(f"  voice: {name}"); break
    else:
        raise SystemExit("All TTS engines failed")
    times, t = [], 0.0
    for p in paths:
        d = dur(p); times.append((t, t + d)); t += d
    lst = f"{outdir}/a.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in paths))
    out = f"{outdir}/voice.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-b:a", "192k", out], check=True)
    return out, times
