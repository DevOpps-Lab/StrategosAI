# StrategosAI — Business Sandbox Feature Spec

---

## Overview

The Business Sandbox lets a company test a business decision or simulate a competitor move before it happens in real life. You describe a scenario, select the market context from existing data, and the system spawns a simulated crowd of AI agents — customers, skeptics, power users, competitor loyalists, enterprise buyers, analysts — who react to the scenario organically. The output is a structured simulation report: what the crowd felt, what individuals said, an overall market score, and key business metrics. Think of it as a war-gaming sandbox — try your move, see how the market reacts, then decide whether to go live with it.

This feature is inspired by [MiroFish](https://github.com/666ghj/MiroFish), an open source swarm intelligence simulation engine. Phase 1 builds the full Business Sandbox using the existing LLM backend to simulate what MiroFish would produce. Phase 2 swaps in real MiroFish API calls. The architecture is designed with that seam in mind from day one.

---

## Part 1 — Build the Feature (Phase 1: LLM-Powered Simulation)

### 1.1 Navigation Entry Point

Add a **"Business Sandbox"** button on the main StrategosAI dashboard that navigates to `/sandbox`.

---

### 1.2 The /sandbox Page — Input Phase

A clean page with:

- **Header:** "Business Sandbox"
- **Subtitle:** "Simulate market moves before you make them — powered by swarm intelligence."

The input phase leverages our existing database of companies and competitors. Instead of typing out full contexts manually, the system pulls in recorded intelligence.

Four input fields:

**Field 1 — Your Company (Dropdown Selector)**
A dropdown selector populated with existing companies in the system (e.g., "PayPal"). Selecting this automatically pulls the company's DNA (ICP, value props, pricing) as foundational context for the simulation.

**Field 2 — Competitor Context (Multi-select Dropdown)**
A dropdown to select one or more known competitors stored in StrategosAI (e.g., "Apple Pay", "Stripe"). This links their existing intelligence data to the simulation automatically.

**Field 3 — Scenario / Additional Context (Textarea)**
A large textarea allowing you to detail the move you want to simulate or provide minimal additional context.
> Placeholder: "e.g. We announce a free tier next month / Competitor drops price by 40% / We launch an enterprise API."

**Field 4 — Your Prediction Question (Text Input)**
A smaller input field narrowing down what you are testing for.
> Placeholder: "e.g. How will our ICP react? Will we gain or lose market share?"

**Run Simulation Button**
Multi-step loading state that cycles through these messages in sequence (2 seconds each):
1. "Generating agent personas..."
2. "Seeding the simulation world..."
3. "Running market reactions..."
4. "Synthesizing report..."

---

### 1.3 The /sandbox Page — Results Phase

Once the LLM responds, transition the page smoothly into results view inline — do not navigate away. Stagger section appearances with subtle animations to make it feel like a live feed loading in.

---

#### Section 1 — Simulation Summary

A 3 to 5 sentence paragraph describing what happened in the simulated market:
- What was the dominant reaction?
- Which segments were positive, which resisted?
- What narrative emerged?

---

#### Section 2 — Notable Agent Comments

A social-feed style list of **6 individual agent reactions**. Each agent card shows:

| Field | Example |
|---|---|
| Name | Generated persona name |
| Role | "Frustrated SMB User", "Enterprise Procurement Lead", "Competitor Loyalist", "Early Adopter", "Price-Sensitive Buyer", "Industry Analyst" |
| Platform | Reddit / Twitter / HackerNews |
| Comment | 1 to 3 sentences written in the agent's voice |
| Sentiment | positive / neutral / negative |

Style these as cards that look like social media posts. Reflect realistic market diversity — some positive, some skeptical, some hostile.

---

#### Section 3 — Overall Market Score

A large bold number out of 100 centered on screen with:
- A one-sentence verdict below it
- A short explanation of what drove the score up or down
- Color coding:
  - 🟢 Green: 66–100
  - 🟡 Yellow: 36–65
  - 🔴 Red: 0–35

---

#### Section 4 — Key Metrics

Four cards in a row:

| Metric | Type | Description |
|---|---|---|
| Sentiment Score | 0–100 | Overall crowd sentiment |
| Adoption Likelihood | Percentage | Likelihood of positive adoption |
| Churn Risk | Percentage | Risk of existing customers churning |
| Competitor Threat Level | Low / Medium / High | How much this move benefits a competitor |

Each card has an icon, metric name, value, and a one-line interpretation.

---

#### Section 5 — Strategic Recommendation

A bullet list of **3 to 4 actionable recommendations** based on simulation results. Written as direct strategic advice, not generic suggestions.

---

#### Bottom Actions

Two buttons at the bottom of the results:
- **"Run Another Simulation"** — resets page to input phase
- **"Export Report"** — generates a PDF using the existing `jsPDF` + `html2canvas` setup already in StrategosAI

---

### 1.4 LLM Prompt Architecture

When the user hits Run Simulation, send a single structured prompt to the existing LLM backend.

**System Prompt (send this as the system role):**

```
You are a swarm intelligence simulation engine. You simulate how a realistic and diverse market crowd of autonomous agents reacts to a business scenario. Your agents must have distinct voices, realistic skepticism, and varied motivations. Do not produce generic marketing analysis. Produce a grounded, honest simulation where some agents will resist, some will champion, and some will be indifferent. Base everything strictly on the company and competitor context provided. Respond only in valid JSON with no preamble, no markdown, no code fences.
```

**User Prompt (constructed dynamically):**

```
Company Context:
[Auto-injected from selected Primary Company]

Competitor Context:
[Auto-injected from selected Competitors]

Scenario:
{scenario}

Prediction Question:
{prediction_question}

Simulate this scenario and return a JSON object with this exact structure:

{
  "summary": "3 to 5 sentence paragraph of what happened in the simulated market",
  "agents": [
    {
      "name": "string",
      "role": "string",
      "platform": "Reddit | Twitter | HackerNews",
      "comment": "string",
      "sentiment": "positive | neutral | negative"
    }
  ],
  "market_score": <number 0-100>,
  "score_verdict": "one sentence verdict",
  "score_explanation": "short explanation of what drove the score",
  "metrics": {
    "sentiment_score": <number 0-100>,
    "adoption_likelihood": <number 0-100>,
    "churn_risk": <number 0-100>,
    "competitor_threat": "Low | Medium | High"
  },
  "recommendations": [
    "recommendation 1",
    "recommendation 2",
    "recommendation 3",
    "recommendation 4"
  ]
}
```

**Error Handling:**
- Parse JSON response safely
- If malformed JSON is returned, show a friendly error message and a Retry button
- Do not crash the UI

---

## Part 2 — MiroFish Setup (Phase 2: Real Swarm Simulation)

Once Phase 1 is working and validated, replace the LLM simulation calls with real MiroFish simulation runs. Here is the full setup guide.

---

### 2.1 Prerequisites

Before cloning the repo, verify all three of these on your machine:

```bash
node -v        # Must be 18 or higher
python --version   # Must be 3.11 or 3.12 — NOT 3.13
uv --version   # If missing: pip install uv
```

---

### 2.2 Get Your API Keys

You need two keys before setup:

**Key 1 — LLM API (Gemini)**

You already have this. Your Gemini API key from Google AI Studio.

**Key 2 — Zep Cloud (Agent Memory)**

1. Go to [app.getzep.com](https://app.getzep.com)
2. Sign up for a free account (no credit card required)
3. Go to **Project Settings → Project Keys**
4. Click **Add Key**, name it anything (e.g. `mirofish-test`), click Create
5. Copy the key — it will start with `z_`

---

### 2.3 Clone and Configure MiroFish

```bash
git clone https://github.com/666ghj/MiroFish.git
cd MiroFish
cp .env.example .env
```

Open `.env` and fill in the following:

```env
# Gemini via OpenAI-compatible endpoint
LLM_API_KEY=your_gemini_api_key_here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL_NAME=gemini-2.0-flash

# Zep Cloud
ZEP_API_KEY=your_zep_api_key_here
```

---

### 2.4 Install and Run

```bash
# Install all dependencies in one command
npm run setup:all

# Start both frontend and backend
npm run dev
```

MiroFish will be available at:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

---

### 2.5 Proof of Concept — Test It Raw First

Before integrating with StrategosAI, validate that MiroFish produces useful output by running it standalone.

Open MiroFish at `http://localhost:3000` and paste in this seed document:

```
Notion is a productivity and collaboration SaaS tool used by startups and SMBs. 
Their pricing is $8/user/month for Plus and $15/user/month for Business. 

Common customer complaints include: too slow on large databases, offline mode is 
unreliable, too complex to onboard non-technical users, customer support is slow. 

Their main ad messaging focuses on "one tool for everything." They recently started 
hiring enterprise sales reps, suggesting an upmarket move. Reddit and HackerNews 
sentiment is mostly positive among power users but increasingly negative among new 
users who find the learning curve too steep.

Linear is a competing project management tool. Users frequently say they switched 
from Notion because it was too slow and too complex. Linear's strengths are speed, 
clean UX, and developer-focused workflows. Linear's weakness is no docs or wiki support.
```

Prediction question:
```
If Notion announces a 30% price increase for Business tier next month, how will their 
user base react, and what is the opportunity for Linear to capture switching users?
```

**Keep your first simulation small:** 20–30 agents, 15–20 rounds. Fast, cheap, enough to judge quality.

---

### 2.6 Phase 2 Integration — Swap MiroFish into StrategosAI

Once MiroFish is running locally and producing good output, replace the LLM simulation call in the Business Sandbox with a real MiroFish run.

The integration is two steps:

**Step 1 — Seed document generator**

Write a function in the StrategosAI backend that takes the company context, competitor context, and scenario from the sandbox form and formats them into a plain text seed document. This is just string templating over data you already have.

**Step 2 — Call MiroFish backend**

Replace the LLM API call with a POST request to MiroFish's backend at `http://localhost:5001` passing the seed document and prediction question. Poll for completion, then parse MiroFish's report into the same JSON structure the frontend already expects. The frontend does not need to change at all.

---

### 2.7 Storage Considerations (Windows)

MiroFish disk usage breakdown on Windows:

| Component | Approximate Size |
|---|---|
| Python virtual environment + packages | 400–600 MB |
| Node modules (frontend) | 200–300 MB |
| Running process RAM usage | 300–500 MB |
| Repo itself | 50–100 MB |

**Total: ~1–1.2 GB.** You need at least 2 GB of free disk space before cloning. Check free space in File Explorer → right click C drive → Properties before starting.

---

## Summary — What Gets Built and When

| Phase | What | How |
|---|---|---|
| Phase 1 | Full Business Sandbox UI + simulation flow | Existing LLM backend in StrategosAI |
| Phase 2 | Real swarm simulation with distinct agent memory and emergent behavior | MiroFish running locally, called from StrategosAI backend |

Phase 1 is fully functional and demoable on its own. Phase 2 makes it real.
