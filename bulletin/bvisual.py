import base64, io
from PIL import Image
import visuals as sv, script_gen as sg
import bconfig as B

RULES = """आप न्यूज़ बुलेटिन के फ़ोटो एडिटर हैं। एक ख़बर और उसके उम्मीदवार फ़ोटो (फ़ाइल-नाम के साथ) दिए हैं।
हर स्वीकार्य फ़ोटो का नंबर \"keep\" में दें, सबसे अच्छी पहले (अधिकतम 7): पहले वे जो ख़बर से सीधे मेल खाती हैं; फिर सही तरह की जगह/वस्तु की सामान्य हानिरहित फ़ोटो (इमारत, सड़क, थाना, अदालत, स्टेडियम) भी चलेंगी।
इन्हें शामिल न करें: भ्रामक/उलटे विषय की (नाम में Tiger तो बाघ, किसी और देश/घटना की ख़ास तस्वीर), लोगो/नक्शा/पोस्टर/स्क्रीनशॉट/टेक्स्ट-भारी चित्र, ग्राफ़िक हिंसा/ख़ून/शव, पहचाने जाने योग्य बच्चे, बहुत ख़राब गुणवत्ता।
व्यक्ति वाली ख़बर में उस व्यक्ति की फ़ोटो तभी रखें जब फ़ाइल-नाम में वही नाम हो (चेहरे से किसी को पहचानने की कोशिश न करें)।
केवल JSON: {\"keep\":[2,0,5]}"""

def collect(queries, person, tmp, tag, used, k=9):
    plan = ([("person", person)] if person else []) + [("place", q) for q in queries if q]
    out, seen = [], set()
    for kind, q in plan:
        for fn in ((sv.person_images,) if kind == "person" else (sv.commons_images, sv.openverse_images)):
            if len(out) >= k: break
            try: found = fn(q)
            except Exception as e: print("    search fail", fn.__name__, str(e)[:80]); continue
            for c in found:
                if len(out) >= k: break
                if c["id"] in used or c["id"] in seen: continue
                seen.add(c["id"])
                try:
                    im = Image.open(io.BytesIO(sv._fetch(c["url"]))).convert("RGB")
                    if im.width < 900 or not (0.6 < im.width / im.height < 2.8): continue
                    path = f"{tmp}/{tag}_{len(out)}.jpg"; im.save(path, quality=90)
                    th = im.copy(); th.thumbnail((384, 384)); b = io.BytesIO(); th.save(b, "JPEG", quality=70)
                    out.append({**c, "path": path, "thumb": b.getvalue(), "q": q})
                except Exception as e:
                    print("    img fail", str(e)[:80])
    return out

def judge(headline, summary, person, cands):
    if not cands: return []
    parts = [{"text": RULES + f"\n\nख़बर: {headline}\nसार: {summary}\nव्यक्ति: {person or '-'}"}]
    for j, c in enumerate(cands):
        parts += [{"text": f"उम्मीदवार {j} (फ़ाइल: {c['id']}):"},
                  {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(c["thumb"]).decode()}}]
    try:
        import time; time.sleep(3)
        keep = [int(x) for x in sg.gemini_json(parts, 0.1).get("keep", []) if 0 <= int(x) < len(cands)]
    except BaseException as e:
        print("    judge failed, keeping first 4:", str(e)[:100]); keep = list(range(min(4, len(cands))))
    seen, res = set(), []
    for x in keep:
        if x not in seen: seen.add(x); res.append(cands[x])
    return res[:7]

def story_images(story, data, tmp, tag, used, pool):
    """Approved photos for one story. Falls back to category-generic searches, then to photos already approved elsewhere."""
    cands = collect(data["queries"], data["person"], tmp, tag, used)
    keep = judge(story["headline"], " ".join(data["lines"][:2]), data["person"], cands)
    for c in cands: used.add(c["id"])
    if len(keep) < 3:
        gen = B.CATEGORY_GENERIC.get(story["category"], B.DEFAULT_GENERIC)
        more = collect(gen, "", tmp, tag + "g", used, k=6)
        keep += judge(story["headline"], "सामान्य चित्र", "", more)[: 4 - len(keep)]
        for c in more: used.add(c["id"])
    keep = keep[:7]
    pool.extend(keep)
    if len(keep) < 3 and pool:   # never leave a story visually empty: borrow approved photos from other stories
        keep += [p for p in pool[::-1] if p not in keep][: 3 - len(keep)]
    print(f"    {tag}: {len(keep)} photos ({', '.join(c['id'][5:40] for c in keep[:3])})")
    return keep
