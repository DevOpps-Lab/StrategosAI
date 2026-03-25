import { useState, useEffect, useRef } from 'react';
import { listCompanies, listCompetitors, runSandboxSimulation } from '../utils/api';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

const LOADING_MESSAGES = [
    'Generating agent personas...',
    'Seeding the simulation world...',
    'Running market reactions...',
    'Synthesizing report...',
];

const PLATFORM_ICONS = { Reddit: '🟠', Twitter: '🐦', HackerNews: '🟧' };
const SENTIMENT_COLORS = {
    positive: { bg: 'rgba(39, 174, 96, 0.08)', border: 'rgba(39, 174, 96, 0.25)', color: '#27ae60', label: '👍 Positive' },
    neutral: { bg: 'rgba(201, 169, 110, 0.08)', border: 'rgba(201, 169, 110, 0.25)', color: '#c9a96e', label: '😐 Neutral' },
    negative: { bg: 'rgba(192, 57, 43, 0.08)', border: 'rgba(192, 57, 43, 0.25)', color: '#c0392b', label: '👎 Negative' },
};

function getScoreColor(score) {
    if (score >= 66) return { color: '#27ae60', bg: 'rgba(39, 174, 96, 0.1)', label: '🟢' };
    if (score >= 36) return { color: '#e8a838', bg: 'rgba(232, 168, 56, 0.1)', label: '🟡' };
    return { color: '#c0392b', bg: 'rgba(192, 57, 43, 0.1)', label: '🔴' };
}

function getThreatColor(level) {
    if (level === 'Low') return '#27ae60';
    if (level === 'Medium') return '#e8a838';
    return '#c0392b';
}

