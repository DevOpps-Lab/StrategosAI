import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { useState } from 'react';
import Landing from './pages/Landing';
import Onboarding from './pages/Onboarding';
import CompetitorAdd from './pages/CompetitorAdd';
import Analysis from './pages/Analysis';
import Dashboard from './pages/Dashboard';
import CompareView from './pages/CompareView';
import ChatBot from './components/ChatBot';
import { getReviews, getAds, getCommunityIntel } from './utils/api';

function App() {
    const [companyId, setCompanyId] = useState(null);
    const [companyData, setCompanyData] = useState(null);

    // Multi-competitor state
    const [competitors, setCompetitors] = useState([]);         // [{id, name, url, status, page_count}]
    const [activeCompetitorId, setActiveCompetitorId] = useState(null);
    const [analysisDataMap, setAnalysisDataMap] = useState({});  // { competitorId: analysisResult }
    const [planDataMap, setPlanDataMap] = useState({});           // { competitorId: planResult }
    const [reviewDataMap, setReviewDataMap] = useState({});       // { competitorId: [reviewRecords] }
    const [adDataMap, setAdDataMap] = useState({});               // { competitorId: [adRecords] }
    const [communityIntelMap, setCommunityIntelMap] = useState({}); // { competitorId: [communityIntelRecords] }

    const addCompetitorToList = (comp) => {
        setCompetitors((prev) => {
            const exists = prev.find((c) => String(c.id) === String(comp.id));
            if (exists) return prev.map((c) => (String(c.id) === String(comp.id) ? { ...c, ...comp } : c));
            return [...prev, comp];
        });
        if (!activeCompetitorId) setActiveCompetitorId(comp.id);
    };

    const updateCompetitorInList = (comp) => {
        setCompetitors((prev) =>
            prev.map((c) => (String(c.id) === String(comp.id) ? { ...c, ...comp } : c))
        );
    };

    const setAnalysisData = (competitorId, data) => {
        setAnalysisDataMap((prev) => ({ ...prev, [competitorId]: data }));
        // Auto-fetch review, ad, and community intel data when analysis completes
        getReviews(competitorId).then(r => setReviewDataMap(prev => ({ ...prev, [competitorId]: r }))).catch(() => {});
        getAds(competitorId).then(a => setAdDataMap(prev => ({ ...prev, [competitorId]: a }))).catch(() => {});
        getCommunityIntel(competitorId).then(c => setCommunityIntelMap(prev => ({ ...prev, [competitorId]: c }))).catch(() => {});
    };

    const setPlanData = (competitorId, data) => {
        setPlanDataMap((prev) => ({ ...prev, [competitorId]: data }));
    };

    const hasCompetitors = competitors.length > 0;
    const activeAnalysis = analysisDataMap[activeCompetitorId] || null;
    const activePlan = planDataMap[activeCompetitorId] || null;

    return (
        <BrowserRouter>
            <Routes>
                {/* Standalone Landing Page Route */}
                <Route 
                    path="/" 
                    element={
                        <Landing 
                            onComplete={(company) => {
                                setCompanyId(company.id);
                                setCompanyData(company);
                            }} 
                        />
                    } 
                />

                {/* Main Application Routes */}
                <Route 
                    path="/*" 
                    element={
                        <div className="app-layout">
                            <nav className="navbar">
                                <div className="navbar-brand">
                                    <div className="logo">🎯</div>
                                    <span>StrategosAI</span>
                                </div>
                                <ul className="navbar-nav">
                                    <li><NavLink to="/app" end>Onboard</NavLink></li>
                                    <li>
                                        <NavLink to="/competitor" className={!companyId ? 'disabled' : ''}>
                                            Scout
                                        </NavLink>
                                    </li>
                                    <li>
                                        <NavLink to="/analysis" className={!hasCompetitors ? 'disabled' : ''}>
                                            Analyze
                                        </NavLink>
                                    </li>
                                    <li>
                                        <NavLink to="/dashboard" className={!hasCompetitors ? 'disabled' : ''}>
                                            Dashboard
                                        </NavLink>
                                    </li>
                                </ul>

                            </nav>

                            <div className="page-container">
                                <Routes>
                                    <Route
                                        path="/app"
                                        element={
                                            <Onboarding
                                                onComplete={(company) => {
                                                    setCompanyId(company.id);
                                                    setCompanyData(company);
                                                }}
                                                companyData={companyData}
                                            />
                                        }
                                    />
                                    <Route
                                        path="/competitor"
                                        element={
                                            companyId ? (
                                                <CompetitorAdd
                                                    companyId={companyId}
                                                    competitors={competitors}
                                                    onCompetitorAdded={addCompetitorToList}
                                                    onCompetitorUpdated={updateCompetitorInList}
                                                    onSelectCompetitor={setActiveCompetitorId}
                                                    activeCompetitorId={activeCompetitorId}
                                                />
                                            ) : (
                                                <Navigate to="/" replace />
                                            )
                                        }
                                    />
                                    <Route
                                        path="/analysis"
                                        element={
                                            hasCompetitors ? (
                                                <Analysis
                                                    competitors={competitors}
                                                    activeCompetitorId={activeCompetitorId}
                                                    onSelectCompetitor={setActiveCompetitorId}
                                                    analysisDataMap={analysisDataMap}
                                                    planDataMap={planDataMap}
                                                    onAnalysisComplete={(id, data) => setAnalysisData(id, data)}
                                                    onPlanComplete={(id, data) => setPlanData(id, data)}
                                                />
                                            ) : (
                                                <Navigate to="/" replace />
                                            )
                                        }
                                    />
                                    <Route
                                        path="/dashboard"
                                        element={
                                            hasCompetitors ? (
                                                <Dashboard
                                                    competitors={competitors}
                                                    activeCompetitorId={activeCompetitorId}
                                                    onSelectCompetitor={setActiveCompetitorId}
                                                    companyData={companyData}
                                                    analysisDataMap={analysisDataMap}
                                                    planDataMap={planDataMap}
                                                    reviewDataMap={reviewDataMap}
                                                    adDataMap={adDataMap}
                                                    communityIntelMap={communityIntelMap}
                                                />
                                            ) : (
                                                <Navigate to="/" replace />
                                            )
                                        }
                                    />
                                    <Route
                                        path="/compare"
                                        element={
                                            companyId ? (
                                                <CompareView
                                                    companyId={companyId}
                                                    companyData={companyData}
                                                />
                                            ) : (
                                                <Navigate to="/" replace />
                                            )
                                        }
                                    />
                                </Routes>
                            </div>

                            {/* Global floating AI Analyst Chatbot - ONLY visible if analysis exists */}
                            {activeAnalysis && (
                                <ChatBot
                                    competitorId={activeCompetitorId}
                                    competitorName={competitors.find(c => c.id === activeCompetitorId)?.name || null}
                                    analysisData={activeAnalysis}
                                    reviewData={reviewDataMap[activeCompetitorId] || []}
                                    adData={adDataMap[activeCompetitorId] || []}
                                    communityIntelData={communityIntelMap[activeCompetitorId] || []}
                                />
                            )}
                        </div>
                    } 
                />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
