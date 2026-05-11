import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

RSS_FEEDS = [
    # Tech / AI
    ("Hacker News",  "Tech",      "https://hnrss.org/frontpage"),
    ("BBC Tech",     "Tech",      "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    # Marketing
    ("HubSpot",      "Marketing", "https://blog.hubspot.com/marketing/rss.xml"),
    # India News
    ("NDTV India",   "India",     "https://feeds.feedburner.com/ndtvnews-india-news"),
    ("Times of India", "India",   "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
    # Fashion
    ("Fashionista",  "Fashion",   "https://fashionista.com/feed"),
    ("WWD",          "Fashion",   "https://wwd.com/feed/"),
]


def _tag(text, tag):
    m = re.search(rf"<{tag}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", text, re.S)
    return m.group(1).strip() if m else ""


def _parse_with_regex(xml_text, source, category):
    """Fallback parser for feeds with unescaped characters that break ET."""
    articles = []
    for item in re.findall(r"<item[^>]*>(.*?)</item>", xml_text, re.S):
        articles.append({
            "source":      source,
            "category":    category,
            "title":       _tag(item, "title")[:200],
            "link":        _tag(item, "link")[:500],
            "description": _tag(item, "description")[:600],
        })
    return articles


def fetch_feed(source, category, url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
        xml_bytes = resp.read()

    # strip control characters illegal in XML
    xml_bytes = bytes(b for b in xml_bytes if b >= 0x20 or b in (0x09, 0x0A, 0x0D))

    try:
        root = ET.fromstring(xml_bytes)
        articles = []
        for item in root.findall(".//item"):
            articles.append({
                "source":      source,
                "category":    category,
                "title":       (item.findtext("title") or "").strip(),
                "link":        (item.findtext("link")  or "").strip(),
                "description": (item.findtext("description") or "")[:600].strip(),
            })
        return articles
    except ET.ParseError:
        return _parse_with_regex(xml_bytes.decode("utf-8", errors="ignore"), source, category)


articles = []
counts = {}
for source, category, url in RSS_FEEDS:
    try:
        items = fetch_feed(source, category, url)
        articles.extend(items)
        counts[source] = len(items)
        print(f"  [{category}] {source}: {len(items)} articles")
    except Exception as e:
        print(f"  [{category}] {source}: failed — {e}")

Path(".tmp").mkdir(exist_ok=True)
out = Path(".tmp/research.json")
out.write_text(json.dumps({
    "fetched_at": datetime.now().isoformat(),
    "articles": articles,
}, indent=2))

print(f"\nSaved {len(articles)} articles to {out}")
