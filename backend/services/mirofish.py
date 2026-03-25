"""MiroFish integration service — Phase 2 swarm simulation backend.

When USE_MIROFISH is True in config, the sandbox router will call MiroFish
instead of the LLM-based simulation agent.
"""

import logging
import httpx
from config import settings

log = logging.getLogger(__name__)


def generate_seed_document(
    company_context: str,
    competitor_context: str,
    scenario: str,
) -> str:
    """Format company + competitor + scenario into a MiroFish seed document.

    MiroFish expects a plain-text document that describes the market context.
    This is pure string templating over data we already have.
    """
    parts = []

    parts.append("=== COMPANY CONTEXT ===")
    parts.append(company_context)
    parts.append("")
    parts.append("=== COMPETITOR CONTEXT ===")
    parts.append(competitor_context)
    parts.append("")
    parts.append("=== SCENARIO ===")
    parts.append(scenario)

    return "\n".join(parts)


async def run_mirofish_simulation(
    seed_document: str,
    prediction_question: str,
    num_agents: int = 25,
    num_rounds: int = 15,
) -> dict:
    """Call the MiroFish backend API and return the simulation results.

    This POSTs the seed document to MiroFish, polls for completion,
    then parses the report into the same JSON structure the frontend expects.

    Args:
        seed_document: Plain text context document
        prediction_question: The question to test
        num_agents: Number of simulated agents (default 25)
        num_rounds: Simulation rounds (default 15)

    Returns:
        dict matching the sandbox response schema
    """
    base_url = settings.MIROFISH_BACKEND_URL.rstrip("/")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Start simulation
        log.info(f"\033[1;35m[MIROFISH] Starting simulation at {base_url}...\033[0m")

        try:
            resp = await client.post(
                f"{base_url}/api/simulate",
                json={
                    "seed_document": seed_document,
                    "prediction_question": prediction_question,
                    "num_agents": num_agents,
                    "num_rounds": num_rounds,
                },
            )
            resp.raise_for_status()
            result = resp.json()
        except httpx.HTTPStatusError as e:
            log.error(f"[MIROFISH] HTTP error: {e}")
            raise ValueError(f"MiroFish API error: {e.response.status_code}")
        except httpx.ConnectError:
            raise ValueError(
                "Cannot connect to MiroFish backend. "
                "Make sure MiroFish is running at " + base_url
            )
        except Exception as e:
            log.error(f"[MIROFISH] Error: {e}")
            raise ValueError(f"MiroFish request failed: {str(e)}")

    # Map MiroFish output to our expected schema
    # NOTE: Adjust this mapping once MiroFish output format is confirmed
    return _normalize_mirofish_output(result)


def _normalize_mirofish_output(raw: dict) -> dict:
    """Convert MiroFish raw output into the standard sandbox response schema.

    This is the seam — adjust mappings here when MiroFish output format
    is finalized. The frontend never needs to change.
    """
    # For now, assume MiroFish returns a compatible structure
    # or do a best-effort mapping
    return {
        "summary": raw.get("summary", "Simulation complete."),
        "agents": raw.get("agents", []),
        "market_score": raw.get("market_score", 50),
        "score_verdict": raw.get("score_verdict", ""),
        "score_explanation": raw.get("score_explanation", ""),
        "metrics": {
            "sentiment_score": raw.get("metrics", {}).get("sentiment_score", 50),
            "adoption_likelihood": raw.get("metrics", {}).get("adoption_likelihood", 50),
            "churn_risk": raw.get("metrics", {}).get("churn_risk", 50),
            "competitor_threat": raw.get("metrics", {}).get("competitor_threat", "Medium"),
        },
        "recommendations": raw.get("recommendations", []),
    }
