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
    """The Ultimate Image Hunter: Scans meta tags, link attributes, and body content."""
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. OpenGraph (Highly reliable)
            og_image = soup.find("meta", property="og:image")
            if og_image and og_image.get("content"): return og_image["content"]
            
            # 2. Twitter Cards
            tw_image = soup.find("meta", name="twitter:image")
            if tw_image and tw_image.get("content"): return tw_image["content"]
            
            # 3. Schema.org / itemprop
            item_image = soup.find("meta", itemprop="image")
            if item_image and item_image.get("content"): return item_image["content"]
            
            # 4. Link image_src
            link_image = soup.find("link", rel="image_src")
            if link_image and link_image.get("href"): return link_image["href"]
            
            # 4. Body Content Scan (The Ultimate Fallback)
            # We look for the first img tag that isn't an icon
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if not src or "data:image" in src: continue
                
                # Check for standard extensions
                if any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    # Resolve relative URLs
                    from urllib.parse import urljoin
                    full_url = urljoin(url, src)
                    return full_url
                    
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
            url = entry.link
            if url in seen_urls: continue
            
            # Date check
            published_parsed = entry.get('published_parsed')
            if published_parsed:
                dt = datetime.fromtimestamp(time.mktime(published_parsed))
                if dt < cutoff: continue
            
            # Keyword filter
            text = (entry.title + " " + entry.get('summary', '')).lower()
            if not any(kw in text for kw in KEYWORDS): continue
            
            source = "Landlord Today" if "landlordtoday" in feed_url else "The Negotiator"
            
            # Clean the summary HTML immediately to ensure news.json has clean text
            raw_summary = entry.get('summary', '')
            clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text().strip()
            
            article = {
                "id": url,
                "title": entry.title,
                "summary": clean_summary,
                "url": url,
                "source": source,
                "published": entry.get('published', datetime.now().isoformat()),
                "image": None,
                "ai_summary": None
            }
            all_articles.append(article)
            seen_urls.add(url)

    print(f"Found {len(all_articles)} articles. Processing ENTIRE list (No limits)...")
    
    api_key = os.environ.get("PROPERLYAPIKEY")
    
    for i, article in enumerate(all_articles):
        # 1. Hunt Image (100% logic)
        img = get_preview_image(article["url"])
        if img:
            article["image"] = img
            
        # 2. AI Summarize
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                
                # Strip HTML for cleaner AI summarizes
                clean_text = BeautifulSoup(article['summary'], "html.parser").get_text()
                prompt = f"Summarize this UK property news in 2 punchy bullet points:\nTitle: {article['title']}\nContent: {clean_text}"
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                article["ai_summary"] = response.choices[0].message.content
                print(f"[{i+1}/{len(all_articles)}] Success: {article['title'][:30]}...")
            except Exception as e:
                print(f"AI Error for {article['title']}: {e}")

    output = {
        "last_updated": datetime.now().isoformat(),
        "article_count": len(all_articles),
        "articles": all_articles
    }
    
    with open("news.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(all_articles)} stories to news.json")

if __name__ == "__main__":
    fetch_and_summarize()
