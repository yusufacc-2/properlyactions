import json
import feedparser
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Only keep articles from last 3 months
CUTOFF_DATE = datetime.now(timezone.utc) - timedelta(days=90)

# Best sources — GOV.UK first (most authoritative)
FEEDS = [
    {
        "source": "GOV.UK — Housing & Legislation",
        "category": "Official",
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=landlord+tenant+rental&organisations%5B%5D=department-for-levelling-up-housing-and-communities"
    },
    {
        "source": "GOV.UK — Private Renting",
        "category": "Official",
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=private+renting+eviction+section+21"
    },
    {
        "source": "GOV.UK — Housing Benefits & Tax",
        "category": "Official",
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=housing+benefit+stamp+duty+rental+income"
    },
    {
        "source": "Landlord Today",
        "category": "Industry",
        "url": "https://www.landlordtoday.co.uk/feed"
    },
    {
        "source": "Property Investor Today",
        "category": "Industry",
        "url": "https://www.propertyinvestortoday.co.uk/feed"
    },
    {
        "source": "The Negotiator",
        "category": "Industry",
        "url": "https://thenegotiator.co.uk/feed/"
    },
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

articles = []
seen_urls = set()

for feed_info in FEEDS:
    try:
        feed = feedparser.parse(feed_info["url"])
        count = 0
        for entry in feed.entries:
            pub_date = parse_date(entry)

            # Make timezone-aware if needed
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)

            # Skip articles older than 3 months
            if pub_date < CUTOFF_DATE:
                continue

            url = entry.get("link", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)

            articles.append({
                "id": entry.get("id", url),
                "title": clean_html(entry.get("title", "No title")),
                "summary": clean_html(entry.get("summary", entry.get("description", ""))),
                "url": url,
                "source": feed_info["source"],
                "category": feed_info["category"],
                "published": pub_date.isoformat(),
                "image": extract_image(entry)
            })
            count += 1

        print(f"OK [{feed_info['category']}] {count} articles (last 3 months) from {feed_info['source']}")
    except Exception as e:
        print(f"FAILED {feed_info['source']}: {e}")

# Sort newest first
articles.sort(key=lambda x: x.get("published", ""), reverse=True)

output = {
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "article_count": len(articles),
    "articles": articles
}

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nDONE: {len(articles)} articles (last 3 months) written to news.json")
