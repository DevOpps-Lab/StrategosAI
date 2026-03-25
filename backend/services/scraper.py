"""Web scraping utilities: HTTP fetch, HTML cleaning, link extraction, and Multi-Source APIs."""

import re
import html
import urllib.parse
from urllib.parse import urljoin, urlparse
import feedparser
import httpx
from bs4 import BeautifulSoup


# Reusable client — avoids creating a new TCP connection per request
_client = None


async def _get_client() -> httpx.AsyncClient:
    """Get or create a shared async HTTP client for connection reuse."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=8.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
    return _client


# ==========================================
# CORE WEB SCRAPING ALGORITHMS
# ==========================================

async def fetch_page(url: str, timeout: float = 8.0) -> tuple[str, int]:
    """Fetch a URL and return (html_content, status_code)."""
    client = await _get_client()
    try:
        resp = await client.get(url, timeout=timeout)
        return resp.text, resp.status_code
    except Exception as e:
        print(f"[SCRAPER] Error fetching {url}: {e}")
        return "", 500


def html_to_markdown(html: str) -> str:
    """Convert HTML to clean, readable text/markdown."""
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "iframe", "noscript"]):
        tag.decompose()

    lines = []
    for elem in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote"]):
        text = elem.get_text(strip=True)
        if not text:
            continue
        tag = elem.name
        if tag == "h1":
            lines.append(f"# {text}")
        elif tag == "h2":
            lines.append(f"## {text}")
        elif tag == "h3":
            lines.append(f"### {text}")
        elif tag in ("h4", "h5", "h6"):
            lines.append(f"#### {text}")
        elif tag == "li":
            lines.append(f"- {text}")
        elif tag == "blockquote":
            lines.append(f"> {text}")
        else:
            lines.append(text)

    content = "\n\n".join(lines)
    # Collapse excessive whitespace
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def extract_title(html: str) -> str:
    """Extract the page title from HTML."""
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract and normalize all internal links from a page."""
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc
    links = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        # Skip anchors, mailto, javascript, etc.
        if href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        # Only keep same-domain links
        if parsed.netloc == base_domain:
            # Normalize: strip fragment, keep path
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean.endswith("/"):
                clean = clean[:-1]
            links.add(clean)

    return sorted(links)


# ==========================================
# MULTI-SOURCE SCRAPING (REDDIT, NEWS, JOBS)
# ==========================================

async def fetch_reddit_data(competitor_name: str) -> str:
    """Search Reddit for the competitor and return formatted community sentiment."""
    if not competitor_name:
        return ""
    
    query = urllib.parse.quote(competitor_name)
    url = f"https://www.reddit.com/search.json?q={query}&sort=relevance&t=year&limit=10"
    
    client = await _get_client()
    try:
        resp = await client.get(url, timeout=10.0)
        if resp.status_code != 200:
            return ""
            
        data = resp.json()
        posts = data.get("data", {}).get("children", [])
        
        md_lines = [f"# Reddit Discussions about {competitor_name}"]
        for p in posts:
            post_data = p.get("data", {})
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")[:300] # Limit selftext
            subreddit = post_data.get("subreddit_name_prefixed", "")
            score = post_data.get("score", 0)
            
            if title:
                md_lines.append(f"## {title} ({subreddit} - Score: {score})")
                if selftext:
                    md_lines.append(f"{selftext}...")
                md_lines.append("")
                
        return "\n".join(md_lines)
    except Exception as e:
        print(f"[SCRAPER] Reddit fetch failed: {e}")
        return ""


