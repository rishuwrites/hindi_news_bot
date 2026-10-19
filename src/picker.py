import base64
from script_gen import gemini_json
RULES = """आप न्यूज़ वीडियो के फ़ोटो एडिटर हैं। हर सीन की लाइन और उसके उम्मीदवार फ़ोटो (फ़ाइल-नाम के साथ) दिए हैं। हर सीन के लिए वह फ़ोटो चुनें जो लाइन के विषय को सही और बिना भ्रम के दिखाए।
-1 दें (कोई फ़ोटो नहीं) अगर: विषय से असंबंधित या सिर्फ़ नाम से मिलती-जुलती चीज़ (जैसे नाम में Tiger तो बाघ), लोगो/नक्शा/पोस्टर/स्क्रीनशॉट/टेक्स्ट-भारी चित्र, ग्राफ़िक हिंसा/ख़ून/शव, पहचाने जाने योग्य बच्चे, बहुत धुंधली या ख़राब फ़ोटो।
व्यक्ति वाले सीन में तभी चुनें जब फ़ाइल-नाम में वही नाम हो (चेहरे से किसी को पहचानने की कोशिश न करें)। एक ही फ़ोटो दो सीन में न चुनें।
केवल JSON: {"picks":[{"scene":0,"pick":1}]}  (pick = उम्मीदवार नंबर या -1)"""

def pick(scenes):
    """scenes: [{'line':str,'want':str,'person':str,'cands':[{'id','thumb'(jpeg bytes)}]}] -> list of chosen index or -1"""
    parts = [{"text": RULES}]
    for i, s in enumerate(scenes):
        if not s["cands"]: continue
        parts.append({"text": f"\n--- सीन {i}: लाइन='{s['line']}' | चाहिए='{s['want']}' | व्यक्ति='{s['person']}'"})
        for j, c in enumerate(s["cands"]):
            parts.append({"text": f"उम्मीदवार {j} (फ़ाइल: {c['id']}):"})
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(c["thumb"]).decode()}})
    res = {i: -1 for i in range(len(scenes))}
    try:
        for p in gemini_json(parts, 0.1).get("picks", []):
            if 0 <= int(p["scene"]) < len(scenes): res[int(p["scene"])] = int(p["pick"])
    except BaseException as e:
        print("  picker failed, using first safe candidate:", str(e)[:150])
        return None
    return [res[i] for i in range(len(scenes))]
