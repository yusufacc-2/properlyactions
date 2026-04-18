import json
import feedparser
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

CUTOFF_DATE = datetime.now(timezone.utc) - timedelta(days=60)

# UK keywords — article must contain at least one to pass
UK_KEYWORDS = [
    "uk", "united kingdom", "england", "scotland", "wales",
    "british", "britain", "london", "landlord", "tenant",
    "renter", "renters", "lettings", "leasehold", "freehold",
    "stamp duty", "rightmove", "zoopla", "section 21", "section 8",
    "rental", "buy-to-let", "buy to let", "hmrc", "council tax",
    "planning permission", "housing benefit", "universal credit",
    "renters reform", "deposit", "assured shorthold"
]

# All UK-based property news sources
FEEDS = [
    {"source": "Landlord Today", "url": "https://www.landlordtoday.co.uk/feed"},
    {"source": "Property Investor Today", "url": "https://www.propertyinvestortoday.co.uk/feed"},
    {"source": "The Negotiator", "url": "https://thenegotiator.co.uk/feed/"},
    {"source": "Estate Agent Today", "url": "https://www.estateagenttoday.co.uk/feed"},
    {"source": "Property Wire", "url": "https://www.propertywire.com/feed/"},
]

def clean_html(text):
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'&amp;', '&', clean)
    clean = re.sub(r'&nbsp;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:500]

def parse_date(entry):
    for field in ['published', 'updated']:
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except:
                try:
                    return datetime.fromisoformat(raw.replace('Z', '+00:00'))
                except:
                    pass
    return datetime.now(timezone.utc)

def extract_image(entry):
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url')
    for enc in entry.get('enclosures', []):
        if 'image' in enc.get('type', ''):
            return enc.get('url')
    for media in entry.get('media_content', []):
        if 'image' in media.get('type', ''):
            return media.get('url')
    return None

def is_uk_relevant(title, summary):
    combined = (title + " " + summary).lower()
    return any(kw in combined for kw in UK_KEYWORDS)

articles = []
seen_urls = set()

for feed_info in FEEDS:
    try:
        feed = feedparser.parse(feed_info["url"])
        count = 0
        skipped = 0
        for entry in feed.entries:
            pub_date = parse_date(entry)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            if pub_date < CUTOFF_DATE:
                continue
            url = entry.get("link", "")
            if url in seen_urls:
                continue
            title = clean_html(entry.get("title", ""))
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            # UK relevance filter
            if not is_uk_relevant(title, summary):
                skipped += 1
                continue
            seen_urls.add(url)
            articles.append({
                "id": entry.get("id", url),
                "title": title,
                "summary": summary,
                "url": url,
                "source": feed_info["source"],
                "category": "Industry",
                "published": pub_date.isoformat(),
                "image": extract_image(entry)
            })
            count += 1
        print(f"OK: {count} UK articles from {feed_info['source']} ({skipped} non-UK skipped)")
    except Exception as e:
        print(f"FAILED {feed_info['source']}: {e}")

articles.sort(key=lambda x: x.get("published", ""), reverse=True)

output = {
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "article_count": len(articles),
    "articles": articles
}

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nDONE: {len(articles)} UK-only articles (last 60 days) written to news.json")