async def fetch_news_data(competitor_name: str) -> str:
    """Fetch recent news articles from Google News RSS."""
    if not competitor_name:
        return ""
        
    query = urllib.parse.quote(competitor_name)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        # feedparser uses sync urllib, but it's fast enough for RSS
        d = feedparser.parse(url)
        
        md_lines = [f"# Recent News for {competitor_name}"]
        # Take top 8 recent articles
        for entry in d.entries[:8]:
            title = entry.get("title", "")
            pub_date = entry.get("published", "")
            if title:
                # Basic cleaning of the source name often appended at the end e.g. " - TechCrunch"
                clean_title = title.split(" - ")[0] 
                md_lines.append(f"- **{clean_title}** ({pub_date})")
                
        return "\n".join(md_lines)
    except Exception as e:
        print(f"[SCRAPER] News fetch failed: {e}")
        return ""


async def fetch_jobs_data(competitor_name: str) -> str:
    """Fetch job postings to infer roadmap via Google RSS search on ATS platforms."""
    if not competitor_name:
        return ""
        
    # Search common ATS endpoints like lever/greenhouse/ashby
    q = f'(site:lever.co OR site:greenhouse.io OR site:boards.greenhouse.io OR site:jobs.ashbyhq.com) "{competitor_name}"'
    query = urllib.parse.quote(q)
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        d = feedparser.parse(url)
        
        md_lines = [f"# Open Job Roles for {competitor_name}"]
        roles_found = 0
        
        for entry in d.entries[:10]:
            title = entry.get("title", "")
            # Clean up the ATS title e.g. "Senior Software Engineer - Stripe - Lever" -> "Senior Software Engineer"
            clean_title = title.split(" - ")[0].strip()
            
            if clean_title and "lever" not in clean_title.lower() and "greenhouse" not in clean_title.lower():
                md_lines.append(f"- {clean_title}")
                roles_found += 1
                
        if roles_found == 0:
            md_lines.append("- No specific job listings found on common ATS platforms.")
            
        return "\n".join(md_lines)
    except Exception as e:
        print(f"[SCRAPER] Jobs fetch failed: {e}")
        return ""


# ==========================================
# REVIEW PLATFORM & AD LIBRARY SCRAPERS
# ==========================================

import time
import requests as sync_requests


