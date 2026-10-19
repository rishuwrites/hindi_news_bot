import json, time
import script_gen as sg
import bconfig as B

FACT = ("तथ्य-नियम: सिर्फ़ दिए गए टेक्स्ट के तथ्य इस्तेमाल करें, कुछ अपनी तरफ़ से न जोड़ें। आँकड़े/मौतें/बयान तभी बताएँ जब टेक्स्ट में हों और स्रोत-संकेत दें "
        "(\"रिपोर्ट के मुताबिक\", \"पुलिस के अनुसार\")। आरोप को तथ्य की तरह न लिखें। निष्पक्ष भाषा, बिना भड़काऊ/सांप्रदायिक शब्दों के। सरल बोलचाल की हिंदी।")

def _call(parts, t=0.5):
    time.sleep(3)  # stay under free-tier requests/minute
    return sg.gemini_json(parts, t)

PLAN = ("आप भारतीय न्यूज़ बुलेटिन \"देश की नब्ज़\" के संपादक हैं। नीचे आज की ख़बरों के टुकड़े (अलग-अलग स्रोतों से) और भारत में ट्रेंडिंग खोजें हैं।\n"
        "काम: 16 तक अलग-अलग ख़बरें चुनें, महत्व के क्रम में। नियम: (1) एक ही घटना कई स्रोतों में हो तो उसे एक ख़बर गिनें और बाक़ी नंबर \"also\" में डालें; "
        "(2) लगभग आधी ख़बरें राजनीति/राष्ट्रीय, बाक़ी विश्व/व्यापार/खेल/मनोरंजन/तकनीक/विज्ञान/स्वास्थ्य से, पहली 10 में कम से कम 4 श्रेणियाँ; "
        "(3) वही चुनें जिनके टेक्स्ट में पर्याप्त तथ्य हों; (4) हाल के बुलेटिन के शीर्षकों जैसी ख़बरें न दोहराएँ।\n"
        "केवल JSON: {\"stories\":[{\"index\":0,\"also\":[3],\"category\":\"राजनीति|राष्ट्रीय|विश्व|व्यापार|खेल|मनोरंजन|तकनीक|विज्ञान|स्वास्थ्य\",\"headline\":\"<=9 शब्द की हेडलाइन\"}]}\n")

def plan(items, trends, recent):
    body = "ट्रेंडिंग खोजें:\n" + "\n".join("- " + t for t in trends) + "\n\nहाल के बुलेटिन शीर्षक:\n" + "\n".join("- " + t for t in recent if t)
    body += "\n\nख़बरें:\n" + "\n\n".join(f"[{i}] ({it['source']}{'/' + it['hint'] if it['hint'] else ''}) {it['title']}\n{it['text'][:450]}" for i, it in enumerate(items))
    res = _call([{"text": PLAN + "\n" + body}], 0.4)
    out, seen = [], set()
    for s in res.get("stories", []):
        try: i = int(s["index"])
        except Exception: continue
        if 0 <= i < len(items) and i not in seen:
            seen.add(i); out.append({"index": i, "also": [j for j in s.get("also", []) if isinstance(j, int) and 0 <= j < len(items)],
                                     "category": s.get("category", "राष्ट्रीय"), "headline": s.get("headline") or items[i]["title"]})
    return out

