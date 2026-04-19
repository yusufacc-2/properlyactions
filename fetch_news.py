import json
import feedparser
import re
import os
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import google.generativeai as genai

# Configuration
CUTOFF_DATE = datetime.now(timezone.utc) - timedelta(days=60)

# YOUR API KEY IS NOW HARDCODED HERE
GEMINI_API_KEY = "AIzaSyAcRmpb_-Rj5aj8bVF_n1kLTJCa4CrGUaI"

# Initialize Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI Initialized Successfully")
except Exception as e:
    print(f"❌ Failed to init Gemini: {e}")
    model = None

UK_KEYWORDS = [
    "uk", "united kingdom", "england", "scotland", "wales",
    "british", "britain", "london", "landlord", "tenant",
    "renter", "lettings", "leasehold", "stamp duty", "rightmove", 
    "zoopla", "section 21", "section 8", "buy-to-let", "hmrc", 
    "council tax", "renters reform", "assured shorthold"
]

FEEDS = [
    {"source": "Landlord Today", "url": "https://www.landlordtoday.co.uk/feed"},
    {"source": "The Negotiator", "url": "https://thenegotiator.co.uk/feed/"},
    {"source": "Property Investor Today", "url": "https://www.propertyinvestortoday.co.uk/feed"},
    {"source": "Estate Agent Today", "url": "https://www.estateagenttoday.co.uk/feed"},
]

def clean_html(text):
    if not text: return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'&amp;', '&', clean).strip()
    return clean[:1000]

def get_ai_summary(title, summary):
    if not model: return None
    try:
        # Instruction for the "Baby Words" summary
        prompt = f"""
        Summarize this UK landlord news for a 10-year old.
        Keep it to 2-3 very short bullet points.
        Start with a '🚨 ACTION' or '✅ CALM' emoji based on if the landlord needs to do anything.
        
        Title: {title}
        Content: {summary}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return None

# Load old data to keep existing summaries
existing_data = {}
if os.path.exists("news.json"):
    try:
        with open("news.json", "r") as f:
            old = json.load(f)
            for a in old.get("articles", []):
                if a.get("ai_summary"):
                    existing_data[a["url"]] = a["ai_summary"]
    except: pass

articles = []
seen_urls = set()

for f_info in FEEDS:
    feed = feedparser.parse(f_info["url"])
    for entry in feed.entries:
        url = entry.get("link", "")
        if url in seen_urls: continue
        seen_urls.add(url)
        
        pub_date = parsedate_to_datetime(entry.get('published', datetime.now(timezone.utc).isoformat()))
        if pub_date.tzinfo is None: pub_date = pub_date.replace(tzinfo=timezone.utc)
        if pub_date < CUTOFF_DATE: continue
        
        title = clean_html(entry.get("title", ""))
        desc = clean_html(entry.get("summary", entry.get("description", "")))
        
        if not any(kw in (title + desc).lower() for kw in UK_KEYWORDS): continue
        
        # Get AI summary if missing
        ai_sum = existing_data.get(url)
        if not ai_sum and model:
            print(f"🤖 AI Summarizing: {title[:40]}...")
            ai_sum = get_ai_summary(title, desc)
            
        articles.append({
            "id": entry.get("id", url),
            "title": title,
            "summary": desc,
            "ai_summary": ai_sum,
            "url": url,
            "source": f_info["source"],
            "published": pub_date.isoformat()
        })

articles.sort(key=lambda x: x["published"], reverse=True)
with open("news.json", "w") as f:
    json.dump({"last_updated": datetime.now(timezone.utc).isoformat(), "articles": articles}, f, indent=2)

print(f"✅ DONE: {len(articles)} articles saved to news.json")
