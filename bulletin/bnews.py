import concurrent.futures as cf, json, os, re, requests, feedparser, trafilatura
import config as C
import bconfig as B
UA = {"User-Agent": "Mozilla/5.0 (compatible; DeshKiNabzBot/1.0)"}
HIST = os.path.join(B.BASE, "history.json")

def _load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def history(): return _load(HIST, [])

def add_history(entry):
    h = history(); h.append(entry); json.dump(h[-40:], open(HIST, "w"), ensure_ascii=False, indent=1)

def recent_titles(n=8): return [h.get("title", "") for h in history()[-n:]]

def _seen():
    out = set()
    for h in history()[-20:]: out |= set(h.get("links", []))
    return out

def _clean(t): return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", t or "")).strip()

def gather(per_feed=6, cap=60):
    """Many outlets + topic feeds (world, business, sports...) interleaved so no outlet dominates."""
    seen, pools = _seen(), []
    feeds = [(n, u, "") for n, u in C.FEEDS] + B.TOPIC_FEEDS
    for name, url, hint in feeds:
        try: feed = feedparser.parse(requests.get(url, headers=UA, timeout=20).content)
        except Exception as e: print(f"   {name}: FAILED {type(e).__name__}"); continue
        items = []
        for e in feed.entries[:20]:
            link = e.get("link")
            if not link or link in seen: continue
            items.append({"source": name, "hint": hint, "link": link,
                          "title": _clean(re.sub(r"\s+-\s+[^-]+$", "", e.get("title", ""))),
                          "summary": _clean(e.get("summary", ""))[:500]})
            if len(items) >= per_feed: break
        print(f"   {name}: {len(items)}"); pools.append(items)
    out = []
    while len(out) < cap and any(pools):
        for p in pools:
            if p and len(out) < cap: out.append(p.pop(0))
    return out

def _text(item):
    if "news.google.com" in item["link"]: return item["summary"] or item["title"]
    try: t = trafilatura.extract(requests.get(item["link"], headers=UA, timeout=15).text) or ""
    except Exception: t = ""
    return (t or item["summary"] or item["title"])[:2500]

def fetch_texts(items):
    with cf.ThreadPoolExecutor(8) as ex:
        for it, t in zip(items, ex.map(_text, items)): it["text"] = t
