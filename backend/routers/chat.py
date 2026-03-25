"""Chat router — standard + streaming SSE endpoints."""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_db
from models import Competitor
from agents.chat import chat_with_analyst, chat_with_analyst_stream

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatContext(BaseModel):
    competitor_name: str = "Unknown"
    competitor_url: str = "Unknown"
    pricing_model: str = "Unknown"
    pricing_complaints: List[str] = []
    community_price_perception: str = "Unknown"
    we_win: List[str] = []
    they_win: List[str] = []
    sentiment_score: str = "N/A"
    sentiment_trend: str = "N/A"
    top_praise: List[str] = []
    top_complaints: List[str] = []
    positioning: str = "Unknown"
    review_summary: str = "No review data available"
    ad_summary: str = "No ad data available"

class ChatRequest(BaseModel):
    competitor_id: int
    context: ChatContext
    history: List[ChatMessage] = []
    message: str


# ---------------------------------------------------------------------------
# Original non-streaming endpoint (signature preserved)
# ---------------------------------------------------------------------------
@router.post("")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Chat with the AI analyst about a specific competitor."""
    result = await db.execute(select(Competitor).where(Competitor.id == req.competitor_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    try:
        reply = await chat_with_analyst(
            competitor_id=req.competitor_id,
            context=req.context.dict(),
            history=[{"role": m.role, "content": m.content} for m in req.history],
            user_message=req.message,
        )
        return {"reply": reply}
    except Exception as e:
        log.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Streaming SSE endpoint (NEW)
# ---------------------------------------------------------------------------
@router.post("/stream")
async def chat_stream(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Stream AI analyst response as Server-Sent Events."""
    result = await db.execute(select(Competitor).where(Competitor.id == req.competitor_id))
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    async def event_generator():
        try:
            async for token in chat_with_analyst_stream(
                competitor_id=req.competitor_id,
                context=req.context.dict(),
                history=[{"role": m.role, "content": m.content} for m in req.history],
                user_message=req.message,
            ):
                payload = json.dumps({"token": token})
                yield f"data: {payload}\n\n"

            # Signal completion
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            log.error(f"Stream error: {e}")
            error_payload = json.dumps({"error": str(e)})
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
