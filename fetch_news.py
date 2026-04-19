import json, feedparser, re, os, time, google.generativeai as genai
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

CUTOFF_DATE = datetime.now(timezone.utc) - timedelta(days=60)
GEMINI_API_KEY = "AIzaSyAcRmpb_-Rj5aj8bVF_n1kLTJCa4CrGUaI"

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except: model = None
else: model = None

FEEDS = [
    {"source": "Landlord Today", "url": "https://www.landlordtoday.co.uk/feed"},
    {"source": "The Negotiator", "url": "https://thenegotiator.co.uk/feed/"},
    {"source": "Property Investor Today", "url": "https://www.propertyinvestortoday.co.uk/feed"},
    {"source": "Estate Agent Today", "url": "https://www.estateagenttoday.co.uk/feed"},
]

def clean(t): return re.sub(r'<[^>]+>', '', t)[:800].strip() if t else ""

def get_sum(t, s):
    if not model: return None
    try: 
        res = model.generate_content(f"Explain this UK landlord news for a 10yo. 2 bullets. Title: {t} Content: {s}")
        return res.text.strip()
    except: return None

existing = {}
if os.path.exists("news.json"):
    try:
        with open("news.json", "r") as f:
            old = json.load(f)
            for a in old.get("articles", []):
                if a.get("ai_summary"): existing[a["url"]] = a["ai_summary"]
    except: pass

articles = []
seen = set()
for f in FEEDS:
    d = feedparser.parse(f["url"])
    for e in d.entries:
        u = e.get("link", "")
        if u in seen: continue
        seen.add(u)
        pub = parsedate_to_datetime(e.get('published', datetime.now(timezone.utc).isoformat()))
        if pub.tzinfo is None: pub = pub.replace(tzinfo=timezone.utc)
        if pub < CUTOFF_DATE: continue
        t, ds = clean(e.get("title", "")), clean(e.get("summary", e.get("description", "")))
        if not any(k in (t + ds).lower() for k in ["uk", "property", "landlord", "rent"]): continue
        ais = existing.get(u)
        if not ais and model:
            print(f"🤖 Summarizing: {t[:30]}...")
            ais = get_sum(t, ds)
            time.sleep(2)
        articles.append({"id": e.get("id", u), "title": t, "summary": ds, "ai_summary": ais, "url": u, "source": f["source"], "published": pub.isoformat()})

articles.sort(key=lambda x: x["published"], reverse=True)
with open("news.json", "w") as f:
    json.dump({"last_updated": datetime.now(timezone.utc).isoformat(), "article_count": len(articles), "articles": articles}, f, indent=2)
print("✅ DONE")
