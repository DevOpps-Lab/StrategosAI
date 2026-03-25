"""Pydantic schemas for the StrategosAI data collection pipeline."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ScoutPayload(BaseModel):
    """Bundle of all scraped data produced by the Scout agent in a single run."""

    company_name: str = ""
    homepage_text: str = ""
    pricing_text: str = ""
    g2_reviews: list[str] = Field(default_factory=list)
    trustpilot_reviews: list[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class CompanyDNA(BaseModel):
    """Structured company profile returned by the Gemini DNA extraction prompt."""

    company_name: str = ""
    core_offering: str = ""
    target_audience: str = ""
    pricing_model: str = ""                       # e.g. "Freemium", "Subscription", "Usage-based"
    pricing_tiers: list[str] = Field(default_factory=list)  # e.g. ["Free - $0", "Pro - $49/mo"]
    key_features: list[str] = Field(default_factory=list)
    usp: str = ""                                 # Unique Selling Proposition
    sentiment_summary: str = ""                   # Derived from review text
    avg_review_score: Optional[float] = None      # Parsed from scraped reviews if available
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