def scrape_trustpilot(competitor_url: str) -> dict | None:
    """Scrape Trustpilot reviews. Returns structured dict or None on failure."""
    if not competitor_url:
        return None
    try:
        domain = urlparse(competitor_url).netloc.replace("www.", "")
        if not domain:
            return None
        url = f"https://www.trustpilot.com/review/{domain}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        time.sleep(2)
        resp = sync_requests.get(url, headers=headers, timeout=15)
        if resp.status_code in (403, 429, 404):
            print(f"[SCRAPER] Trustpilot returned {resp.status_code} for {domain}")
            return None
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # TrustScore
        trust_score = 0.0
        score_el = soup.select_one('[data-rating-typography]') or soup.select_one('[class*="trustScore"]')
        if score_el:
            try:
                trust_score = float(score_el.get_text(strip=True).split()[0])
            except (ValueError, IndexError):
                pass

        # Review count
        review_count = 0
        count_el = soup.select_one('[data-reviews-count-typography]') or soup.select_one('[class*="reviewCount"]')
        if count_el:
            try:
                review_count = int(re.sub(r"[^\d]", "", count_el.get_text(strip=True)))
            except (ValueError, TypeError):
                pass

        # Rating distribution
        rating_distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        dist_labels = soup.select('[class*="distribution"] label, [class*="rating-bar"]')
        for label in dist_labels:
            text = label.get_text(strip=True)
            for star in ["5", "4", "3", "2", "1"]:
                if f"{star} star" in text.lower() or f"{star}-star" in text.lower():
                    pct_match = re.search(r"(\d+)%", text)
                    if pct_match:
                        rating_distribution[star] = int(pct_match.group(1))

        # Recent reviews
        recent_reviews = []
        review_cards = soup.select('[class*="review-card"], article[class*="review"]')[:5]
        for card in review_cards:
            title_el = card.select_one('[data-service-review-title-typography], h2')
            body_el = card.select_one('[data-service-review-text-typography], p[class*="text"]')
            rating_el = card.select_one('[data-service-review-rating], img[alt*="Rated"]')
            date_el = card.select_one('time, [datetime]')

            rating = 0
            if rating_el:
                alt = rating_el.get("alt", "")
                r_match = re.search(r"(\d)", alt)
                if r_match:
                    rating = int(r_match.group(1))

            review_obj = {
                "title": title_el.get_text(strip=True) if title_el else "",
                "body": body_el.get_text(strip=True)[:300] if body_el else "",
                "rating": rating,
                "date": date_el.get("datetime", date_el.get_text(strip=True) if date_el else ""),
            }
            if review_obj["title"] or review_obj["body"]:
                recent_reviews.append(review_obj)

        # Extract negative themes from low-rated reviews
        negative_themes = []
        negative_words = {}
        for card in soup.select('[class*="review-card"], article[class*="review"]')[:20]:
            rating_el = card.select_one('[data-service-review-rating], img[alt*="Rated"]')
            if rating_el:
                alt = rating_el.get("alt", "")
                r_match = re.search(r"(\d)", alt)
                if r_match and int(r_match.group(1)) <= 2:
                    body_el = card.select_one('[data-service-review-text-typography], p[class*="text"]')
                    if body_el:
                        text = body_el.get_text(strip=True).lower()
                        phrases = ["slow support", "billing issues", "poor onboarding", "buggy",
                                   "expensive", "no response", "terrible", "worst", "refund",
                                   "misleading", "hidden fees", "downtime", "unreliable"]
                        for phrase in phrases:
                            if phrase in text:
                                negative_words[phrase] = negative_words.get(phrase, 0) + 1
        negative_themes = sorted(negative_words.keys(), key=lambda k: -negative_words[k])[:5]

        return {
            "source": "trustpilot",
            "url": url,
            "trust_score": trust_score,
            "review_count": review_count,
            "rating_distribution": rating_distribution,
            "recent_reviews": recent_reviews,
            "negative_themes": negative_themes,
        }
    except Exception as e:
        print(f"[SCRAPER] Trustpilot scrape failed for '{competitor_url}': {e}")
        return None


