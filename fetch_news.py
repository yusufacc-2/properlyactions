import json, feedparser, re, os, time, requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from openai import OpenAI

# Setup OpenAI
client = OpenAI(api_key=os.environ.get("PROPERLYAPIKEY"))

def get_sum(t, s):
    try: 
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Summarize this UK landlord news for a 10-year old. 2 simple bullets."},
                {"role": "user", "content": f"Title: {t}\n\nContent: {s}"}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except: return None

# 📸 NEW: Image Hunter Function
def hunt_image(url):
    try:
        # Visit the website briefly to find the 'og:image' meta tag
        r = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        # Use regex to find the og:image content (fastest way)
        match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', r.text)
        if not match:
            match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', r.text)
        return match.group(1) if match else None
    except:
        return None

UK_KEYWORDS = ["uk", "property", "landlord", "rent", "housing", "scotland", "england"]
FEEDS = [
    {"source": "Landlord Today", "url": "https://www.landlordtoday.co.uk/feed"},
    {"source": "The Negotiator", "url": "https://thenegotiator.co.uk/feed/"},
    {"source": "Property Investor Today", "url": "https://www.propertyinvestortoday.co.uk/feed"},
    {"source": "Estate Agent Today", "url": "https://www.estateagenttoday.co.uk/feed"},
]

def clean(t): return re.sub(r'<[^>]+>', '', t)[:800].strip() if t else ""

# Load old data to save AI summaries
existing_sums = {}
existing_imgs = {}
if os.path.exists("news.json"):
    try:
        with open("news.json", "r") as f:
            old = json.load(f)
            for a in old.get("articles", []):
                if a.get("ai_summary"): existing_sums[a["url"]] = a["ai_summary"]
                if a.get("image"): existing_imgs[a["url"]] = a["image"]
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
        
        # 1. Get/Keep AI Summary (Persistent)
        ais = existing_sums.get(u)
        if not ais:
            print(f"🤖 AI Summary for: {t[:40]}...")
            ais = get_sum(t, ds)
        
        # 2. Get/Hunt Proper Image
        img = existing_imgs.get(u)
        if not img:
            print(f"📸 Hunting Image for: {t[:40]}...")
            img = hunt_image(u)
            
        articles.append({
            "id": e.get("id", u),
            "title": t,
            "summary": ds,
            "ai_summary": ais,
            "image": img,
            "url": u,
            "source": f_info["source"],
            "published": pub.isoformat()
        })

articles.sort(key=lambda x: x["published"], reverse=True)
with open("news.json", "w") as f:
    json.dump({"last_updated": datetime.now(timezone.utc).isoformat(), "article_count": len(articles), "articles": articles}, f, indent=2)
print("✅ DONE")
