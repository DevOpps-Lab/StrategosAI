"""AI Agent for classifying and routing strategic threats to the correct department."""
import json
import logging
import google.generativeai as genai
from config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

ESCALATION_PROMPT = """You are the Strategic Operations Assistant for a competitive intelligence platform.
Your job is to read a newly identified competitive threat and classify which internal departments need to handle it based on the problem criteria.

AVAILABLE DEPARTMENTS:
- Product (for feature gaps, UI/UX issues, missing integrations)
- Engineering (for technical performance, security vulnerabilities, uptime)
- Marketing (for positioning, messaging, branding, PR risks)
- Sales (for pricing changes, new sales tactics, discount wars)
- Customer Success (for customer churn risks, support quality, onboarding)
- Leadership (for existential threats, M&A, massive market shifts)

THREAT DESCRIPTION:
{threat}

Analyze the threat and determine the relevant departments to handle it. Also assign a priority level (low, medium, high, critical) and a brief 1-sentence reason for your choice.

Respond EXCLUSIVELY in valid JSON format matching this schema:
{{
  "departments": ["Engineering", "Leadership"],
  "priority": "high",
  "reason": "Because..."
}}
"""

async def classify_threat_for_escalation(threat_description: str) -> dict:
    """Uses Gemini to classify the threat and route to a department."""
    if not settings.GEMINI_API_KEY:
        return {"departments": ["Leadership"], "priority": "high", "reason": "Fallback: No Gemini API Key"}

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = ESCALATION_PROMPT.format(threat=threat_description)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        
        # Parse the JSON response
        result = json.loads(response.text)
        
        # Ensure fallback defaults if LLM hallucinated
        valid_departments = ["Product", "Engineering", "Marketing", "Sales", "Customer Success", "Leadership"]
        if "departments" not in result or not isinstance(result["departments"], list):
            # Fallback if the AI uses the old schema
            if "department" in result and isinstance(result["department"], str):
                result["departments"] = [result["department"]]
            else:
                result["departments"] = ["Leadership"]
                
        result["departments"] = [d for d in result["departments"] if d in valid_departments]
        if not result["departments"]:
            result["departments"] = ["Leadership"]
            
        return result
        
    except Exception as e:
        logger.error(f"Error classifying threat for escalation: {str(e)}")
        # Fallback to Leadership for manual triage if AI fails
        return {
            "departments": ["Leadership"], 
            "priority": "high", 
            "reason": f"AI Parsing Error: {str(e)}"
        }
