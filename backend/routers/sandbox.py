"""Sandbox router — Business Sandbox simulation endpoint."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from config import settings
from database import get_db
from models import Company, Competitor
from agents.sandbox import (
    run_sandbox_simulation,
    _format_company_context,
    _format_competitor_context,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class SandboxRequest(BaseModel):
    company_id: int
    competitor_ids: List[int] = []
    scenario: str
    prediction_question: str


class AgentResponse(BaseModel):
    name: str
    role: str
    platform: str
    comment: str
    sentiment: str


class MetricsResponse(BaseModel):
    sentiment_score: int = 50
    adoption_likelihood: int = 50
    churn_risk: int = 50
    competitor_threat: str = "Medium"


class SandboxResponse(BaseModel):
    summary: str
    agents: List[AgentResponse]
    market_score: int
    score_verdict: str
    score_explanation: str
    metrics: MetricsResponse
    recommendations: List[str]


# ---------------------------------------------------------------------------
# POST /api/sandbox/simulate
# ---------------------------------------------------------------------------
@router.post("/simulate", response_model=SandboxResponse)
async def simulate(req: SandboxRequest, db: AsyncSession = Depends(get_db)):
    """Run a Business Sandbox simulation.

    Phase 1: Uses LLM (Gemini) to generate the simulation.
    Phase 2: When USE_MIROFISH=true, calls MiroFish backend instead.
    """

    # Fetch company
    result = await db.execute(select(Company).where(Company.id == req.company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company_dict = {
        "name": company.name,
        "summary": company.summary,
        "features": company.features,
        "icp": company.icp,
        "positioning": company.positioning,
        "pricing": company.pricing,
    }

    # Fetch competitors (if any selected)
    competitor_dicts = []
    if req.competitor_ids:
        result = await db.execute(
            select(Competitor).where(Competitor.id.in_(req.competitor_ids))
        )
        competitors = result.scalars().all()
        for c in competitors:
            competitor_dicts.append({
                "name": c.name or c.url,
                "summary": "",
                "raw_profile": "",
            })

    # Build context strings
    company_context = _format_company_context(company_dict)
    competitor_context = _format_competitor_context(competitor_dicts)

    if not req.scenario.strip():
        raise HTTPException(status_code=400, detail="Scenario is required")

    # Run simulation — Phase 1 (LLM) or Phase 2 (MiroFish)
    try:
        if settings.USE_MIROFISH:
            # Phase 2: MiroFish swarm simulation
            from services.mirofish import generate_seed_document, run_mirofish_simulation

            seed_doc = generate_seed_document(
                company_context, competitor_context, req.scenario
            )
            simulation = await run_mirofish_simulation(
                seed_document=seed_doc,
                prediction_question=req.prediction_question,
            )
        else:
            # Phase 1: LLM-powered simulation
            simulation = await run_sandbox_simulation(
                company_context=company_context,
                competitor_context=competitor_context,
                scenario=req.scenario,
                prediction_question=req.prediction_question,
            )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.error(f"Sandbox simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    return simulation

