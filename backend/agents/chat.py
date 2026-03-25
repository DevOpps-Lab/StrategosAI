"""StrategosAI Chat Agent — Gemini-powered competitive intelligence analyst."""

import json
import logging
import google.generativeai as genai
from config import settings

log = logging.getLogger(__name__)
genai.configure(api_key=settings.GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# System Prompt — Sharp, opinionated strategic analyst
# ---------------------------------------------------------------------------
CHAT_SYSTEM_PROMPT = """\
You are **StrategosAI**, an elite Competitive Intelligence Analyst.
You have a full intelligence dossier on a competitor. The user is a founder or sales leader. Be direct. Be sharp. No fluff. No disclaimers.

## YOUR RULES
1. **Lead with the most critical insight** — start every answer with the single most important takeaway before expanding.
2. **Use structure** — use markdown headers (###), bold, and bullet points. Never write a wall of text.
3. **Reference SPECIFIC data** — cite actual numbers, scores, and quotes from the dossier below. Say "Their sentiment score is 42/100" not "they have low sentiment".
4. **Proactively suggest actions** — after answering, recommend 1-2 concrete next steps the user should take.
5. **Stay within the dossier** — if you lack data, say "I don't have intel on that yet" and suggest what data the user should gather.
6. **Keep responses 80-200 words** unless the user asks for something longer (e.g. an email, a full report).
7. If asked to write an email or sales script, do it — make it short and punchy.

## FOLLOW-UP QUESTIONS (CRITICAL)
At the VERY END of every response, you MUST append a valid JSON block on its own line, wrapped in triple backticks with the json label. This block contains exactly 3 smart follow-up questions the user might want to ask next, based on the conversation so far. Format:
```json
{{"follow_ups": ["Question 1?", "Question 2?", "Question 3?"]}}
```
These must be specific, strategic questions — never generic. Always include this block.

## COMPETITOR INTELLIGENCE DOSSIER
**Competitor:** {competitor_name}
**URL:** {competitor_url}

### Pricing Intelligence
- Model: {pricing_model}
- Community Pricing Complaints: {pricing_complaints}
- Price Perception: {community_price_perception}

### Feature Gap Analysis
**Where WE Win (their weaknesses):**
{we_win}

**Where THEY Win (their strengths):**
{they_win}

### Community Sentiment
- Overall Score: {sentiment_score}/100
- Trend: {sentiment_trend}
- Top Praise: {top_praise}
- Top Complaints: {top_complaints}

### Strategic Positioning
{positioning}

### Review Platform Intelligence
{review_summary}

### Ad Library Intelligence
{ad_summary}
"""


# ---------------------------------------------------------------------------
# Tool definitions for Gemini function-calling
# ---------------------------------------------------------------------------
SEND_EMAIL_TOOL = {
    "name": "send_email",
    "description": "Send a sales or intelligence email to a specific recipient.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "recipient_email": {
                "type": "STRING",
                "description": "The exact email address to send to."
            },
            "subject": {
                "type": "STRING",
                "description": "A catchy, relevant subject line."
            },
            "body": {
                "type": "STRING",
                "description": "The body of the email. MUST be formatted in crisp, professional HTML. Use <p>, <b>, <i>, <ul>, <li>, and <br> tags. Do NOT wrap the output in markdown blockquotes or ```html tags."
            }
        },
        "required": ["recipient_email", "subject", "body"]
    }
}

SEND_VOICE_TOOL = {
    "name": "send_voice_briefing",
    "description": "Trigger an executive briefing phone call to the provided phone number.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "phone_number": {
                "type": "STRING",
                "description": "The phone number to call in E.164 format. If a 10-digit Indian number, prepend '+91'."
            }
        },
        "required": ["phone_number"]
    }
}


def _build_system_prompt(context: dict) -> str:
    """Format the system prompt with dossier context."""
    return CHAT_SYSTEM_PROMPT.format(
        competitor_name=context.get("competitor_name", "Unknown"),
        competitor_url=context.get("competitor_url", "Unknown"),
        pricing_model=context.get("pricing_model", "Unknown"),
        pricing_complaints=", ".join(context.get("pricing_complaints", [])) or "None reported",
        community_price_perception=context.get("community_price_perception", "Unknown"),
        we_win="\n".join([f"- {f}" for f in context.get("we_win", [])]) or "None identified",
        they_win="\n".join([f"- {f}" for f in context.get("they_win", [])]) or "None identified",
        sentiment_score=context.get("sentiment_score", "N/A"),
        sentiment_trend=context.get("sentiment_trend", "N/A"),
        top_praise=", ".join(context.get("top_praise", [])) or "None found",
        top_complaints=", ".join(context.get("top_complaints", [])) or "None found",
        positioning=context.get("positioning", "Unknown"),
        review_summary=context.get("review_summary", "No review data available"),
        ad_summary=context.get("ad_summary", "No ad data available"),
    )


def _build_model(system_prompt: str):
    """Create a Gemini model instance with tools."""
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
        tools=[SEND_EMAIL_TOOL, SEND_VOICE_TOOL],
    )


def _convert_history(history: list) -> list:
    """Convert chat history dicts to Gemini format."""
    gemini_history = []
    for msg in history:
        gemini_history.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [msg["content"]]
        })
    return gemini_history


