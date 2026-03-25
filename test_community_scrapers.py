import sys
import json
import os

# Add backend directory to path so we can import modules
sys.path.append(os.path.abspath("backend"))

from services.scraper import scrape_hackernews, scrape_reddit_deep

def test_scrapers(competitor_name):
    print(f"\n==========================================")
    print(f"Testing Scrapers for: '{competitor_name}'")
    print(f"==========================================\n")
    
    print("1. Scraping Hacker News...")
    hn_data = scrape_hackernews(competitor_name)
    if hn_data:
        print(f"   Success! Found {hn_data.get('total_mentions', 0)} mentions.")
        print(f"   Sentiment Score: {hn_data.get('sentiment_score', 'N/A')}/100")
        if hn_data.get('switching_signals'):
            print(f"   Found {len(hn_data['switching_signals'])} switching signals!")
    else:
        print("   Failed or no data found.")

    print("\n2. Scraping Reddit Deep...")
    reddit_data = scrape_reddit_deep(competitor_name)
    if reddit_data:
        print(f"   Success! Found {reddit_data.get('total_mentions', 0)} posts across {len(reddit_data.get('top_subreddits', []))} subreddits.")
        print(f"   Sentiment Breakdown: {reddit_data.get('sentiment_breakdown', {})}")
        if reddit_data.get('complaints'):
            print(f"   Found {len(reddit_data['complaints'])} complaint posts!")
    else:
        print("   Failed or no data found.")
        
    print("\nTest completed.")

if __name__ == "__main__":
    # Test with a well-known B2B SaaS company that will have community discussion
    test_scrapers("Apple Pay")
