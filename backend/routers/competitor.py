"""Competitor router — Add competitors, trigger scout, stream progress."""

import asyncio
import json
import uuid
import traceback
from typing import Dict, Optional
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from database import get_db
from models import Competitor, CrawledPage, Company, ReviewData, AdData
from agents.scout import run_scout
from services.event_bus import event_bus
from config import settings

router = APIRouter(prefix="/api/competitor", tags=["competitor"])


class CompetitorRequest(BaseModel):
    url: str
    company_id: int


class CompetitorResponse(BaseModel):
    id: int
    name: str
    url: str
    status: str
    page_count: int
    company_id: int
    job_id: Optional[str] = None

    class Config:
        from_attributes = True


_running_jobs: Dict[int, str] = {}


@router.post("/add", response_model=CompetitorResponse)
async def add_competitor(req: CompetitorRequest, db: AsyncSession = Depends(get_db)):
    """Add a competitor and start crawling."""
    result = await db.execute(select(Company).where(Company.id == req.company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    url = req.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    competitor = Competitor(
        url=url,
        name="",
        status="crawling",
        company_id=req.company_id,
    )
    db.add(competitor)
    await db.commit()
    await db.refresh(competitor)

    job_id = str(uuid.uuid4())
    comp_id = competitor.id
    _running_jobs[comp_id] = job_id

    async def _background_crawl(comp_name_guess=""):
        print("[CRAWL] Starting background crawl for competitor %d, url=%s, job=%s" % (comp_id, url, job_id))
        from database import async_session
        from services.scraper import (
            fetch_reddit_data, fetch_news_data, fetch_jobs_data,
            scrape_trustpilot, scrape_meta_ads, scrape_google_ads_transparency,
            scrape_hackernews, scrape_reddit_deep,
        )
        from models import ReviewData, AdData, CommunityIntelData
        import asyncio
        
        async with async_session() as session:
            try:
                # To search Reddit/News/Jobs effectively we need a name, we'll try to guess it from the URL
                # e.g., https://www.stripe.com -> stripe
                name_query = urlparse(url).netloc.replace("www.", "").split(".")[0]
                
                await event_bus.publish(job_id, "log", {"message": f"Fetching multi-source intelligence for '{name_query}'..."})

                # Run web scout and external fetchers concurrently
                scout_task = asyncio.create_task(run_scout(job_id, url, max_pages=settings.MAX_CRAWL_PAGES))
                reddit_task = asyncio.create_task(fetch_reddit_data(name_query))
                news_task = asyncio.create_task(fetch_news_data(name_query))
                jobs_task = asyncio.create_task(fetch_jobs_data(name_query))

                pages, reddit_md, news_md, jobs_md = await asyncio.gather(
                    scout_task, reddit_task, news_task, jobs_task, return_exceptions=True
                )

                # Handle potential exceptions in gather
                if isinstance(pages, Exception):
                    raise pages
                
                print("[CRAWL] Scout returned %d pages for competitor %d" % (len(pages), comp_id))

                comp_name = ""
                # Save normal web pages
                for page_data in pages:
                    page = CrawledPage(
                        url=page_data["url"],
                        title=page_data["title"],
                        content_md=page_data["content_md"],
                        page_type=page_data["page_type"],
                        strategic_score=page_data["strategic_score"],
                        competitor_id=comp_id,
                    )
                    session.add(page)
                    if not comp_name and page_data["title"]:
                        # A better guess based on the actual homepage title
                        comp_name = page_data["title"].split("|")[0].split("-")[0].strip()

                # Save external data as high-priority pages so Analyst guarantees to see them
                if isinstance(reddit_md, str) and reddit_md:
                    session.add(CrawledPage(
                        url=f"reddit://search/{name_query}",
                        title=f"{name_query} Reddit Discussions",
                        content_md=reddit_md,
                        page_type="REDDIT_SOURCE",
                        strategic_score=95,
                        competitor_id=comp_id,
                    ))
                if isinstance(news_md, str) and news_md:
                    session.add(CrawledPage(
                        url=f"news://search/{name_query}",
                        title=f"{name_query} Recent News",
                        content_md=news_md,
                        page_type="NEWS_SOURCE",
                        strategic_score=95,
                        competitor_id=comp_id,
                    ))
                if isinstance(jobs_md, str) and jobs_md:
                    session.add(CrawledPage(
                        url=f"jobs://search/{name_query}",
                        title=f"{name_query} Open Jobs",
                        content_md=jobs_md,
                        page_type="JOB_SOURCE",
                        strategic_score=95,
                        competitor_id=comp_id,
                    ))

                # ===== REVIEW & AD LIBRARY SCRAPING =====
                scraper_name = comp_name or name_query

                await event_bus.publish(job_id, "log", {"message": "📝 Scraping Trustpilot reviews..."})
                await event_bus.publish(job_id, "log", {"message": "📢 Checking Meta Ads Library..."})
                await event_bus.publish(job_id, "log", {"message": "📢 Checking Google Ads Transparency..."})

                # Run 3 scrapers concurrently in threads (they use sync requests)
                tp_result, meta_result, google_result = await asyncio.gather(
                    asyncio.to_thread(scrape_trustpilot, url),
                    asyncio.to_thread(scrape_meta_ads, scraper_name, url),
                    asyncio.to_thread(scrape_google_ads_transparency, url),
                    return_exceptions=True,
                )

                # Handle exceptions from gather
                if isinstance(tp_result, Exception):
                    print(f"[CRAWL] Trustpilot scraper exception: {tp_result}")
                    tp_result = None
                if isinstance(meta_result, Exception):
                    print(f"[CRAWL] Meta Ads scraper exception: {meta_result}")
                    meta_result = None
                if isinstance(google_result, Exception):
                    print(f"[CRAWL] Google Ads scraper exception: {google_result}")
                    google_result = None

                # Save Trustpilot review data
                if tp_result:
                    session.add(ReviewData(
                        competitor_id=comp_id,
                        source="trustpilot",
                        url=tp_result["url"],
                        overall_rating=tp_result.get("trust_score", 0.0),
                        review_count=tp_result.get("review_count", 0),
                        rating_distribution=tp_result.get("rating_distribution", {}),
                        recent_reviews=tp_result.get("recent_reviews", []),
                        negative_themes=tp_result.get("negative_themes", []),
                        scraper_status="success",
                    ))
                    await event_bus.publish(job_id, "classified", {"message": f"✅ Trustpilot: score {tp_result.get('trust_score', 0)}/5", "page_type": "📝 Trustpilot", "strategic_score": "📊 Score: 90"})
                else:
                    session.add(ReviewData(competitor_id=comp_id, source="trustpilot", scraper_status="blocked"))
                    await event_bus.publish(job_id, "log", {"message": "⚠️ Trustpilot data unavailable"})

                # Save Meta Ads data
                if meta_result:
                    session.add(AdData(
                        competitor_id=comp_id,
                        source="meta_ads",
                        url=meta_result["url"],
                        total_ads_found=meta_result.get("total_ads_found", 0),
                        ads=meta_result.get("ads", []),
                        cta_distribution=meta_result.get("cta_distribution", {}),
                        top_messaging_themes=meta_result.get("top_messaging_themes", []),
                        scraper_status="success",
                    ))
                    await event_bus.publish(job_id, "classified", {"message": f"✅ Meta Ads: {meta_result.get('total_ads_found', 0)} active ads", "page_type": "📢 Meta Ads", "strategic_score": "📊 Score: 85"})
                else:
                    session.add(AdData(competitor_id=comp_id, source="meta_ads", scraper_status="blocked"))
                    await event_bus.publish(job_id, "log", {"message": "⚠️ Meta Ads data unavailable"})

                # Save Google Ads data
                if google_result:
                    session.add(AdData(
                        competitor_id=comp_id,
                        source="google_ads",
                        url=google_result["url"],
                        total_ads_found=google_result.get("total_ads_found", 0),
                        ads=google_result.get("ads", []),
                        top_keywords=google_result.get("top_keywords", []),
                        headline_patterns=google_result.get("headline_patterns", []),
                        scraper_status="success",
                    ))
                    await event_bus.publish(job_id, "classified", {"message": f"✅ Google Ads: {google_result.get('total_ads_found', 0)} creatives", "page_type": "📢 Google Ads", "strategic_score": "📊 Score: 85"})
                else:
                    session.add(AdData(competitor_id=comp_id, source="google_ads", scraper_status="blocked"))
                    await event_bus.publish(job_id, "log", {"message": "⚠️ Google Ads data unavailable"})

                # ===== COMMUNITY INTELLIGENCE SCRAPING =====
                await event_bus.publish(job_id, "log", {"message": "🔥 Scraping Hacker News discussions..."})
                await event_bus.publish(job_id, "log", {"message": "🔍 Deep-scanning Reddit threads..."})

                hn_result, reddit_deep_result = await asyncio.gather(
                    asyncio.to_thread(scrape_hackernews, scraper_name),
                    asyncio.to_thread(scrape_reddit_deep, scraper_name),
                    return_exceptions=True,
                )

                if isinstance(hn_result, Exception):
                    print(f"[CRAWL] HackerNews scraper exception: {hn_result}")
                    hn_result = None
                if isinstance(reddit_deep_result, Exception):
                    print(f"[CRAWL] Reddit Deep scraper exception: {reddit_deep_result}")
                    reddit_deep_result = None

                # Save HackerNews data
                if hn_result:
                    session.add(CommunityIntelData(
                        competitor_id=comp_id,
                        source="hackernews",
                        total_mentions=hn_result.get("total_mentions", 0),
                        sentiment_score=hn_result.get("sentiment_score", 50),
                        positive_comments=hn_result.get("positive_comments", []),
                        negative_comments=hn_result.get("negative_comments", []),
                        switching_signals=hn_result.get("switching_signals", []),
                        scraper_status="success",
                    ))
                    await event_bus.publish(job_id, "classified", {
                        "message": f"✅ HackerNews: {hn_result.get('total_mentions', 0)} mentions, sentiment {hn_result.get('sentiment_score', 50)}/100",
                        "page_type": "🔥 HackerNews", "strategic_score": "📊 Score: 88",
                    })
                else:
                    session.add(CommunityIntelData(competitor_id=comp_id, source="hackernews", scraper_status="blocked"))
                    await event_bus.publish(job_id, "log", {"message": "⚠️ HackerNews data unavailable"})

                # Save Reddit Deep data
                if reddit_deep_result:
                    session.add(CommunityIntelData(
                        competitor_id=comp_id,
                        source="reddit_deep",
                        total_mentions=reddit_deep_result.get("total_mentions", 0),
                        sentiment_score=reddit_deep_result.get("sentiment_score", 50),
                        sentiment_breakdown=reddit_deep_result.get("sentiment_breakdown", {}),
                        reviews=reddit_deep_result.get("reviews", []),
                        complaints=reddit_deep_result.get("complaints", []),
                        comparisons=reddit_deep_result.get("comparisons", []),
                        switching_signals=reddit_deep_result.get("switching_signals", []),
                        top_subreddits=reddit_deep_result.get("top_subreddits", []),
                        scraper_status="success",
                    ))
                    await event_bus.publish(job_id, "classified", {
                        "message": f"✅ Reddit Deep: {reddit_deep_result.get('total_mentions', 0)} posts across {len(reddit_deep_result.get('top_subreddits', []))} subreddits",
                        "page_type": "🔍 Reddit Deep", "strategic_score": "📊 Score: 85",
                    })
                else:
                    session.add(CommunityIntelData(competitor_id=comp_id, source="reddit_deep", scraper_status="blocked"))
                    await event_bus.publish(job_id, "log", {"message": "⚠️ Reddit Deep data unavailable"})

                result = await session.execute(
                    select(Competitor).where(Competitor.id == comp_id)
                )
                comp = result.scalar_one()
                comp.status = "crawled"
                comp.page_count = len(pages) + 3 # approx incl external
                if comp_name:
                    comp.name = comp_name

                await session.commit()
                print("[CRAWL] Crawl complete for competitor %d: %d pages, name=%s" % (comp_id, len(pages), comp_name))
                await event_bus.publish(job_id, "done", {
                    "message": "Crawl complete",
                    "total_pages": len(pages)
                })
            except Exception as e:
                print("[CRAWL] Crawl FAILED for competitor %d: %s" % (comp_id, str(e)))
                traceback.print_exc()
                await event_bus.publish(job_id, "error", {
                    "message": "Crawl failed: " + str(e)
                })
                await event_bus.publish(job_id, "done", {
                    "message": "Crawl failed",
                    "total_pages": 0
                })
                try:
                    result = await session.execute(
                        select(Competitor).where(Competitor.id == comp_id)
                    )
                    comp = result.scalar_one()
                    comp.status = "failed"
                    await session.commit()
                except Exception:
                    pass
            finally:
                _running_jobs.pop(comp_id, None)

    asyncio.create_task(_background_crawl())

    return CompetitorResponse(
        id=competitor.id,
        name=competitor.name or "",
        url=competitor.url,
        status=competitor.status,
        page_count=competitor.page_count or 0,
        company_id=competitor.company_id,
        job_id=job_id,
    )


@router.get("/{competitor_id}/stream")
async def stream_competitor(competitor_id: int):
    """SSE endpoint for live crawl progress."""
    job_id = _running_jobs.get(competitor_id)
    if not job_id:
        done_payload = json.dumps({"event": "done", "data": {"message": "Crawl already completed", "total_pages": 0}})
        async def _completed_stream():
            yield {"data": done_payload}
        return EventSourceResponse(_completed_stream())

    return EventSourceResponse(event_bus.subscribe(job_id))


@router.get("/job/{job_id}/stream")
async def stream_job(job_id: str):
    """SSE endpoint using job_id directly (more reliable)."""
    return EventSourceResponse(event_bus.subscribe(job_id))


@router.get("/job/{job_id}/events")
async def get_job_events(job_id: str):
    """Polling fallback — get all buffered events for a job."""
    return event_bus.get_buffer(job_id)


@router.get("/{competitor_id}/reviews")
async def get_competitor_reviews(competitor_id: int, db: AsyncSession = Depends(get_db)):
    """Get all review data for a competitor."""
    result = await db.execute(
        select(ReviewData)
        .where(ReviewData.competitor_id == competitor_id)
        .order_by(ReviewData.scraped_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id, "source": r.source, "url": r.url,
            "overall_rating": r.overall_rating, "review_count": r.review_count,
            "rating_distribution": r.rating_distribution, "likes": r.likes,
            "dislikes": r.dislikes, "use_cases": r.use_cases,
            "negative_themes": r.negative_themes, "reviewer_segments": r.reviewer_segments,
            "recent_reviews": r.recent_reviews, "scraper_status": r.scraper_status,
        }
        for r in records
    ]


@router.get("/{competitor_id}/community-intel")
async def get_competitor_community_intel(competitor_id: int, db: AsyncSession = Depends(get_db)):
    """Get all community intelligence data for a competitor."""
    from models import CommunityIntelData
    result = await db.execute(
        select(CommunityIntelData)
        .where(CommunityIntelData.competitor_id == competitor_id)
        .order_by(CommunityIntelData.scraped_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id, "source": r.source, "total_mentions": r.total_mentions,
            "sentiment_score": r.sentiment_score, "sentiment_breakdown": r.sentiment_breakdown,
            "positive_comments": r.positive_comments, "negative_comments": r.negative_comments,
            "reviews": r.reviews, "complaints": r.complaints, "comparisons": r.comparisons,
            "switching_signals": r.switching_signals, "top_subreddits": r.top_subreddits,
            "scraper_status": r.scraper_status,
        }
        for r in records
    ]


@router.get("/{competitor_id}/ads")
async def get_competitor_ads(competitor_id: int, db: AsyncSession = Depends(get_db)):
    """Get all ad data for a competitor."""
    result = await db.execute(
        select(AdData)
        .where(AdData.competitor_id == competitor_id)
        .order_by(AdData.scraped_at.desc())
    )
    records = result.scalars().all()
    return [
        {
            "id": r.id, "source": r.source, "url": r.url,
            "total_ads_found": r.total_ads_found, "ads": r.ads,
            "cta_distribution": r.cta_distribution,
            "top_messaging_themes": r.top_messaging_themes,
            "top_keywords": r.top_keywords, "headline_patterns": r.headline_patterns,
            "scraper_status": r.scraper_status,
        }
        for r in records
    ]


@router.get("/{competitor_id}", response_model=CompetitorResponse)
async def get_competitor(competitor_id: int, db: AsyncSession = Depends(get_db)):
    """Get competitor details."""
    result = await db.execute(select(Competitor).where(Competitor.id == competitor_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    job_id = _running_jobs.get(competitor_id)
    return CompetitorResponse(
        id=competitor.id,
        name=competitor.name or "",
        url=competitor.url,
        status=competitor.status,
        page_count=competitor.page_count or 0,
        company_id=competitor.company_id,
        job_id=job_id,
    )


@router.get("/company/{company_id}")
async def list_competitors(company_id: int, db: AsyncSession = Depends(get_db)):
    """List all competitors for a company."""
    result = await db.execute(
        select(Competitor)
        .where(Competitor.company_id == company_id)
        .order_by(Competitor.created_at.desc())
    )
    competitors = result.scalars().all()
    return [
        CompetitorResponse(
            id=c.id,
            name=c.name or "",
            url=c.url,
            status=c.status,
            page_count=c.page_count or 0,
            company_id=c.company_id,
            job_id=_running_jobs.get(c.id),
        )
        for c in competitors
    ]
