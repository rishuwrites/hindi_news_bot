import os, requests
import upload as su    # src/upload.py (token refresh)

def upload_video(mp4, title, description, tags, publish_at=None, thumb=None):
    title = title.replace("<", "").replace(">", "").strip()[:100]
    tg, total = [], 0
    for t in tags:
        t = str(t).replace("<", "").replace(">", "").strip()
        if t and total + len(t) + 1 < 450: tg.append(t); total += len(t) + 1
    status = {"selfDeclaredMadeForKids": False}
    if publish_at: status.update(privacyStatus="private", publishAt=publish_at.strftime("%Y-%m-%dT%H:%M:%SZ"))
    else: status["privacyStatus"] = os.getenv("UPLOAD_PRIVACY") or "public"
    meta = {"snippet": {"title": title, "description": description[:4900], "tags": tg, "categoryId": "25",
                        "defaultLanguage": "hi", "defaultAudioLanguage": "hi"}, "status": status}
    tok = su._token(); size = os.path.getsize(mp4)
    init = requests.post("https://www.googleapis.com/upload/youtube/v3/videos", params={"uploadType": "resumable", "part": "snippet,status"},
                         headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                                  "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}, json=meta, timeout=60)
    if init.status_code != 200: raise SystemExit(f"YouTube upload init failed: {init.status_code} {init.text[:500]}")
    with open(mp4, "rb") as f:
        r = requests.put(init.headers["Location"], data=f, headers={"Content-Type": "video/mp4", "Content-Length": str(size)}, timeout=3600)
    if r.status_code not in (200, 201): raise SystemExit(f"YouTube upload failed: {r.status_code} {r.text[:500]}")
    vid = r.json()["id"]; print("UPLOADED https://youtube.com/watch?v=" + vid, "| publishAt:", publish_at)
    if thumb and os.path.exists(thumb):
        try:
            t = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set", params={"videoId": vid, "uploadType": "media"},
                              headers={"Authorization": f"Bearer {su._token()}", "Content-Type": "image/jpeg"}, data=open(thumb, "rb").read(), timeout=120)
            print("thumbnail:", t.status_code, "" if t.status_code == 200 else t.text[:200])
        except Exception as e:
            print("thumbnail skipped:", e)
    return vid
