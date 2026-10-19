import datetime as dt, json, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src")); sys.path.insert(0, HERE)
import news as sn                       # src/news.py (trends)
import upload as su                     # src/upload.py (enabled())
import bconfig as B, bnews, bscript, bsynth, bvisual, brender, bupload
from config import CHANNEL_NAME

IST = dt.timezone(dt.timedelta(hours=5, minutes=30)); SLOTS_F = os.path.join(B.BASE, "slots.json")
fmt = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
TEST = os.getenv("TEST_MODE", "").lower() == "true"
if TEST: B.TARGET_SECONDS, B.MIN_SECONDS, B.MAX_SECONDS, B.MIN_STORIES, B.MAX_STORIES = 60, 40, 150, 2, 3

def taken():
    try: return json.load(open(SLOTS_F))
    except Exception: return []

def next_slot(min_lead=8):
    now = dt.datetime.now(dt.timezone.utc); tk = set(taken())
    for d in range(3):
        day = (now.astimezone(IST) + dt.timedelta(days=d)).date()
        for h, m in B.SLOTS_IST:
            t = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=IST).astimezone(dt.timezone.utc)
            if t > now + dt.timedelta(minutes=min_lead) and fmt(t) not in tk: return t

def mmss(s): return f"{int(s) // 60:02d}:{int(s) % 60:02d}"

event = os.getenv("EVENT_NAME", "")
publish_now = event != "schedule" and os.getenv("PUBLISH_NOW", "true").lower() != "false"
do_upload = (not TEST) and os.getenv("DO_UPLOAD", "true").lower() != "false" and su.enabled()
slot = None if (publish_now or not do_upload) else next_slot()
when = (slot or dt.datetime.now(dt.timezone.utc)).astimezone(IST)
edition = ("सुबह 7 बजे का बुलेटिन" if slot and when.hour < 12 else "शाम 7 बजे का बुलेटिन") if slot else ("सुबह का बुलेटिन" if when.hour < 15 else "शाम का बुलेटिन")
date_str = f"{when.day} {B.HI_MONTHS[when.month - 1]} {when.year}"
print(f"edition: {edition} | {date_str} | upload: {do_upload} | slot: {slot} | test: {TEST}")
tmp = os.path.join(HERE, "..", "tmp_b"); os.makedirs(tmp, exist_ok=True); os.makedirs(os.path.join(HERE, "..", "output_b"), exist_ok=True)
outdir = os.path.join(HERE, "..", "output_b")

print("1/8 news + trends")
items = bnews.gather()
if len(items) < 8: raise SystemExit("Too few news items found")
bnews.fetch_texts(items[:45])
for it in items[45:]: it["text"] = it["summary"] or it["title"]
trends = sn.trends()

print("2/8 plan")
plan = bscript.plan(items, trends, bnews.recent_titles())
if len(plan) < max(B.MIN_STORIES, 2): raise SystemExit(f"Planner returned only {len(plan)} stories")
print("   planned:", [p["headline"] for p in plan])

print("3/8 write stories + voice (one voice for the whole bulletin)")
OVERHEAD = 85                                   # intro + headlines rundown + outro (seconds, estimate)
need = B.TARGET_SECONDS - OVERHEAD; cap_ = B.MAX_SECONDS - 120
segs, est, nxt = [], 0.0, 0
def write_next():
    global nxt
    while nxt < len(plan):
        s = dict(plan[nxt]); nxt += 1
        try: d = bscript.write_story(s, items)
        except BaseException as e: print("   story write failed:", str(e)[:100]); continue
        if len(d["lines"]) < 4: continue
        s.update(d); return s
    return None
while (est < need or len(segs) < B.MIN_STORIES) and len(segs) < B.MAX_STORIES:
    s = write_next()
    if s is None: break
    segs.append(s); est += sum(len(l.split()) for l in s["lines"]) / B.WPS
    print(f"   + {s['headline']} ({len(s['lines'])} lines, est {est:.0f}s)")

engine = None
for eng in ("edge-tts", "gtts"):
    ok = True
    for k, s in enumerate(segs):
        r = bsynth.synth(s["lines"], tmp, f"s{k}", eng)
        if r is None: print(f"   {eng} failed on story {k}; redoing everything with the next voice engine"); ok = False; break
        s["audio"], s["times"] = r
    if ok: engine = eng; break
if not engine: raise SystemExit("All voice engines failed")
print("   voice engine:", engine)
total = sum(s["times"][-1][1] for s in segs)
while total < need and len(segs) < B.MAX_STORIES:      # real audio shorter than the estimate -> add stories
    s = write_next()
    if s is None: break
    r = bsynth.synth(s["lines"], tmp, f"s{len(segs)}", engine)
    if r is None: continue
    s["audio"], s["times"] = r; segs.append(s); total += r[1][-1][1]; print(f"   + {s['headline']} (real total {total:.0f}s)")
while total > cap_ and len(segs) > B.MIN_STORIES: total -= segs.pop()["times"][-1][1]
print(f"   {len(segs)} stories, {total:.0f}s of story audio")