STORY = ("आप टीवी न्यूज़ बुलेटिन के लिए एक ख़बर की वॉइस-ओवर स्क्रिप्ट लिख रहे हैं। 7-9 पंक्तियाँ, हर पंक्ति 13-18 शब्द (कुल 115-150 शब्द)। "
         "क्रम: क्या हुआ, मुख्य ब्योरा, पृष्ठभूमि/संदर्भ, प्रतिक्रिया, आगे क्या। टेक्स्ट में तथ्य कम हों तो पंक्तियाँ कम रखें, कुछ न गढ़ें। कोई अभिवादन या समापन नहीं (वह अलग से जुड़ेगा)। " + FACT + "\n"
         "विज़ुअल: \"queries\" में 6 अंग्रेज़ी खोजें जिनसे विकिमीडिया कॉमन्स पर असली फ़ोटो मिलें: पहली 3 ख़बर की असली जगह/इमारत/संस्था के नाम (proper noun, जैसे \"Tihar Jail\", \"Supreme Court of India\"), "
         "बाक़ी 3 ज़्यादा आम (जैसे \"Delhi\", \"police station India\")। queries में कभी व्यक्ति/अभिनेता/फ़िल्म/ब्रांड का नाम नहीं। "
         "अगर ख़बर का मुख्य विषय कोई जाना-माना सार्वजनिक व्यक्ति (नेता, अभिनेता, खिलाड़ी) है तो \"person\" में उसका पूरा अंग्रेज़ी नाम, वरना \"\"। आरोपी, पीड़ित या आम नागरिक के लिए हमेशा \"\"। हादसे/मौत में भयावह चित्र न माँगें।\n"
         "केवल JSON: {\"lines\":[\"...\"],\"queries\":[\"...\"],\"person\":\"\"}\n")

def write_story(story, items):
    ids = [story["index"]] + story["also"][:2]
    text = "\n\n".join(f"({items[i]['source']}) {items[i]['title']}\n{items[i]['text']}" for i in ids)[:4500]
    res = _call([{"text": STORY + f"\nश्रेणी: {story['category']}\nहेडलाइन: {story['headline']}\n\nस्रोत-टेक्स्ट:\n{text}"}], 0.5)
    lines = [str(l).strip() for l in res.get("lines", []) if str(l).strip()]
    return {"lines": lines, "queries": [q for q in res.get("queries", []) if q][:6], "person": res.get("person", "") or ""}

FRAME = ("आप न्यूज़ बुलेटिन \"देश की नब्ज़\" के एंकर-स्क्रिप्ट राइटर हैं। नीचे आज की ख़बरों की हेडलाइन हैं। लिखें:\n"
         "\"intro\": 3 पंक्तियाँ (कुल 40-50 शब्द): अभिवादन, चैनल का नाम, बुलेटिन का नाम (दिया गया edition) और तारीख़, आज की ख़ास बात का एक संकेत।\n"
         "\"outro\": 3 पंक्तियाँ (कुल 30-40 शब्द): सार, दर्शकों का धन्यवाद, चैनल फ़ॉलो/सब्सक्राइब करने की अपील, \"नमस्कार\"।\n"
         "\"title\": यूट्यूब शीर्षक, 95 अक्षर तक, उसमें edition और तारीख़ हो, सबसे बड़ी ख़बर का संकेत हो, भ्रामक नहीं।\n"
         "\"description\": 3-4 वाक्य का सार + 6 हैशटैग।  \"tags\": 10 कीवर्ड (हिंदी+अंग्रेज़ी)।\n"
         "केवल JSON: {\"intro\":[\"..\"],\"outro\":[\"..\"],\"title\":\"..\",\"description\":\"..\",\"tags\":[\"..\"]}\n")

def write_frame(headlines, edition, date_str):
    res = _call([{"text": FRAME + f"\nedition: {edition}\nतारीख़: {date_str}\n\nहेडलाइन:\n" + "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))}], 0.6)
    return {"intro": [str(x) for x in res.get("intro", [])] or [f"नमस्कार, आप देख रहे हैं देश की नब्ज़। {edition}, {date_str}।"],
            "outro": [str(x) for x in res.get("outro", [])] or ["यह थीं आज की प्रमुख ख़बरें।", "देश की नब्ज़ को फ़ॉलो करना न भूलें।", "नमस्कार।"],
            "title": res.get("title") or f"आज की बड़ी ख़बरें | {edition} | {date_str}",
            "description": res.get("description", ""), "tags": res.get("tags", [])}
