import asyncio, os, subprocess, requests
from config import *

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
    asyncio.run(edge_tts.Communicate(text, EDGE_VOICE, rate="+8%").save(path))

def _gtts(text, path):  # last-resort free fallback (works from cloud IPs)
    from gtts import gTTS
    gTTS(text=text, lang="hi", tld="co.in").save(path)

def _one(text, path):
    engines = []
    if os.getenv("ELEVENLABS_API_KEY"): engines.append(("elevenlabs", _eleven))
    engines += [("edge-tts", _edge), ("gtts", _gtts)]
    for name, fn in engines:
        try:
            fn(text, path)
            if os.path.getsize(path) > 1000:
                return name
        except Exception as e:
            print(f"  TTS {name} failed: {type(e).__name__}: {str(e)[:200]}")
    raise SystemExit("All TTS engines failed")

def dur(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode())

def synth_lines(lines, outdir):
    """One clip per line => exact caption timing. Returns (full_audio_path, [(start,end)])."""
    paths = []
    for i, ln in enumerate(lines):
        p = f"{outdir}/l{i}.mp3"
        eng = _one(ln["text"], p); print(f"  line {i}: {eng}")
        paths.append(p)
    times, t = [], 0.0
    for p in paths:
        d = dur(p); times.append((t, t + d)); t += d
    lst = f"{outdir}/a.txt"
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in paths))
    out = f"{outdir}/voice.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:a", "libmp3lame", "-b:a", "192k", out], check=True)
    return out, times