print("4/8 photos")
used, pool = set(), []
for k, s in enumerate(segs):
    print(f"   story {k}: {s['headline']}")
    s["images"] = bvisual.story_images(s, s, tmp, f"p{k}", used, pool)

print("5/8 bulletin frame (intro, outro, title)")
heads = [s["headline"] for s in segs]
fr = bscript.write_frame(heads, edition, date_str)
rund = [f"{B.ORDINALS[i] if i < len(B.ORDINALS) else str(i + 1)} ख़बर: {h}" for i, h in enumerate(heads)]
frames = {}
for key, lines in (("intro", fr["intro"]), ("rundown", rund), ("outro", fr["outro"])):
    r = bsynth.synth(lines, tmp, key, engine)
    if r is None: raise SystemExit(f"voice failed for {key}")
    frames[key] = {"lines": lines, "audio": r[0], "times": r[1]}

print("6/8 render")
def comps_for(imgs, tag, headline, category):
    out = []
    for j, c in enumerate(imgs):
        p = f"{tmp}/{tag}_comp{j}.jpg"; brender.comp_wide(c["path"], p); out.append(p)
    if not out:
        p = f"{tmp}/{tag}_card.jpg"; brender.text_card(headline, category, p); out = [p]
    return out
hero = [comps_for(s["images"][:1], f"h{k}", s["headline"], s["category"])[0] for k, s in enumerate(segs)]
segfiles, starts, t0 = [], [], 0.0
def add(tag, tagtext, headline, lines, times, audio, comps, per_line=False, chapter=None):
    global t0
    out = f"{tmp}/seg_{tag}.mp4"
    D = brender.render_segment(tag, tagtext, headline, lines, times, audio, comps, tmp, out, per_line)
    segfiles.append(out)
    if chapter: starts.append((t0, chapter))
    t0 += D; print(f"   {tag}: {D:.0f}s (total {t0:.0f}s)")
add("intro", "बुलेटिन", f"{CHANNEL_NAME} | {edition} | {date_str}", frames["intro"]["lines"], frames["intro"]["times"], frames["intro"]["audio"], hero[:3] or hero, chapter="शुरुआत")
add("rundown", "सुर्खियाँ", "आज की प्रमुख सुर्खियाँ", frames["rundown"]["lines"], frames["rundown"]["times"], frames["rundown"]["audio"], hero, per_line=True, chapter="आज की प्रमुख सुर्खियाँ")
for k, s in enumerate(segs):
    add(f"s{k}", s["category"], s["headline"], s["lines"], s["times"], s["audio"], comps_for(s["images"], f"s{k}", s["headline"], s["category"]), chapter=s["headline"])
add("outro", "धन्यवाद", f"{CHANNEL_NAME} को फ़ॉलो करें", frames["outro"]["lines"], frames["outro"]["times"], frames["outro"]["audio"], hero[-3:] or hero)

print("7/8 final video + metadata")
name = f"{outdir}/bulletin_{int(time.time())}"
brender.concat(segfiles, tmp, name + ".mp4")
dur_total = t0
chapters = "\n".join(f"{mmss(a)} {b}" for a, b in starts)
srcs = sorted({items[s['index']]['source'] for s in segs})
desc = fr["description"].strip() + "\n\nअध्याय:\n" + chapters
desc += "\n\nस्रोत: " + ", ".join(srcs) + " (ख़बरों की पुष्टि मूल स्रोत से करें)."
desc += "\nयह बुलेटिन AI की मदद से बनाया गया है (स्क्रिप्ट, आवाज़)।"
credits = sorted({c["credit"] for s in segs for c in s["images"]})
if credits: desc += "\nImages: " + "; ".join(credits)[:1800]
thumb = name + ".jpg"
try: brender.thumbnail(segs[0]["images"][0]["path"] if segs[0]["images"] else hero[0], heads[0], f"{edition} | {date_str}", thumb)
except Exception as e: print("thumbnail failed:", str(e)[:100]); thumb = None
meta = {"title": fr["title"], "description": desc, "tags": fr["tags"], "duration_sec": round(dur_total), "stories": heads}
json.dump(meta, open(name + ".json", "w"), ensure_ascii=False, indent=2)
print(f"   video length {mmss(dur_total)} ({dur_total:.0f}s)", "OK >= 8:30" if dur_total >= 510 else "WARNING: shorter than 8:30")

print("8/8 upload")
uploaded = False
if do_upload:
    print("   mode:", "publish now" if not slot else f"scheduled for {slot} UTC")
    bupload.upload_video(name + ".mp4", meta["title"], desc, meta["tags"], slot, thumb)
    if slot: json.dump([x for x in taken() if x >= fmt(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2))] + [fmt(slot)], open(SLOTS_F, "w"))
    uploaded = True
else:
    print("   upload skipped")
if not TEST:
    bnews.add_history({"title": meta["title"], "links": [items[s["index"]]["link"] for s in segs] + [items[j]["link"] for s in segs for j in s["also"][:2]],
                       "at": dt.datetime.utcnow().isoformat(), "uploaded": uploaded, "seconds": round(dur_total)})
print("done", name)