def scrape_meta_ads(competitor_name: str, competitor_url: str) -> dict | None:
    """Scrape Meta Ad Library for a competitor. Returns structured dict or None on failure."""
    if not competitor_name:
        return None
    try:
        encoded_name = urllib.parse.quote(competitor_name)
        search_url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=US&q={encoded_name}&search_type=keyword_unordered"
        api_url = f"https://www.facebook.com/ads/library/async/search_ads/?q={encoded_name}&count=20&active_status=active&ad_type=all&countries[0]=US"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        ads = []
        cta_counts = {}
        themes = {}

        # Try the API endpoint first
        time.sleep(2)
        resp = sync_requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code == 200 and resp.text:
            # Try to parse JSON from response (may be wrapped in HTML)
            import json as _json
            text = resp.text
            # Look for JSON blobs in the response
            json_start = text.find("{")
            if json_start >= 0:
                try:
                    data = _json.loads(text[json_start:])
                    results = data.get("results", data.get("ads", []))
                    if isinstance(results, list):
                        for ad_item in results[:20]:
                            ad_obj = {
                                "headline": ad_item.get("title", ad_item.get("headline", "")),
                                "body": ad_item.get("body", ad_item.get("description", ""))[:200],
                                "cta": ad_item.get("cta_text", ad_item.get("call_to_action", "")),
                                "format": ad_item.get("format", ad_item.get("ad_format", "unknown")),
                                "start_date": ad_item.get("start_date", ad_item.get("creation_time", "")),
                                "landing_url": ad_item.get("landing_url", ad_item.get("link_url", "")),
                            }
                            ads.append(ad_obj)
                            if ad_obj["cta"]:
                                cta_counts[ad_obj["cta"]] = cta_counts.get(ad_obj["cta"], 0) + 1
                except _json.JSONDecodeError:
                    pass

        # Fallback: Scrape the HTML page
        if not ads:
            resp2 = sync_requests.get(search_url, headers=headers, timeout=15)
            if resp2.status_code == 200:
                soup = BeautifulSoup(resp2.text, "lxml")
                ad_cards = soup.select('[class*="ad-card"], [class*="_7jvw"], [class*="xrvj5dj"]')[:20]
                for card in ad_cards:
                    headline_el = card.select_one('[class*="headline"], h3, h4')
                    body_el = card.select_one('[class*="body"], [class*="description"], p')
                    cta_el = card.select_one('[class*="cta"], button, [class*="call-to-action"]')
                    ad_obj = {
                        "headline": headline_el.get_text(strip=True) if headline_el else "",
                        "body": body_el.get_text(strip=True)[:200] if body_el else "",
                        "cta": cta_el.get_text(strip=True) if cta_el else "",
                        "format": "unknown",
                        "start_date": "",
                        "landing_url": "",
                    }
                    if ad_obj["headline"] or ad_obj["body"]:
                        ads.append(ad_obj)
                        if ad_obj["cta"]:
                            cta_counts[ad_obj["cta"]] = cta_counts.get(ad_obj["cta"], 0) + 1

        # Extract messaging themes from ad text
        all_text = " ".join([f"{a['headline']} {a['body']}" for a in ads]).lower()
        theme_keywords = {
            "ease of use": ["easy", "simple", "effortless", "intuitive"],
            "social proof": ["trusted by", "join", "companies use", "customers"],
            "free trial": ["free trial", "try free", "no credit card"],
            "team management": ["team", "collaborate", "workspace"],
            "cost savings": ["save", "affordable", "cheaper", "cost"],
            "enterprise": ["enterprise", "scale", "security", "compliance"],
            "speed": ["fast", "quick", "instant", "minutes"],
            "integration": ["integrate", "connect", "sync", "api"],
        }
        for theme, kws in theme_keywords.items():
            count = sum(1 for kw in kws if kw in all_text)
            if count > 0:
                themes[theme] = count

        top_themes = sorted(themes.keys(), key=lambda k: -themes[k])[:5]

        return {
            "source": "meta_ads",
            "url": search_url,
            "total_ads_found": len(ads),
            "ads": ads[:20],
            "cta_distribution": cta_counts,
            "top_messaging_themes": top_themes,
            "top_keywords": [],
            "headline_patterns": [],
        }
    except Exception as e:
        print(f"[SCRAPER] Meta Ads scrape failed for '{competitor_name}': {e}")
        return None


