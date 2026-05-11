"""
research.py — Fetches AI & Tech news from free RSS feeds
No API key needed. Saves to .tmp/research.json
"""

import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

RSS_FEEDS = [
    ("The Verge - AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("TechCrunch - AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("Ars Technica - AI", "https://feeds.arstechnica.com/arstechnica/index"),
    ("VentureBeat - AI", "https://venturebeat.com/category/ai/feed/"),
]

MAX_ARTICLES = 10  # total articles to collect


def fetch_feed(name, url):
    articles = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()
        root = ET.fromstring(content)

        # Handle both RSS and Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        for item in items[:3]:  # max 3 per source
            title = (
                item.findtext("title")
                or item.findtext("atom:title", namespaces=ns)
                or ""
            ).strip()
            summary = (
                item.findtext("description")
                or item.findtext("atom:summary", namespaces=ns)
                or ""
            ).strip()
            link = (
                item.findtext("link")
                or (item.find("atom:link", ns).get("href") if item.find("atom:link", ns) is not None else "")
            ).strip()

            # Strip HTML tags simply
            import re
            summary = re.sub(r"<[^>]+>", "", summary)[:300]

            if title:
                articles.append({
                    "source": name,
                    "title": title,
                    "summary": summary,
                    "link": link,
                })
    except Exception as e:
        print(f"  ⚠️  Could not fetch {name}: {e}")
    return articles


def main():
    print("🔍 Fetching AI & Tech news from RSS feeds...\n")
    all_articles = []

    for name, url in RSS_FEEDS:
        print(f"  Fetching {name}...")
        articles = fetch_feed(name, url)
        all_articles.extend(articles)
        print(f"  ✅ Got {len(articles)} articles")

    # Trim to max
    all_articles = all_articles[:MAX_ARTICLES]

    # Save
    Path(".tmp").mkdir(exist_ok=True)
    data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "topic": "AI & Tech News",
        "articles": all_articles,
    }
    with open(".tmp/research.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Saved {len(all_articles)} articles to .tmp/research.json")


if __name__ == "__main__":
    main()
