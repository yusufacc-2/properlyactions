import json, feedparser, re, os, time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from openai import OpenAI

# Setup OpenAI with your PROPERLYAPIKEY secret
client = OpenAI(api_key=os.environ.get("PROPERLYAPIKEY"))

def get_sum(t, s):
    try: 
        response = client.chat.completions.create(
            model="gpt-4o-mini", # <--- THE CHEAPEST MODEL WORLDWIDE
            messages=[
                {"role": "system", "content": "Summarize this UK landlord news for a 10-year old. 2 simple bullets."},
                {"role": "user", "content": f"Title: {t}\n\nContent: {s}"}
            ],
            max_tokens=100 # Saves you even more money by keeping it short
        )
        return response.choices[0].message.content.strip()
    except: return None

# ... (Rest of the scraping logic remains the same)
UK_KEYWORDS = ["uk", "property", "landlord", "rent", "housing"]
FEEDS = [
    {"source": "Landlord Today", "url": "https://www.landlordtoday.co.uk/feed"},
    {"source": "The Negotiator", "url": "https://thenegotiator.co.uk/feed/"},
    {"source": "Property Investor Today", "url": "https://www.propertyinvestortoday.co.uk/feed"},
    {"source": "Estate Agent Today", "url": "https://www.estateagenttoday.co.uk/feed"},
]

def clean(t): return re.sub(r'<[^>]+>', '', t)[:800].strip() if t else ""

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
for f_info in FEEDS:
    d = feedparser.parse(f_info["url"])
    for e in d.entries:
        u = e.get("link", "")
        if u in seen: continue
        seen.add(u)
        pub = parsedate_to_datetime(e.get('published', datetime.now(timezone.utc).isoformat()))
        if pub.tzinfo is None: pub = pub.replace(tzinfo=timezone.utc)
        if pub < (datetime.now(timezone.utc) - timedelta(days=60)): continue
        t, ds = clean(e.get("title", "")), clean(e.get("summary", e.get("description", "")))
        if not any(k in (t + ds).lower() for k in UK_KEYWORDS): continue
        ais = existing.get(u)
        if not ais:
            print(f"🤖 Cheapest AI Summarizing: {t[:40]}...")
            ais = get_sum(t, ds)
        articles.append({"id": e.get("id", u), "title": t, "summary": ds, "ai_summary": ais, "url": u, "source": f_info["source"], "published": pub.isoformat()})

articles.sort(key=lambda x: x["published"], reverse=True)
with open("news.json", "w") as f:
    json.dump({"last_updated": datetime.now(timezone.utc).isoformat(), "article_count": len(articles), "articles": articles}, f, indent=2)
print("✅ DONE")