export default function Sandbox({ companyId: propCompanyId, companyData: propCompanyData }) {
    // Phase management
    const [phase, setPhase] = useState('input'); // input | loading | results | error
    const [loadingMsg, setLoadingMsg] = useState('');
    const [errorMsg, setErrorMsg] = useState('');

    // Input state
    const [companies, setCompanies] = useState([]);
    const [selectedCompanyId, setSelectedCompanyId] = useState(propCompanyId || '');
    const [competitorOptions, setCompetitorOptions] = useState([]);
    const [selectedCompetitorIds, setSelectedCompetitorIds] = useState([]);
    const [scenario, setScenario] = useState('');
    const [predictionQuestion, setPredictionQuestion] = useState('');
    const [competitorDropdownOpen, setCompetitorDropdownOpen] = useState(false);

    // Results
    const [results, setResults] = useState(null);
    const resultsRef = useRef(null);

    // Load companies on mount
    useEffect(() => {
        listCompanies().then(setCompanies).catch(() => {});
    }, []);

    // Pre-select company from props
    useEffect(() => {
        if (propCompanyId && !selectedCompanyId) setSelectedCompanyId(propCompanyId);
    }, [propCompanyId]);

    // Load competitors when company changes
    useEffect(() => {
        if (!selectedCompanyId) {
            setCompetitorOptions([]);
            setSelectedCompetitorIds([]);
            return;
        }
        listCompetitors(selectedCompanyId)
            .then((comps) => {
                setCompetitorOptions(comps.filter(c => c.name));
                setSelectedCompetitorIds([]);
            })
            .catch(() => setCompetitorOptions([]));
    }, [selectedCompanyId]);

    // Toggle competitor selection
    const toggleCompetitor = (id) => {
        setSelectedCompetitorIds((prev) =>
            prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
        );
    };

    // Run simulation
    const handleRunSimulation = async () => {
        if (!selectedCompanyId || !scenario.trim()) return;

        setPhase('loading');
        setErrorMsg('');

        // Cycle through loading messages
        let msgIdx = 0;
        setLoadingMsg(LOADING_MESSAGES[0]);
        const interval = setInterval(() => {
            msgIdx++;
            if (msgIdx < LOADING_MESSAGES.length) {
                setLoadingMsg(LOADING_MESSAGES[msgIdx]);
            }
        }, 2000);

        try {
            const data = await runSandboxSimulation(
                parseInt(selectedCompanyId),
                selectedCompetitorIds.map(Number),
                scenario,
                predictionQuestion
            );
            clearInterval(interval);
            setResults(data);
            setPhase('results');
        } catch (err) {
            clearInterval(interval);
            setErrorMsg(err.message || 'Simulation failed. Please try again.');
            setPhase('error');
        }
    };

    // Reset to input
    const handleReset = () => {
        setPhase('input');
        setResults(null);
        setScenario('');
        setPredictionQuestion('');
        setSelectedCompetitorIds([]);
        setErrorMsg('');
    };

    // Export PDF
    const handleExportPDF = async () => {
        if (!resultsRef.current) return;
        try {
            const canvas = await html2canvas(resultsRef.current, {
                scale: 2,
                useCORS: true,
                backgroundColor: '#f5f0e8',
            });
            const imgData = canvas.toDataURL('image/png');
            const pdf = new jsPDF('p', 'mm', 'a4');
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
            let heightLeft = pdfHeight;
            let position = 0;

            pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, pdfHeight);
            heightLeft -= pdf.internal.pageSize.getHeight();

            while (heightLeft > 0) {
                position = heightLeft - pdfHeight;
                pdf.addPage();
                pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, pdfHeight);
                heightLeft -= pdf.internal.pageSize.getHeight();
            }

            pdf.save('sandbox-simulation-report.pdf');
        } catch (e) {
            console.error('PDF export failed:', e);
        }
    };

    // =========================================================================
    // RENDER
    // =========================================================================
    return (
        <div className="sandbox-page">
            <h1 className="page-title">🧪 Business Sandbox</h1>
            <p className="page-subtitle">
                Simulate market moves before you make them — powered by swarm intelligence.
            </p>

            {/* ─── INPUT PHASE ─── */}
            {phase === 'input' && (
                <div className="sandbox-input-phase animate-fade-in-up">
                    {/* Company Selector */}
                    <div className="sandbox-field">
                        <label className="sandbox-label">Your Company</label>
                        <select
                            id="sandbox-company-select"
                            className="sandbox-select"
                            value={selectedCompanyId}
                            onChange={(e) => setSelectedCompanyId(e.target.value)}
                        >
                            <option value="">Select a company...</option>
                            {companies.map((c) => (
                                <option key={c.id} value={c.id}>{c.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Competitor Multi-Select */}
                    <div className="sandbox-field">
                        <label className="sandbox-label">Competitor Context</label>
                        <div className="sandbox-multiselect">
                            <div
                                className="sandbox-multiselect-trigger"
                                onClick={() => setCompetitorDropdownOpen(!competitorDropdownOpen)}
                            >
                                {selectedCompetitorIds.length === 0
                                    ? <span className="sandbox-placeholder">Select competitors...</span>
                                    : <div className="sandbox-selected-tags">
                                        {selectedCompetitorIds.map((id) => {
                                            const comp = competitorOptions.find(c => c.id === id);
                                            return (
                                                <span key={id} className="sandbox-tag-chip">
                                                    {comp?.name || id}
                                                    <span
                                                        className="sandbox-tag-remove"
                                                        onClick={(e) => { e.stopPropagation(); toggleCompetitor(id); }}
                                                    >×</span>
                                                </span>
                                            );
                                        })}
                                    </div>
                                }
                                <span className="sandbox-chevron">{competitorDropdownOpen ? '▲' : '▼'}</span>
                            </div>
                            {competitorDropdownOpen && (
                                <div className="sandbox-dropdown-menu">
                                    {competitorOptions.length === 0 && (
                                        <div className="sandbox-dropdown-empty">
                                            {selectedCompanyId ? 'No competitors found' : 'Select a company first'}
                                        </div>
                                    )}
                                    {competitorOptions.map((c) => (
                                        <div
                                            key={c.id}
                                            className={`sandbox-dropdown-item ${selectedCompetitorIds.includes(c.id) ? 'selected' : ''}`}
                                            onClick={() => toggleCompetitor(c.id)}
                                        >
                                            <span className="sandbox-checkbox">
                                                {selectedCompetitorIds.includes(c.id) ? '☑' : '☐'}
                                            </span>
                                            {c.name}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Scenario */}
                    <div className="sandbox-field">
                        <label className="sandbox-label">Scenario / Additional Context</label>
                        <textarea
                            id="sandbox-scenario"
                            className="sandbox-textarea"
                            rows={4}
                            value={scenario}
                            onChange={(e) => setScenario(e.target.value)}
                            placeholder="e.g. We announce a free tier next month / Competitor drops price by 40% / We launch an enterprise API."
                        />
                    </div>

                    {/* Prediction Question */}
                    <div className="sandbox-field">
                        <label className="sandbox-label">Your Prediction Question</label>
                        <input
                            id="sandbox-prediction"
                            className="sandbox-input"
                            type="text"
                            value={predictionQuestion}
                            onChange={(e) => setPredictionQuestion(e.target.value)}
                            placeholder="e.g. How will our ICP react? Will we gain or lose market share?"
                        />
                    </div>

                    <button
                        id="sandbox-run-btn"
                        className="btn btn-primary btn-lg sandbox-run-btn"
                        onClick={handleRunSimulation}
                        disabled={!selectedCompanyId || !scenario.trim()}
                    >
                        🚀 Run Simulation
                    </button>
                </div>
            )}

            {/* ─── LOADING PHASE ─── */}
            {phase === 'loading' && (
                <div className="sandbox-loading animate-fade-in">
                    <div className="sandbox-loading-orb">
                        <div className="sandbox-loading-ring" />
                        <div className="sandbox-loading-ring sandbox-loading-ring--2" />
                        <div className="sandbox-loading-ring sandbox-loading-ring--3" />
                        <span className="sandbox-loading-icon">🧠</span>
                    </div>
                    <p className="sandbox-loading-msg">{loadingMsg}</p>
                </div>
            )}

            {/* ─── ERROR PHASE ─── */}
            {phase === 'error' && (
                <div className="sandbox-error animate-fade-in-up">
                    <div className="glass-card sandbox-error-card">
                        <span className="sandbox-error-icon">⚠️</span>
                        <h3>Simulation Failed</h3>
                        <p>{errorMsg}</p>
                        <button className="btn btn-primary" onClick={handleRunSimulation}>
                            🔄 Retry
                        </button>
                        <button className="btn btn-secondary" onClick={handleReset} style={{ marginLeft: 12 }}>
                            ← Back to Input
                        </button>
                    </div>
                </div>
            )}

            {/* ─── RESULTS PHASE ─── */}
            {phase === 'results' && results && (
                <div className="sandbox-results" ref={resultsRef}>
                    {/* Section 1: Summary */}
                    <section className="sandbox-section sandbox-anim" style={{ animationDelay: '0.1s' }}>
                        <h2 className="section-title">📋 Simulation Summary</h2>
                        <div className="glass-card--static sandbox-summary-card">
                            <p>{results.summary}</p>
                        </div>
                    </section>

                    {/* Section 2: Agent Comments */}
                    <section className="sandbox-section sandbox-anim" style={{ animationDelay: '0.3s' }}>
                        <h2 className="section-title">💬 Notable Agent Comments</h2>
                        <div className="sandbox-agents-grid">
                            {(results.agents || []).map((agent, i) => {
                                const sent = SENTIMENT_COLORS[agent.sentiment] || SENTIMENT_COLORS.neutral;
                                return (
                                    <div
                                        key={i}
                                        className="sandbox-agent-card"
                                        style={{
                                            borderLeft: `4px solid ${sent.color}`,
                                            animationDelay: `${0.35 + i * 0.08}s`,
                                        }}
                                    >
                                        <div className="sandbox-agent-header">
                                            <div className="sandbox-agent-avatar">
                                                {agent.name?.charAt(0) || '?'}
                                            </div>
                                            <div className="sandbox-agent-meta">
                                                <span className="sandbox-agent-name">{agent.name}</span>
                                                <span className="sandbox-agent-role">{agent.role}</span>
                                            </div>
                                            <span className="sandbox-agent-platform">
                                                {PLATFORM_ICONS[agent.platform] || '🌐'} {agent.platform}
                                            </span>
                                        </div>
                                        <p className="sandbox-agent-comment">"{agent.comment}"</p>
                                        <span className="sandbox-sentiment-badge" style={{
                                            background: sent.bg,
                                            border: `1px solid ${sent.border}`,
                                            color: sent.color,
                                        }}>
                                            {sent.label}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>
                    </section>

                    {/* Section 3: Market Score */}
                    <section className="sandbox-section sandbox-anim" style={{ animationDelay: '0.55s' }}>
                        <h2 className="section-title">📊 Overall Market Score</h2>
                        <div className="sandbox-score-container">
                            {(() => {
                                const sc = getScoreColor(results.market_score || 0);
                                return (
                                    <>
                                        <div className="sandbox-score-circle" style={{
                                            background: sc.bg,
                                            borderColor: sc.color,
                                        }}>
                                            <span className="sandbox-score-number" style={{ color: sc.color }}>
                                                {results.market_score}
                                            </span>
                                            <span className="sandbox-score-label">/ 100</span>
                                        </div>
                                        <p className="sandbox-score-verdict">{sc.label} {results.score_verdict}</p>
                                        <p className="sandbox-score-explanation">{results.score_explanation}</p>
                                    </>
                                );
                            })()}
                        </div>
                    </section>

                    {/* Section 4: Key Metrics */}
                    <section className="sandbox-section sandbox-anim" style={{ animationDelay: '0.7s' }}>
                        <h2 className="section-title">📈 Key Metrics</h2>
                        <div className="sandbox-metrics-grid">
                            <MetricCard
                                icon="😊"
                                name="Sentiment Score"
                                value={`${results.metrics?.sentiment_score ?? 50}/100`}
                                interpretation={results.metrics?.sentiment_score >= 60 ? 'Crowd sentiment is favorable' : results.metrics?.sentiment_score >= 40 ? 'Mixed feelings in the market' : 'Significant market resistance'}
                                color={getScoreColor(results.metrics?.sentiment_score ?? 50).color}
                            />
                            <MetricCard
                                icon="🚀"
                                name="Adoption Likelihood"
                                value={`${results.metrics?.adoption_likelihood ?? 50}%`}
                                interpretation={results.metrics?.adoption_likelihood >= 60 ? 'Strong adoption potential' : results.metrics?.adoption_likelihood >= 40 ? 'Moderate adoption expected' : 'Adoption faces headwinds'}
                                color={getScoreColor(results.metrics?.adoption_likelihood ?? 50).color}
                            />
                            <MetricCard
                                icon="⚠️"
                                name="Churn Risk"
                                value={`${results.metrics?.churn_risk ?? 50}%`}
                                interpretation={results.metrics?.churn_risk <= 30 ? 'Low risk of customer loss' : results.metrics?.churn_risk <= 60 ? 'Some customers may leave' : 'High churn danger — act fast'}
                                color={getScoreColor(100 - (results.metrics?.churn_risk ?? 50)).color}
                            />
                            <MetricCard
                                icon="🎯"
                                name="Competitor Threat"
                                value={results.metrics?.competitor_threat || 'Medium'}
                                interpretation={
                                    results.metrics?.competitor_threat === 'Low' ? 'Competitors unlikely to benefit' :
                                    results.metrics?.competitor_threat === 'High' ? 'This move may empower rivals' :
                                    'Moderate competitive impact expected'
                                }
                                color={getThreatColor(results.metrics?.competitor_threat || 'Medium')}
                            />
                        </div>
                    </section>

                    {/* Section 5: Recommendations */}
                    <section className="sandbox-section sandbox-anim" style={{ animationDelay: '0.85s' }}>
                        <h2 className="section-title">🎯 Strategic Recommendations</h2>
                        <div className="glass-card--static sandbox-recommendations">
                            <ul>
                                {(results.recommendations || []).map((rec, i) => (
                                    <li key={i}>{rec}</li>
                                ))}
                            </ul>
                        </div>
                    </section>

                    {/* Bottom Actions */}
                    <div className="sandbox-actions sandbox-anim" style={{ animationDelay: '1s' }}>
                        <button className="btn btn-secondary btn-lg" onClick={handleReset}>
                            🔄 Run Another Simulation
                        </button>
                        <button className="btn btn-primary btn-lg" onClick={handleExportPDF}>
                            📥 Export Report
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ─── Metric Card sub-component ─── */
function MetricCard({ icon, name, value, interpretation, color }) {
    return (
        <div className="sandbox-metric-card glass-card--static">
            <span className="sandbox-metric-icon">{icon}</span>
            <span className="sandbox-metric-name">{name}</span>
            <span className="sandbox-metric-value" style={{ color }}>{value}</span>
            <span className="sandbox-metric-interp">{interpretation}</span>
        </div>
    );
}
