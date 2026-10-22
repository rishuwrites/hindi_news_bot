import os
BASE = os.path.dirname(os.path.abspath(__file__))
SLOTS_IST = [(8, 0), (20, 0)]          # publish times (IST): 8 AM and 8 PM
W, H, FPS = 1920, 1080, 24
MIN_SECONDS = 520                       # hard minimum (8:30 = 510s, plus margin)
TARGET_SECONDS = 600                    # aim for ~10 minutes
MAX_SECONDS = 780                       # never longer than 13 min
MIN_STORIES, MAX_STORIES = 8, 14
WPS = 2.3                               # Hindi speech words/second (estimate only; real length is measured)
TOPIC_FEEDS = [(f"Google News {n}", f"https://news.google.com/rss/headlines/section/topic/{t}?hl=hi&gl=IN&ceid=IN:hi", n)
               for t, n in [("WORLD", "विश्व"), ("BUSINESS", "व्यापार"), ("SPORTS", "खेल"),
                            ("ENTERTAINMENT", "मनोरंजन"), ("TECHNOLOGY", "तकनीक"), ("SCIENCE", "विज्ञान"), ("HEALTH", "स्वास्थ्य")]]
# generic, always-available photo searches per category (used when a story has too few photos)
CATEGORY_GENERIC = {
    "राजनीति": ["Parliament of India", "Rashtrapati Bhavan", "Lok Sabha", "Supreme Court of India"],
    "राष्ट्रीय": ["India Gate New Delhi", "New Delhi street", "Indian Railways station", "Mumbai skyline"],
    "विश्व": ["United Nations headquarters", "airport terminal", "city skyline night", "diplomats meeting"],
    "व्यापार": ["Bombay Stock Exchange", "Reserve Bank of India", "Mumbai skyline", "market India"],
    "खेल": ["cricket stadium India", "Wankhede Stadium", "stadium crowd", "sports ground"],
    "मनोरंजन": ["Film City Mumbai", "cinema hall India", "Bollywood", "concert stage"],
    "तकनीक": ["data center", "ISRO", "smartphone", "technology office"],
    "विज्ञान": ["ISRO launch", "laboratory", "telescope", "satellite"],
    "स्वास्थ्य": ["hospital India", "doctor", "medicine", "AIIMS Delhi"],
}
DEFAULT_GENERIC = ["India Gate New Delhi", "New Delhi street", "Mumbai skyline", "Parliament of India"]
ORDINALS = ["पहली", "दूसरी", "तीसरी", "चौथी", "पाँचवीं", "छठी", "सातवीं", "आठवीं", "नौवीं", "दसवीं",
            "ग्यारहवीं", "बारहवीं", "तेरहवीं", "चौदहवीं"]
HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
