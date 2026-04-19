import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

# RSS Feeds
FEEDS = [
    "https://www.landlordtoday.co.uk/rss",
    "https://thenegotiator.co.uk/feed/"
]

KEYWORDS = ["landlord", "rent", "property", "tenancy", "letting", "housing", "tax", "regulation", "uk"]

def get_preview_image(url):
    """The Image Hunter: Extracts og:image from the article URL."""
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for OpenGraph image
            og_image = soup.find("meta", property="og:image")
            if og_image:
                return og_image["content"]
            # Fallback to Twitter image
            tw_image = soup.find("meta", name="twitter:image")
            if tw_image:
                return tw_image["content"]
    except Exception as e:
        print(f"Error hunting image for {url}: {e}")
    return None

def fetch_and_summarize():
    all_articles = []
    seen_urls = set()
    
    # 30-day cutoff
    cutoff = datetime.now() - timedelta(days=30)
    
    print(f"Fetching news from {len(FEEDS)} sources...")
    
    for feed_url in FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            # Basic validation
            url = entry.link
            if url in seen_urls: continue
            
            # Date check
            published_parsed = entry.get('published_parsed')
            if published_parsed:
                dt = datetime.fromtimestamp(time.mktime(published_parsed))
                if dt < cutoff: continue
            
            # Keyword filter (Check title and summary)
            text = (entry.title + " " + entry.get('summary', '')).lower()
            if not any(kw in text for kw in KEYWORDS): continue
            
            # Identify Source
            source = "Landlord Today" if "landlordtoday" in feed_url else "The Negotiator"
            
            # It's a valid landlord article!
            article = {
                "id": url,
                "title": entry.title,
                "summary": entry.get('summary', ''),
                "url": url,
                "source": source,
                "published": entry.get('published', datetime.now().isoformat()),
                "image": None,
                "ai_summary": None
            }
            
            all_articles.append(article)
            seen_urls.add(url)

    print(f"Found {len(all_articles)} relevant articles. Hunting images...")
    
    # Summarization with OpenAI (If available)
    api_key = os.environ.get("PROPERLYAPIKEY")
    
    # Image Hunting & AI Summarization
    for i, article in enumerate(all_articles[:15]): # Limit to top 15 for speed/cost
        # 1. Hunt Image
        img = get_preview_image(article["url"])
        if img:
            article["image"] = img
            
        # 2. AI Summarize
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                
                prompt = f"Provide a brief, professional 2-bullet summary for this UK landlord news article:\nTitle: {article['title']}\nContent: {article['summary']}"
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                article["ai_summary"] = response.choices[0].message.content
            except Exception as e:
                print(f"AI Error for {article['title']}: {e}")

    # Output to news.json
    output = {
        "last_updated": datetime.now().isoformat(),
        "article_count": len(all_articles),
        "articles": all_articles
    }
    
    with open("news.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Successfully saved {len(all_articles)} articles to news.json")

if __name__ == "__main__":
    fetch_and_summarize()
