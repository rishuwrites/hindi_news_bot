import json, os, re, requests, feedparser, trafilatura
from config import FEEDS, TRENDS_URL
UA = {"User-Agent": "Mozilla/5.0 (compatible; DeshKiNabzBot/1.0)"}
HIST = "history.json"

def _load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def history(): return _load(HIST, [])

def add_history(entry):
    h = history(); h.append(entry); json.dump(h[-80:], open(HIST, "w"), ensure_ascii=False, indent=1)

def recent_titles(n=25): return [h.get("title", "") for h in history()[-n:]]

def _seen(): return {h.get("link") for h in history()} | set(_load("used.json", []))

def _clean(t): return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", t or "")).strip()

def gather(per_feed=5, cap=18):
    """Round-robin across many sources so no single outlet dominates."""
    seen, pools = _seen(), []
    for name, url in FEEDS:
        try:
            feed = feedparser.parse(requests.get(url, headers=UA, timeout=20).content)
        except Exception as e:
            print(f"   {name}: FAILED {type(e).__name__}"); continue
        items = []
        for e in feed.entries[:15]:
            link = e.get("link")
            if not link or link in seen: continue
            items.append({"source": name, "title": _clean(re.sub(r"\s+-\s+[^-]+$", "", e.get("title", ""))),
                          "link": link, "summary": _clean(e.get("summary", ""))[:600]})
            if len(items) >= per_feed: break
        print(f"   {name}: {len(items)}"); pools.append(items)
    out = []
    while len(out) < cap and any(pools):
        for p in pools:
            if p and len(out) < cap: out.append(p.pop(0))
    return out

def trends(n=15):
    """What India is searching on Google right now (a real 'trending' signal)."""
    try:
        feed = feedparser.parse(requests.get(TRENDS_URL, headers=UA, timeout=20).content)
        out = [f'{e.get("title","")} ({e.get("ht_approx_traffic","")})'.replace(" ()", "") for e in feed.entries[:n]]
        print(f"   trends: {len(out)}"); return out
    except Exception as e:
        print("   trends: FAILED", type(e).__name__); return []

def fetch_text(item):
    if "news.google.com" in item["link"]:
        return item["summary"] or item["title"]
    try:
        html = requests.get(item["link"], headers=UA, timeout=15).text
        t = trafilatura.extract(html) or ""
    except Exception:
        t = ""
    return (t or item["summary"] or item["title"])[:1500]
