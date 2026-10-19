import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import news, script_gen, schedule, upload
from tts import synth_lines
from render import render

os.makedirs("output", exist_ok=True); tmp = "tmp"; os.makedirs(tmp, exist_ok=True)
event = os.getenv("EVENT_NAME", "")
publish_now = event != "schedule" and (os.getenv("PUBLISH_NOW", "true").lower() != "false")
do_upload = os.getenv("DO_UPLOAD", "true").lower() != "false"

print("1/6 news + trends")
items = news.gather()[:18]
if not items: raise SystemExit("No news items found (feeds empty or all already covered)")
for it in items[:12]: it["text"] = news.fetch_text(it)
for it in items[12:]: it["text"] = it["summary"] or it["title"]
trends = news.trends()

print("2/6 script")
data = script_gen.generate(items, trends, news.recent_titles())
lines = [l for l in data.get("lines", []) if l.get("text")]
if not lines: raise SystemExit(f"Bad script JSON: {data}")
for l in lines: l.setdefault("visual", "India city"); l.setdefault("visual_alt", []); l.setdefault("person", "")
chosen = items[min(max(int(data.get("index", 0)), 0), len(items) - 1)]
print("   headline:", data.get("headline"), "| title:", data.get("title"))

print("3/6 voice"); audio, times = synth_lines(lines, tmp)
name = f"output/short_{int(time.time())}"

print("4/6 visuals + render"); credits = render(data.get("headline", chosen["title"]), lines, audio, times, name + ".mp4", tmp)

print("5/6 metadata")
desc = data.get("description", "").strip()
desc += f"\n\nस्रोत: {chosen['source']} - {chosen['link']}"
desc += "\n\nयह वीडियो AI की मदद से बनाया गया है (स्क्रिप्ट, आवाज़)। ख़बर की पुष्टि मूल स्रोत से ज़रूर करें."
if credits: desc += "\nImages: " + "; ".join(sorted(set(credits)))
meta = {"title": data.get("title", chosen["title"]), "description": desc, "tags": data.get("tags", []), "source": chosen["link"]}
json.dump(meta, open(name + ".json", "w"), ensure_ascii=False, indent=2)

print("6/6 upload")
uploaded = False
if do_upload and upload.enabled():
    slot = None if publish_now else schedule.next_slot()
    print("   mode:", "publish now" if publish_now else f"scheduled for {slot} UTC")
    upload.upload(name + ".mp4", meta["title"], desc, meta["tags"], slot)
    if slot: schedule.take(slot)
    uploaded = True
else:
    print("   upload skipped (", "disabled" if not do_upload else "YT_* secrets not set", ")")
news.add_history({"link": chosen["link"], "title": meta["title"], "topic": data.get("topic_key", ""),
                  "at": dt.datetime.utcnow().isoformat(), "uploaded": uploaded})
print("done", name, f"({times[-1][1]:.1f}s)")
