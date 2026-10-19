import os
CHANNEL_NAME = os.getenv("CHANNEL_NAME") or "देश की नब्ज़"
# (display name, rss url). Dead feeds are skipped automatically.
FEEDS = [
    ("BBC हिंदी", "https://feeds.bbci.co.uk/hindi/rss.xml"),
    ("Google News टॉप", "https://news.google.com/rss?hl=hi&gl=IN&ceid=IN:hi"),
    ("Google News भारत", "https://news.google.com/rss/headlines/section/topic/NATION?hl=hi&gl=IN&ceid=IN:hi"),
    ("Google News राजनीति", "https://news.google.com/rss/search?q=%E0%A4%B0%E0%A4%BE%E0%A4%9C%E0%A4%A8%E0%A5%80%E0%A4%A4%E0%A4%BF+when:1d&hl=hi&gl=IN&ceid=IN:hi"),
    ("The Hindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
    ("Indian Express", "https://indianexpress.com/section/india/feed/"),
    ("NDTV", "https://feeds.feedburner.com/ndtvnews-india-news"),
    ("Hindustan Times", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
]
TRENDS_URL = "https://trends.google.com/trending/rss?geo=IN"
SLOTS_IST = [(6, 0), (9, 0), (12, 0), (14, 30), (17, 0), (19, 0), (21, 0)]
GEMINI_MODEL = "gemini-2.5-flash"
W, H, FPS = 1080, 1920, 30