def scrape_google_ads_transparency(competitor_url: str) -> dict | None:
    """Scrape Google Ads Transparency Center for a competitor. Returns structured dict or None."""
    if not competitor_url:
        return None
    try:
        domain = urlparse(competitor_url).netloc.replace("www.", "")
        if not domain:
            return None

        page_url = f"https://adstransparency.google.com/?region=anywhere&domain={domain}"
        api_url = f"https://adstransparency.google.com/anji/_/rpc/SearchService/SearchCreatives"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": page_url,
        }

        ads = []
        top_keywords = {}
        headline_patterns = {"action-oriented": 0, "question-based": 0, "social proof": 0, "feature-led": 0}

        time.sleep(2)
        resp = sync_requests.get(f"https://adstransparency.google.com/?region=anywhere&domain={domain}", headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            ad_cards = soup.select('[class*="creative-card"], [class*="ad-card"]')[:20]
            for card in ad_cards:
                headline_el = card.select_one('[class*="headline"], h3, [class*="title"]')
                desc_el = card.select_one('[class*="description"], [class*="body-text"], p')
                date_el = card.select_one('[class*="date"], time')

                headline = headline_el.get_text(strip=True) if headline_el else ""
                ad_obj = {
                    "headline": headline,
                    "description": desc_el.get_text(strip=True)[:200] if desc_el else "",
                    "format": "text",
                    "last_seen": date_el.get_text(strip=True) if date_el else "",
                }
                if ad_obj["headline"] or ad_obj["description"]:
                    ads.append(ad_obj)

                    # Classify headline pattern
                    h_lower = headline.lower()
                    if "?" in headline:
                        headline_patterns["question-based"] += 1
                    elif any(w in h_lower for w in ["join", "trusted", "million", "companies"]):
                        headline_patterns["social proof"] += 1
                    elif any(w in h_lower for w in ["get", "start", "try", "discover", "unlock"]):
                        headline_patterns["action-oriented"] += 1
                    else:
                        headline_patterns["feature-led"] += 1

                    # Extract keywords
                    for word in h_lower.split():
                        if len(word) > 4 and word.isalpha():
                            top_keywords[word] = top_keywords.get(word, 0) + 1

        sorted_keywords = sorted(top_keywords.keys(), key=lambda k: -top_keywords[k])[:10]
        sorted_patterns = [p for p, c in sorted(headline_patterns.items(), key=lambda x: -x[1]) if c > 0]

        return {
            "source": "google_ads",
            "url": page_url,
            "total_ads_found": len(ads),
            "ads": ads[:20],
            "top_keywords": sorted_keywords,
            "headline_patterns": sorted_patterns,
        }
    except Exception as e:
        print(f"[SCRAPER] Google Ads Transparency scrape failed for '{competitor_url}': {e}")
        return None


# ==========================================
# COMMUNITY INTELLIGENCE SCRAPERS
# ==========================================

_POSITIVE_KEYWORDS = {
    "love", "great", "amazing", "awesome", "excellent", "best", "fantastic",
    "solid", "recommend", "impressed", "fast", "reliable", "intuitive",
    "smooth", "powerful", "happy", "wonderful", "perfect", "superior",
}
_NEGATIVE_KEYWORDS = {
    "hate", "terrible", "awful", "worst", "slow", "buggy", "expensive",
    "frustrating", "broken", "horrible", "poor", "disappointed", "sucks",
    "nightmare", "overpriced", "unreliable", "clunky", "bloated", "downgrade",
}
_SWITCHING_PATTERNS = [
    "switched from", "moved from", "migrated from", "moved away from",
    "left .* for", "replaced .* with", "ditched", "dropped .* for",
    "switching from", "migrating from", "moving away from", "leaving .* for",
]


def _classify_sentiment(text: str) -> str:
    """Classify text as positive/negative/neutral via keyword matching."""
    text_lower = text.lower()
    pos = sum(1 for w in _POSITIVE_KEYWORDS if w in text_lower)
    neg = sum(1 for w in _NEGATIVE_KEYWORDS if w in text_lower)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


def _detect_switching_signals(text: str, competitor_name: str) -> list[str]:
    """Detect switching-intent phrases in text."""
    signals = []
    text_lower = text.lower()
    name_lower = competitor_name.lower()
    for pattern in _SWITCHING_PATTERNS:
        if name_lower in text_lower and re.search(pattern, text_lower):
            # Extract surrounding context (up to 200 chars around match)
            match = re.search(pattern, text_lower)
            if match:
                start = max(0, match.start() - 60)
                end = min(len(text_lower), match.end() + 140)
                signals.append(text[start:end].strip())
    return signals


def scrape_hackernews(competitor_name: str) -> dict | None:
    """
    Scrape Hacker News via the Algolia API.
    Runs 3 queries, classifies sentiment, detects switching signals.
    Returns structured dict or None on failure.
    """
    if not competitor_name:
        return None
    try:
        base_url = "https://hn.algolia.com/api/v1/search"
        
        # Enclose multi-word names in quotes for exact matching
        query_name = f'"{competitor_name}"' if ' ' in competitor_name.strip() else competitor_name
        
        queries = [
            query_name,
            f"{query_name} review",
            f"{query_name} alternative",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CompyBot/1.0)",
        }

        all_hits = []
        seen_ids = set()

        for query in queries:
            time.sleep(1)  # polite delay
            params = {
                "query": query,
                "tags": "(story,comment)",
                "hitsPerPage": 50,
            }
            resp = sync_requests.get(base_url, params=params, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"[SCRAPER] HN Algolia returned {resp.status_code} for query: {query}")
                continue
            data = resp.json()
            for hit in data.get("hits", []):
                obj_id = hit.get("objectID")
                if obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)
                all_hits.append(hit)

        if not all_hits:
            print(f"[SCRAPER] Hacker News: no results for '{competitor_name}'")
            return None

        positive_comments = []
        negative_comments = []
        neutral_count = 0
        switching_signals = []

        for hit in all_hits:
            title = hit.get("title") or ""
            comment_text = hit.get("comment_text") or ""
            story_text = hit.get("story_text") or ""
            
            # Clean HTML tags and entities
            title = html.unescape(re.sub(r'<[^>]+>', '', title))
            comment_text = html.unescape(re.sub(r'<[^>]+>', '', comment_text))
            story_text = html.unescape(re.sub(r'<[^>]+>', '', story_text))
            
            text = f"{title} {comment_text} {story_text}".strip()
            if not text:
                continue

            # Relevance Filter: Competitor must be in title, or mentioned > 1 time in the text
            if len(competitor_name) > 2:
                c_lower = competitor_name.lower()
                if c_lower not in title.lower() and text.lower().count(c_lower) < 2:
                    continue

            # Build source URL
            story_id = hit.get("story_id") or hit.get("objectID")
            source_url = f"https://news.ycombinator.com/item?id={story_id}"

            sentiment = _classify_sentiment(text)
            entry = {
                "text": text[:300],
                "url": source_url,
                "points": hit.get("points") or 0,
                "created_at": hit.get("created_at", ""),
                "author": hit.get("author", ""),
            }

            if sentiment == "positive":
                positive_comments.append(entry)
            elif sentiment == "negative":
                negative_comments.append(entry)
            else:
                neutral_count += 1

            # Detect switching signals
            for sig in _detect_switching_signals(text, competitor_name):
                switching_signals.append({
                    "signal": sig,
                    "url": source_url,
                    "author": hit.get("author", ""),
                })

        total = len(positive_comments) + len(negative_comments) + neutral_count
        sentiment_score = 0
        if total > 0:
            sentiment_score = int(((len(positive_comments) - len(negative_comments)) / total) * 50 + 50)
            sentiment_score = max(0, min(100, sentiment_score))

        return {
            "source": "hackernews",
            "total_mentions": len(all_hits),
            "sentiment_score": sentiment_score,
            "positive_comments": sorted(positive_comments, key=lambda x: -(x.get("points") or 0))[:10],
            "negative_comments": sorted(negative_comments, key=lambda x: -(x.get("points") or 0))[:10],
            "neutral_count": neutral_count,
            "switching_signals": switching_signals[:10],
        }
    except Exception as e:
        print(f"[SCRAPER] Hacker News scrape failed for '{competitor_name}': {e}")
        return None