async def _handle_tool_call(fc, competitor_id: int) -> str:
    """Execute a function call (email or voice) and return a status string."""
    if fc.name == "send_email":
        args = fc.args
        recipient = args.get("recipient_email")
        subject = args.get("subject")
        body = args.get("body")

        from routers.sales import SalesSendRequest, send_sales_email
        req = SalesSendRequest(recipient_email=recipient, subject=subject, body=body)
        try:
            log.info("\033[1;33m[AGENT] Chatbot executing send_email...\033[0m")
            send_result = await send_sales_email(req)
            status_msg = send_result.get("message", "Success")
            return (
                f"📧 **Email Sent!**\n\n"
                f"I've dispatched the email to **{recipient}** with subject *\"{subject}\"*.\n\n"
                f"*(Status: {status_msg})*\n\n"
                f'```json\n{{"follow_ups": ["What objections should I prepare for?", "Draft a follow-up email for next week?", "Who else should I target?"]}}\n```'
            )
        except Exception as e:
            return f"❌ **Email Delivery Failed:** {str(e)}"

    elif fc.name == "send_voice_briefing":
        args = fc.args
        phone_number = args.get("phone_number")

        try:
            log.info(f"\033[1;33m[AGENT] Chatbot executing send_voice_briefing to {phone_number}...\033[0m")

            from database import async_session
            from models import Competitor, Signal
            from sqlalchemy import select as sa_select
            from config import settings as cfg
            from twilio.rest import Client

            async with async_session() as db:
                result = await db.execute(sa_select(Competitor).where(Competitor.id == competitor_id))
                competitor = result.scalar_one_or_none()

                if not competitor:
                    return "❌ **Voice Call Failed:** Could not find the competitor in the database."

                signals_result = await db.execute(sa_select(Signal).where(Signal.competitor_id == competitor_id))
                signals = signals_result.scalars().all()

                if not signals:
                    return "❌ **Voice Call Failed:** No intelligence signals found to brief you on."

                intelligence_summary = "\n".join(
                    [f"- {s.signal_type.upper()}: {s.title} ({s.severity})" for s in signals]
                )

                prompt = (
                    f"You are the StrategosAI Analyst calling an executive on the phone to give a quick intel briefing.\n\n"
                    f"The competitor is: {competitor.name}.\n\n"
                    f"Here is the raw intelligence data:\n{intelligence_summary[:4000]}\n\n"
                    f"Write a spoken script for a phone call.\n"
                    f"Rules:\n"
                    f"- Start with 'Hello! This is StrategosAI with your executive briefing on {competitor.name}.'\n"
                    f"- Keep it under 60 seconds when spoken.\n"
                    f"- Highlight their biggest weakness and their biggest strength.\n"
                    f"- Be highly engaging and conversational. No bullet points or markdown.\n"
                    f"- End with 'Thank you, and happy selling.'"
                )

                script_model = genai.GenerativeModel("gemini-2.5-flash")
                script_resp = await script_model.generate_content_async(prompt)
                script = script_resp.text.replace("\n", " ").strip()

                client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
                safe_script = script.replace("<", "").replace(">", "").replace("&", "and")
                twiml = f'<Response><Say voice="alice">{safe_script}</Say></Response>'

                call = client.calls.create(
                    twiml=twiml,
                    to=phone_number,
                    from_=cfg.TWILIO_PHONE_NUMBER,
                )

            return (
                f"📞 **Outbound Call Initiated!**\n\n"
                f"Dialing **{phone_number}** now to deliver the executive briefing.\n\n"
                f"*(Call SID: {call.sid})*\n\n"
                f'```json\n{{"follow_ups": ["What should I brief them on next?", "Send a follow-up email?", "Schedule another call?"]}}\n```'
            )
        except Exception as e:
            import traceback
            log.error(f"VOICE CALL ERROR: {e}")
            traceback.print_exc()
            return f"❌ **Voice Call Failed:** {str(e)}"

    return "⚠️ Unknown tool call."


# ---------------------------------------------------------------------------
# Non-streaming chat (original endpoint — signature preserved)
# ---------------------------------------------------------------------------
async def chat_with_analyst(competitor_id: int, context: dict, history: list, user_message: str) -> str:
    """Non-streaming chat. Returns the full reply string."""
    system_prompt = _build_system_prompt(context)
    model = _build_model(system_prompt)
    gemini_history = _convert_history(history)

    chat = model.start_chat(history=gemini_history)
    response = await chat.send_message_async(user_message)

    # Handle tool calls
    if response.parts and hasattr(response.parts[0], 'function_call') and response.parts[0].function_call:
        return await _handle_tool_call(response.parts[0].function_call, competitor_id)

    return response.text


# ---------------------------------------------------------------------------
# Streaming chat (new — used by /api/chat/stream)
# ---------------------------------------------------------------------------
async def chat_with_analyst_stream(competitor_id: int, context: dict, history: list, user_message: str):
    """Async generator that yields string chunks for streaming."""
    system_prompt = _build_system_prompt(context)
    model = _build_model(system_prompt)
    gemini_history = _convert_history(history)

    chat = model.start_chat(history=gemini_history)
    response = await chat.send_message_async(user_message, stream=True)

    async for chunk in response:
        # If chunk is a tool call, handle it and yield the result
        if chunk.parts and hasattr(chunk.parts[0], 'function_call') and chunk.parts[0].function_call:
            result = await _handle_tool_call(chunk.parts[0].function_call, competitor_id)
            yield result
            return

        if chunk.text:
            yield chunk.text
