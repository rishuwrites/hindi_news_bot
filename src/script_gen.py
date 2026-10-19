import json, os, time, requests
from config import GEMINI_MODEL
BASE = "https://generativelanguage.googleapis.com/v1beta"

def _models(key):
    """Stable models first. Preview/omni models often have 0 free quota (429), so they go last."""
    names = [os.getenv("GEMINI_MODEL") or "", "gemini-flash-latest"]
    try:
        r = requests.get(f"{BASE}/models", params={"key": key, "pageSize": 200}, timeout=30).json()
        ok = [m["name"].split("/")[-1] for m in r.get("models", [])
              if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]
              and not any(x in m["name"] for x in ("image", "tts", "live", "audio", "robotics", "computer", "omni", "exp"))]
        names += sorted([n for n in ok if "preview" not in n and "lite" not in n], reverse=True)
        names += sorted([n for n in ok if "preview" not in n and "lite" in n], reverse=True)
        names += sorted([n for n in ok if "preview" in n], reverse=True)
    except Exception:
        pass
    names.append(GEMINI_MODEL)
    seen = []
    for n in names:
        if n and n not in seen: seen.append(n)
    return seen

def gemini_json(parts, temperature=0.5):
    key = os.environ["GEMINI_API_KEY"]
    payload = {"contents": [{"parts": parts}],
               "generationConfig": {"responseMimeType": "application/json", "temperature": temperature}}
    last = None
    for m in _models(key)[:5]:
        r = requests.post(f"{BASE}/models/{m}:generateContent", params={"key": key}, json=payload, timeout=180)
        if r.status_code == 429:
            print(f"  {m}: 429, waiting 25s"); time.sleep(25)
            r = requests.post(f"{BASE}/models/{m}:generateContent", params={"key": key}, json=payload, timeout=180)
        if r.status_code == 200:
            try:
                txt = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                txt = txt.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                print("  using model", m); return json.loads(txt)
            except Exception as e:
                last = f"{m}: bad response ({e})"; print(last); continue
        last = f"{m}: {r.status_code} {r.text[:200]}"; print("  model failed ->", last)
    raise SystemExit("All Gemini models failed. Last error: " + str(last))

PROMPT = """आप भारतीय न्यूज़ शॉर्ट्स चैनल "देश की नब्ज़" के स्क्रिप्ट राइटर हैं।
नीचे दिए हैं: (1) आज भारत में Google पर ट्रेंड हो रही खोजें, (2) अलग-अलग स्रोतों की ताज़ा ख़बरें, (3) पहले कवर हो चुके शीर्षक।
काम: सबसे ज़्यादा ट्रेंडिंग और महत्वपूर्ण ख़बर चुनें (भारत/राजनीति को प्राथमिकता, ट्रेंड्स से मेल खाती, जिसके बारे में दिए टेक्स्ट में पर्याप्त तथ्य हों)। (3) में दिए विषयों से अलग चुनें। फिर 35-45 सेकंड (लगभग 95-110 शब्द) की हिंदी स्क्रिप्ट लिखें।
तथ्य-नियम: सिर्फ़ दिए गए टेक्स्ट के तथ्य इस्तेमाल करें, कुछ भी अपनी तरफ़ से न जोड़ें। आँकड़े/मौतें तभी बताएँ जब टेक्स्ट में हों, और "रिपोर्ट के मुताबिक" जैसा स्रोत-संकेत दें। आरोप को तथ्य की तरह न लिखें। निष्पक्ष भाषा, बिना भड़काऊ/सांप्रदायिक शब्दों के।
ढाँचा: पहली लाइन तेज़ हुक; आख़िरी लाइन में "ऐसी ख़बरों के लिए देश की नब्ज़ को फ़ॉलो करें"। हर लाइन 8-14 शब्द।
विज़ुअल नियम (हर लाइन के लिए): "visual" में असली फ़ोटो खोजने लायक अंग्रेज़ी शब्द (जगह, इमारत, संस्था, वस्तु; 2-4 शब्द; जैसे "Mumbai police vehicle"), "visual_alt" में 2 वैकल्पिक खोजें (एक ज़्यादा आम, जैसे "Mumbai street"), "visual" में कभी किसी व्यक्ति/अभिनेता/फ़िल्म/ब्रांड का नाम नहीं (ग़लत फ़ोटो आ जाती है)। अगर लाइन किसी जाने-माने सार्वजनिक व्यक्ति (नेता, अभिनेता, खिलाड़ी) के बारे में है जो ख़बर का मुख्य विषय है तो "person" में उसका पूरा अंग्रेज़ी नाम लिखें, वरना ""। आरोपी, पीड़ित या आम नागरिक के लिए "person" हमेशा ""। हादसे/मौत में भयावह चित्र न माँगें, जगह या प्रशासन जैसे तटस्थ विषय रखें। हर लाइन का visual अलग हो।
यूट्यूब: "title" हर बार नया, आकर्षक पर भ्रामक नहीं, 70 अक्षर तक, बिना #Shorts; "description" में 2-3 वाक्य सार + 5-6 प्रासंगिक हैशटैग (हर बार अलग); "tags" में 8-10 कीवर्ड (हिंदी+अंग्रेज़ी)।
केवल JSON लौटाएँ:
{"index": <चुनी ख़बर का नंबर>, "topic_key": "short english slug", "headline": "<=8 शब्द की स्क्रीन हेडलाइन", "lines": [{"text": "हिंदी लाइन", "visual": "...", "visual_alt": ["...", "..."], "person": ""}], "title": "...", "description": "...", "tags": ["..."]}
"""

def generate(items, trends, recent):
    body = "(1) ट्रेंडिंग खोजें:\n" + ("\n".join("- " + t for t in trends) or "- (उपलब्ध नहीं)")
    body += "\n\n(3) पहले कवर हो चुके शीर्षक:\n" + ("\n".join("- " + t for t in recent if t) or "- (कोई नहीं)")
    body += "\n\n(2) ख़बरें:\n" + "\n\n".join(f"[{i}] ({it['source']}) {it['title']}\n{it['text']}" for i, it in enumerate(items))
    return gemini_json([{"text": PROMPT + "\n" + body}], 0.6)