def scrape_reddit_deep(competitor_name: str) -> dict | None:
    """
    Deep Reddit scrape via the JSON search API.
    Runs 5 intent queries, classifies posts, extracts top subreddits.
    Returns structured dict or None on failure.
    """
    if not competitor_name:
        return None
    try:
        # Enclose multi-word names in quotes for exact matching
        query_name = f'"{competitor_name}"' if ' ' in competitor_name.strip() else competitor_name
        
        intent_queries = {
            "review": f"{query_name} review",
            "alternative": f"{query_name} alternative",
            "problems": f"{query_name} problems OR issues",
            "pricing": f"{query_name} pricing OR cost OR expensive",
            "switching": f'"switched from {competitor_name}"',
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CompyBot/1.0)",
        }

        reviews = []
        complaints = []
        comparisons = []
        switching_signals = []
        subreddit_counts: dict[str, int] = {}
        seen_ids = set()
        all_posts = []

        for intent, query in intent_queries.items():
            time.sleep(2)  # Reddit rate limits aggressively
            url = "https://www.reddit.com/search.json"
            params = {
                "q": query,
                "sort": "relevance",
                "t": "year",
                "limit": 25,
                "type": "link",
            }
            try:
                resp = sync_requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code in (403, 429):
                    print(f"[SCRAPER] Reddit blocked ({resp.status_code}) for intent: {intent}")
                    continue
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception:
                continue

            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                post_id = post.get("id", "")
                if not post_id or post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                title = post.get("title", "")
                body = post.get("selftext", "")[:500]
                
                # Clean HTML tags and entities
                title = html.unescape(re.sub(r'<[^>]+>', '', title))
                body = html.unescape(re.sub(r'<[^>]+>', '', body))
                
                # Relevance Filter: Competitor must be in title, or mentioned > 1 time in the body
                if len(competitor_name) > 2:
                    c_lower = competitor_name.lower()
                    combined_text = f"{title} {body}".lower()
                    if c_lower not in title.lower() and combined_text.count(c_lower) < 2:
                        continue
                        
                score = post.get("score", 0)
                subreddit = post.get("subreddit", "unknown")
                permalink = post.get("permalink", "")
                post_url = f"https://www.reddit.com{permalink}" if permalink else ""

                entry = {
                    "title": title,
                    "body": body[:300],
                    "score": score,
                    "subreddit": subreddit,
                    "url": post_url,
                    "intent": intent,
                }
                all_posts.append(entry)

                # Track subreddits
                subreddit_counts[subreddit] = subreddit_counts.get(subreddit, 0) + 1

                # Classify by intent + content
                combined = f"{title} {body}".lower()
                sentiment = _classify_sentiment(combined)

                if intent == "switching" or any(re.search(p, combined) for p in _SWITCHING_PATTERNS):
                    switching_signals.append(entry)
                elif intent == "problems" or sentiment == "negative":
                    complaints.append(entry)
                elif intent == "alternative":
                    comparisons.append(entry)
                else:
                    reviews.append(entry)

        if not all_posts:
            print(f"[SCRAPER] Reddit Deep: no results for '{competitor_name}'")
            return None

        # Sort each category by score (engagement)
        reviews.sort(key=lambda x: -(x.get("score") or 0))
        complaints.sort(key=lambda x: -(x.get("score") or 0))
        comparisons.sort(key=lambda x: -(x.get("score") or 0))
        switching_signals.sort(key=lambda x: -(x.get("score") or 0))

        # Top subreddits
        top_subreddits = sorted(subreddit_counts.items(), key=lambda x: -x[1])[:10]

        # Sentiment breakdown
        pos = sum(1 for p in all_posts if _classify_sentiment(f"{p['title']} {p['body']}") == "positive")
        neg = sum(1 for p in all_posts if _classify_sentiment(f"{p['title']} {p['body']}") == "negative")
        neu = len(all_posts) - pos - neg
        sentiment_score = 0
        if all_posts:
            sentiment_score = int(((pos - neg) / len(all_posts)) * 50 + 50)
            sentiment_score = max(0, min(100, sentiment_score))

        return {
            "source": "reddit_deep",
            "total_mentions": len(all_posts),
            "sentiment_score": sentiment_score,
            "sentiment_breakdown": {"positive": pos, "negative": neg, "neutral": neu},
            "reviews": reviews[:10],
            "complaints": complaints[:10],
            "comparisons": comparisons[:10],
            "switching_signals": switching_signals[:10],
            "top_subreddits": [{"name": s, "mentions": c} for s, c in top_subreddits],
        }
    except Exception as e:
        print(f"[SCRAPER] Reddit Deep scrape failed for '{competitor_name}': {e}")
        return None
