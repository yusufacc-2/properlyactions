import json
import feedparser
from datetime import datetime, timezone

# --- RSS Feeds (100% free, no API key) ---
FEEDS = [
    {
        "source": "Landlord Today",
        "url": "https://www.landlordtoday.co.uk/feed"
    },
    {
        "source": "Property Investor Today",
        "url": "https://www.propertyinvestortoday.co.uk/feed"
    },
    {
        "source": "GOV.UK Housing",
        "url": "https://www.gov.uk/search/news-and-communications.atom?keywords=landlord&organisations%5B%5D=department-for-levelling-up-housing-and-communities"
    },
    {
        "source": "The Negotiator",
        "url": "https://thenegotiator.co.uk/feed/"
    },
]

articles = []

for feed_info in FEEDS:
    try:
        feed = feedparser.parse(feed_info["url"])
        for entry in feed.entries[:5]:  # Top 5 per source
            articles.append({
                "id": entry.get("id", entry.get("link", "")),
                "title": entry.get("title", "No title"),
                "summary": entry.get("summary", entry.get("description", ""))[:300],
                "url": entry.get("link", ""),
                "source": feed_info["source"],
                "published": entry.get("published", str(datetime.now(timezone.utc))),
                "image": next(
                    (enc.get("url") for enc in entry.get("enclosures", []) if "image" in enc.get("type", "")),
                    None
                )
            })
        print(f"Fetched {len(feed.entries[:5])} from {feed_info['source']}")
    except Exception as e:
        print(f"Failed {feed_info['source']}: {e}")

# Sort newest first
articles.sort(key=lambda x: x["published"], reverse=True)

output = {
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "article_count": len(articles),
    "articles": articles
}

with open("news.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"Done! {len(articles)} articles saved to news.json")
