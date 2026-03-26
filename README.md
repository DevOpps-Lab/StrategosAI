# 🤖 Strategos AI — Multi-Agent Competitive Intelligence Engine

Strategos AI is a sophisticated, multi-agent platform designed to provide businesses with deep competitive intelligence. It leverages advanced AI agents to crawl, analyze, and monitor market trends, competitor moves, and strategic opportunities.

Built with a high-performance **FastAPI** backend and a modern **React** frontend, Strategos AI empowers teams to stay ahead of the curve through data-driven strategic insights, synthesized from websites, reviews, ad libraries, and online communities.

---

## ✨ Key Features & Agent Workflows

### 🧬 1. Identity / DNA Extraction
- **Company Profiling:** Automatically crawl your company's homepage, pricing, and feature pages to extract your "DNA Profile" – including Ideal Customer Profile (ICP), core value propositions, and pricing models.

### 🕵️ 2. The Scout Agent (Intel Gathering)
Automated tracking and benchmarking against key competitors across multiple vectors:
- **Website Crawling:** Maps out competitor products and pricing.
- **Review Platforms:** Scrapes **Trustpilot** and **G2** to fetch star ratings and identify recurring complaints.
- **Ad Libraries:** Analyzes **Meta Ads** and **Google Ads Transparency** to gauge marketing aggressiveness and core hooks.
- **Community Intelligence:** Deep-scans **HackerNews** and **Reddit** for organic mentions and "switching signals."
- **Product Velocity Tracker:** Scrapes competitor changelogs and release pages to calculate a Shipping Velocity Score (0-100), actively tracking how fast they iterate.

### 🧠 3. The Analyst Agent (Synthesis)
Digests raw data to generate structured strategic intelligence:
- **Feature & Pricing Gaps:** Analyzes exactly where you win and where you lose.
- **Strategic Radar Mapping:** Scores competitors on a 0-100 scale across vectors like Features, Pricing, Market Position, Growth, Enterprise Readiness, and Community.
- **Inferred Roadmaps:** Predicts competitor moves based on job postings, news, and site changes.

### 📊 4. Strategic Dashboard & Actionable Outcomes
- **Battle Cards & Radar Charts:** Direct visual comparisons of your value prop vs. competitors via Chart.js.
- **Ad Aggressiveness & Objections Tables:** Matrix views of competitor marketing spend and common customer complaints.
- **"Claim vs. Reality" Intelligence Table:** Highlights marketing-vs-reality gaps, empowering sales reps to generate evidence-based cold emails directly from the dashboard.
- **Sales Sequence Generator:** AI-generated targeted cold email sequences designed to poach competitor customers by attacking known weaknesses.
- **Google Calendar Integration:** Push strategic tasks or roadmap adjustments directly to your calendar.
- **PDF Export:** Download comprehensive, high-quality strategic reports.
- **Market Intelligence:** Live financial news headlines fetched directly from MoneyControl.

### 💬 5. AI ChatBot (The Strategist)
- Interact natively with an AI assistant possessing the full context of scraped review data, ad intelligence, and feature gaps. Interrogate the bot to write rebuttals or understand competitor weaknesses on the fly.

### 🧪 6. Business Sandbox (Swarm Intelligence Simulation)
- **Market War-Gaming:** Simulate business decisions or competitor moves before they happen in real life.
- **Swarm Reactions:** Spawns a simulated crowd of AI agents (customers, skeptics, analysts) who react organically to your scenarios.
- **Predictive Metrics:** Get actionable metrics like Adoption Likelihood, Sentiment Score, Competitor Threat Level, and an Overall Market Score (0-100).
- **Phased Architecture:** Designed to seamlessly transition from LLM-powered simulations to full [MiroFish](https://github.com/666ghj/MiroFish) swarm intelligence API integration.

---

## 🛠️ Tech Stack

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **AI Engine**: [Google Gemini Pro / Langchain](https://ai.google.dev/)
- **ORM/DB**: SQLAlchemy with SQLite (async)
- **Scheduling/Async**: Background tasks & SSE for real-time updates
- **Internal Integrations**: Google OAuth, Twilio (Voice), SMTP (Email)

### Frontend
- **Framework**: [React](https://reactjs.org/) + [Vite](https://vitejs.dev/)
- **Routing**: React Router DOM (v6)
- **Visualization**: Chart.js & React-Chartjs-2
- **Styling**: Modern CSS with Neon/Glassmorphism design
- **State/API**: Modern React Hooks and fetch for SSE streams

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- [Gemini API Key](https://aistudio.google.com/app/apikey)

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables (Create a `.env` file in the `backend` folder):
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_number
   ```
5. Run the server:
   ```bash
   python main.py
   ```
   *The backend will be available at http://localhost:8000*

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   *The frontend will be available at http://localhost:5173* (or as shown in your terminal).

---

## 📂 Project Structure

```text
Compy/
├── backend/            # FastAPI Application
│   ├── agents/         # Scout, Analyst, DNA Extractor logic
│   ├── routers/        # API endpoints (analysis, chat, voice, etc.)
│   ├── services/       # Core business logic & scheduler
│   ├── models.py       # Database schemas
│   └── main.py         # Entry point
├── frontend/           # React + Vite Application
│   ├── src/
│   │   ├── pages/      # Dashboard, Analysis, Intelligence pages
│   │   ├── components/ # Reusable UI components
│   │   └── App.jsx     # Main routing and layout
├── feats.txt           # Detailed feature and architecture specs
└── README.md           # You are here!
```

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
