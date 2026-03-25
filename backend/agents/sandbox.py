"""StrategosAI Sandbox Agent — Swarm-intelligence simulation via Gemini."""

import json
import logging
import re
import google.generativeai as genai
from config import settings

log = logging.getLogger(__name__)
genai.configure(api_key=settings.GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# System prompt — swarm intelligence simulation engine
# ---------------------------------------------------------------------------
SANDBOX_SYSTEM_PROMPT = """\
You are a swarm intelligence simulation engine. You simulate how a realistic \
and diverse market crowd of autonomous agents reacts to a business scenario. \
Your agents must have distinct voices, realistic skepticism, and varied motivations. \
Do not produce generic marketing analysis. Produce a grounded, honest simulation \
where some agents will resist, some will champion, and some will be indifferent. \
Base everything strictly on the company and competitor context provided. \
Respond only in valid JSON with no preamble, no markdown, no code fences.\
"""

# ---------------------------------------------------------------------------
# User prompt template
# ---------------------------------------------------------------------------
USER_PROMPT_TEMPLATE = """\
Company Context:
{company_context}

Competitor Context:
{competitor_context}

Scenario:
{scenario}

Prediction Question:
{prediction_question}

Simulate this scenario and return a JSON object with this exact structure:

{{
  "summary": "3 to 5 sentence paragraph of what happened in the simulated market",
  "agents": [
    {{
      "name": "string",
      "role": "string",
      "platform": "Reddit | Twitter | HackerNews",
      "comment": "string",
      "sentiment": "positive | neutral | negative"
    }}
  ],
  "market_score": 0,
  "score_verdict": "one sentence verdict",
  "score_explanation": "short explanation of what drove the score",
  "metrics": {{
    "sentiment_score": 0,
    "adoption_likelihood": 0,
    "churn_risk": 0,
    "competitor_threat": "Low | Medium | High"
  }},
  "recommendations": [
    "recommendation 1",
    "recommendation 2",
    "recommendation 3",
    "recommendation 4"
  ]
}}

Generate exactly 6 agents with diverse roles including skeptics and supporters. \
Return ONLY the JSON object, nothing else.\
"""


def _format_company_context(company: dict) -> str:
    """Build a rich context string from the company DNA."""
    parts = [f"Company: {company.get('name', 'Unknown')}"]

    summary = company.get("summary", "")
    if summary:
        parts.append(f"Summary: {summary}")

    # ICP
    icp = company.get("icp", {})
    if icp:
        segments = icp.get("segments", [])
        if segments:
            parts.append(f"Target Segments: {', '.join(segments) if isinstance(segments, list) else str(segments)}")
        pain_points = icp.get("pain_points", [])
        if pain_points:
            parts.append(f"Pain Points: {', '.join(pain_points) if isinstance(pain_points, list) else str(pain_points)}")

    # Positioning
    positioning = company.get("positioning", {})
    if positioning:
        vp = positioning.get("value_prop", "")
        if vp:
            parts.append(f"Value Proposition: {vp}")
        diffs = positioning.get("differentiators", [])
        if diffs:
            parts.append(f"Differentiators: {', '.join(diffs) if isinstance(diffs, list) else str(diffs)}")

    # Pricing
    pricing = company.get("pricing", {})
    if pricing:
        model = pricing.get("model", "")
        if model:
            parts.append(f"Pricing Model: {model}")
        tiers = pricing.get("tiers", [])
        if tiers:
            tier_strs = []
            for t in tiers:
                if isinstance(t, dict):
                    tier_strs.append(f"{t.get('name', '')}: {t.get('price', '')}")
                else:
                    tier_strs.append(str(t))
            parts.append(f"Pricing Tiers: {'; '.join(tier_strs)}")

    # Features
    features = company.get("features", [])
    if features:
        feat_names = []
        for f in features[:10]:
            if isinstance(f, dict):
                feat_names.append(f.get("name", str(f)))
            else:
                feat_names.append(str(f))
        parts.append(f"Key Features: {', '.join(feat_names)}")

    return "\n".join(parts)


def _format_competitor_context(competitors: list) -> str:
    """Build context string for one or more competitors."""
    if not competitors:
        return "No competitor context provided."

    blocks = []
    for comp in competitors:
        parts = [f"--- {comp.get('name', 'Unknown Competitor')} ---"]
        summary = comp.get("summary", "")
        if summary:
            parts.append(f"Summary: {summary}")
        raw = comp.get("raw_profile", "")
        if raw and len(raw) > 50:
            parts.append(f"Profile: {raw[:2000]}")
        blocks.append("\n".join(parts))

    return "\n\n".join(blocks)


async def run_sandbox_simulation(
    company_context: str,
    competitor_context: str,
    scenario: str,
    prediction_question: str,
) -> dict:
    """Run the swarm-intelligence simulation via Gemini and return parsed JSON."""

    user_prompt = USER_PROMPT_TEMPLATE.format(
        company_context=company_context,
        competitor_context=competitor_context,
        scenario=scenario,
        prediction_question=prediction_question,
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SANDBOX_SYSTEM_PROMPT,
    )

    log.info("\033[1;35m[SANDBOX] Running swarm simulation...\033[0m")
    response = await model.generate_content_async(user_prompt)
    raw_text = response.text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as e:
        log.error(f"[SANDBOX] JSON parse error: {e}\nRaw: {raw_text[:500]}")
        raise ValueError(f"Simulation returned invalid JSON: {str(e)}")

    log.info(f"\033[1;32m[SANDBOX] Simulation complete — market score: {result.get('market_score', '?')}\033[0m")
    return result
