#!/usr/bin/env python3
"""MoltStreet RSS Aggregator
Fetches crypto news from RSS feeds, scores relevance, and posts drafts to WordPress.
Requires: pip install feedparser requests (or use stdlib xml.etree + urllib)
"""
import os, json, time, hashlib, argparse
from datetime import datetime
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

# --- Configuration ---
# Set these via environment or edit directly
WP_SITES = {
    "crypto": {
        "url": os.environ.get("WP_CRYPTO_URL", "https://crypto-analisi.infinityfreeapp.com"),
        "user": os.environ.get("WP_CRYPTO_USER", "admin"),
        "password": os.environ.get("WP_CRYPTO_PASS", ""),
    },
    "ai": {
        "url": os.environ.get("WP_AI_URL", "https://ai-notizie-italia.infinityfreeapp.com"),
        "user": os.environ.get("WP_AI_USER", "admin"),
        "password": os.environ.get("WP_AI_PASS", ""),
    },
    "basket": {
        "url": os.environ.get("WP_BASKET_URL", "https://basket-italia.infinityfreeapp.com"),
        "user": os.environ.get("WP_BASKET_USER", "admin"),
        "password": os.environ.get("WP_BASKET_PASS", ""),
    },
}

FEEDS = {
    "crypto": [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed",
        "https://thedefiant.io/feed",
    ],
    "ai": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://venturebeat.com/category/ai/feed/",
    ],
    "basket": [
        "https://www.gazzetta.it/rss/basket.xml",
        "https://www.lalaziosiamonoi.it/feed",
    ],
}

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".rss_cache.json")


def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_feeds(site_key):
    """Fetch and parse RSS feeds for a site."""
    urls = FEEDS.get(site_key, [])
    articles = []

    for feed_url in urls:
        try:
            req = Request(feed_url, headers={"User-Agent": "MoltStreetRSS/1.0"})
            with urlopen(req, timeout=15) as resp:
                data = resp.read()

            root = ET.fromstring(data)

            # Handle RSS 2.0
            for item in root.iter("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                desc = (item.findtext("description") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()

                if title and link:
                    # Extract source domain
                    source = feed_url.split("/")[2].replace("www.", "")
                    articles.append({
                        "title": title,
                        "link": link,
                        "summary": desc[:500],
                        "pub_date": pub,
                        "source": source,
                    })

            # Handle Atom feeds
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                title = (entry.findtext("atom:title", "", ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                summary = (entry.findtext("atom:summary", "", ns) or "").strip()
                pub = (entry.findtext("atom:published", "", ns) or
                       entry.findtext("atom:updated", "", ns) or "").strip()

                if title and link:
                    source = feed_url.split("/")[2].replace("www.", "")
                    articles.append({
                        "title": title,
                        "link": link,
                        "summary": summary[:500],
                        "pub_date": pub,
                        "source": source,
                    })

        except Exception as e:
            print(f"  [WARN] Feed failed {feed_url[:50]}: {e}")

    return articles


def score_article(article, site_key):
    """Score article relevance 0-100."""
    score = 50.0
    title = (article.get("title") or "").lower()
    summary = (article.get("summary") or "").lower()
    text = title + " " + summary

    # Keyword boosts by site
    keywords = {
        "crypto": {
            "high": ["bitcoin", "ethereum", "solana", "defi", "crypto", "blockchain",
                      "token", "airdrop", "staking", "nft", "web3", "dapp"],
            "low": ["stock", "forex", "commodity", "real estate"],
        },
        "ai": {
            "high": ["artificial intelligence", "machine learning", "gpt", "llm",
                     "neural", "deep learning", "chatbot", "copilot", "openai", "anthropic"],
            "low": ["sports", "cooking", "fashion"],
        },
        "basket": {
            "high": ["serie a", "nba", "euroleague", "basket", "pallacanestro",
                     "olimpia milano", "virtus bologna"],
            "low": ["calcio", "tennis"],
        },
    }

    site_kw = keywords.get(site_key, {"high": [], "low": []})
    for kw in site_kw.get("high", []):
        if kw in text:
            score += 15
    for kw in site_kw.get("low", []):
        if kw in text:
            score -= 20

    # Title relevance (title match > body match)
    for kw in site_kw.get("high", []):
        if kw in title:
            score += 10

    # Recency bonus (rough check)
    now_str = datetime.now().strftime("%Y-%m-%d")
    if now_str in article.get("pub_date", ""):
        score += 10

    return max(0, min(100, round(score)))


def post_to_wp(article, site_key):
    """Post article as draft to WordPress via REST API."""
    import json as _json
    from urllib.request import urlopen, Request

    cfg = WP_SITES[site_key]
    if not cfg.get("password"):
        print(f"  [SKIP] No WP password for {site_key}")
        return None

    source = article.get("source", "")
    link = article.get("link", "")
    content = (
        f'<p><em>Fonte: <a href="{link}" target="_blank">{source}</a></em></p>'
        f'<p>{article.get("summary", "")}</p>'
    )

    try:
        post_data = _json.dumps({
            "title": article["title"],
            "content": content,
            "status": "draft",
        }).encode()

        req = Request(
            f"{cfg['url']}/wp-json/wp/v2/posts",
            data=post_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "MoltStreetRSS/1.0",
            },
            method="POST",
        )

        # Basic auth
        import base64
        creds = base64.b64encode(f"{cfg['user']}:{cfg['password']}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")

        with urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            post_id = result.get("id")
            print(f"  ✅ POSTED (ID:{post_id}): {article['title'][:60]}")
            return post_id

    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return None


def run(site="all", max_posts=5, dry_run=False):
    """Main aggregator run."""
    print(f"📰 MoltStreet RSS Aggregator | {datetime.now():%Y-%m-%d %H:%M}")
    cache = load_cache()
    sites = list(WP_SITES.keys()) if site == "all" else [site]
    total = 0

    for sk in sites:
        print(f"\n{'='*50}")
        print(f"  SITE: {sk.upper()}")
        print(f"{'='*50}")

        articles = fetch_feeds(sk)
        print(f"  Fetched {len(articles)} articles")

        scored = sorted(
            [(score_article(a, sk), a) for a in articles],
            key=lambda x: x[0],
            reverse=True,
        )

        n = 0
        for score, article in scored:
            if n >= max_posts or score < 40:
                continue

            uid = hash_url(article["link"])
            if uid in cache:
                print(f"  [CACHED] {article['title'][:50]}")
                continue

            print(f"  [{score}] {article['title'][:65]}")

            if not dry_run:
                pid = post_to_wp(article, sk)
                if pid:
                    cache[uid] = {"posted": datetime.now().isoformat(), "site": sk}
                    save_cache(cache)
                    n += 1
                    total += 1
                    time.sleep(2)  # Rate limit
            else:
                n += 1
                total += 1

    print(f"\n✅ Done: {total} articles processed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoltStreet RSS Aggregator")
    parser.add_argument("--site", default="all", choices=["all", "ai", "basket", "crypto"])
    parser.add_argument("--max", type=int, default=5, help="Max posts per site")
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    args = parser.parse_args()
    run(args.site, args.max, args.dry_run)
