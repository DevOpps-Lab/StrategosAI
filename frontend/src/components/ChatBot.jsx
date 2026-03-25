import { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../utils/api';

const BASE_QUESTIONS = [
    "Write and send a cold email to test@example.com",
    "Why are customers leaving this competitor?",
    "What's their biggest pricing weakness?",
    "Who should we target first?",
];

const REVIEW_QUESTIONS = [
    "What objections should I address in sales calls?",
    "What do their customers love most?",
];

const AD_QUESTIONS = [
    "What ad angles are they using?",
    "How can I counter their messaging?",
];

const COMMUNITY_QUESTIONS = [
    "Are users complaining on Reddit?",
    "Show me HackerNews sentiment.",
    "Any switching signals from the community?",
];

function buildReviewSummary(reviewData) {
    if (!reviewData || reviewData.length === 0) return 'No review data available';
    const parts = [];
    for (const r of reviewData) {
        if (r.scraper_status !== 'success') continue;
        const src = 'Trustpilot';
        parts.push(`${src}: ${r.overall_rating}/5 (${r.review_count} reviews)`);
        if (r.likes?.length) parts.push(`  Likes: ${r.likes.slice(0, 3).join('; ')}`);
        if (r.dislikes?.length) parts.push(`  Dislikes: ${r.dislikes.slice(0, 3).join('; ')}`);
        if (r.negative_themes?.length) parts.push(`  Complaints: ${r.negative_themes.join(', ')}`);
    }
    return parts.length ? parts.join('\n') : 'No review data available';
}

function buildAdSummary(adData) {
    if (!adData || adData.length === 0) return 'No ad data available';
    const parts = [];
    for (const a of adData) {
        if (a.scraper_status !== 'success') continue;
        const src = a.source === 'meta_ads' ? 'Meta Ads' : 'Google Ads';
        parts.push(`${src}: ${a.total_ads_found} active ads`);
        if (a.top_messaging_themes?.length) parts.push(`  Themes: ${a.top_messaging_themes.join(', ')}`);
        if (a.top_keywords?.length) parts.push(`  Keywords: ${a.top_keywords.slice(0, 5).join(', ')}`);
        if (a.cta_distribution && Object.keys(a.cta_distribution).length) parts.push(`  CTAs: ${Object.entries(a.cta_distribution).map(([k,v]) => `${k} (${v})`).join(', ')}`);
    }
    return parts.length ? parts.join('\n') : 'No ad data available';
}

function buildCommunityIntelSummary(communityIntelData) {
    if (!communityIntelData || communityIntelData.length === 0) return 'No community intelligence available';
    const parts = [];
    for (const c of communityIntelData) {
        if (c.scraper_status !== 'success') continue;
        const src = c.source === 'hackernews' ? 'Hacker News' : 'Reddit Deep';
        parts.push(`=== ${src} (${c.total_mentions} mentions) ===`);
        parts.push(`Sentiment Score: ${c.sentiment_score}/100`);
        if (c.switching_signals?.length) {
            parts.push(`Switching Signals: ${c.switching_signals.slice(0, 3).map(s => `"${s.signal || s.text || s.body}"`).join(' | ')}`);
        }
        if (c.source === 'reddit_deep' && c.complaints?.length) {
            parts.push(`Top Reddit Complaints: ${c.complaints.slice(0, 3).map(cmp => `"${cmp.title}"`).join(' | ')}`);
        }
        if (c.source === 'hackernews' && c.positive_comments?.length) {
            parts.push(`Top HN Praise: ${c.positive_comments.slice(0, 2).map(p => `"${p.text.substring(0, 80)}..."`).join(' | ')}`);
        }
    }
    return parts.length ? parts.join('\n') : 'No community intelligence available';
}

export default function ChatBot({ competitorId, competitorName, analysisData, reviewData = [], adData = [], communityIntelData = [] }) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        {
            role: 'assistant',
            content: `👋 I'm StrategosAI — your Competitive Intelligence Analyst. I have a full dossier on **${competitorName || 'your competitor'}**. Ask me anything about their pricing weaknesses, who to target, or how to position against them.`
        }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        if (isOpen) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            inputRef.current?.focus();
        }
    }, [messages, isOpen]);

    // Reset chat when competitor changes
    useEffect(() => {
        setMessages([{
            role: 'assistant',
            content: `👋 I'm StrategosAI — your Competitive Intelligence Analyst. I have a full dossier on **${competitorName || 'your competitor'}**. Ask me anything about their pricing weaknesses, who to target, or how to position against them.`
        }]);
    }, [competitorId, competitorName]);

    const sendMessage = async (text) => {
        const messageText = text || inputValue.trim();
        if (!messageText || isLoading || !competitorId) return;

        const userMessage = { role: 'user', content: messageText };
        const newMessages = [...messages, userMessage];
        setMessages(newMessages);
        setInputValue('');
        setIsLoading(true);

        // Build history to send (exclude the initial greeting)
        const historyToSend = newMessages.slice(1, -1).map(m => ({
            role: m.role === 'assistant' ? 'assistant' : 'user',
            content: m.content
        }));

        // Build context object with review/ad summaries
        const context = {
            competitor_name: analysisData?.competitor_name || competitorName || "Unknown",
            competitor_url: "",
            pricing_model: analysisData?.pricing_intelligence?.model || "Unknown",
            pricing_complaints: analysisData?.pricing_intelligence?.pricing_complaints || [],
            community_price_perception: analysisData?.pricing_intelligence?.community_price_perception || "Unknown",
            we_win: (analysisData?.feature_gap_analysis?.we_win || []).map(f => f.feature || f.area || String(f)),
            they_win: (analysisData?.feature_gap_analysis?.they_win || []).map(f => f.feature || f.area || String(f)),
            sentiment_score: String(analysisData?.community_sentiment?.overall_score || "N/A"),
            sentiment_trend: analysisData?.community_sentiment?.sentiment_trend || "N/A",
            top_praise: (analysisData?.community_sentiment?.top_praise || []).map(p => p.point || String(p)),
            top_complaints: (analysisData?.community_sentiment?.top_complaints || []).map(c => c.point || String(c)),
            positioning: typeof analysisData?.positioning === 'string' ? analysisData.positioning : JSON.stringify(analysisData?.positioning || {}),
            review_summary: buildReviewSummary(reviewData),
            ad_summary: buildAdSummary(adData),
            community_intel_summary: buildCommunityIntelSummary(communityIntelData),
        };

        try {
            const result = await sendChatMessage(competitorId, context, historyToSend, messageText);
            setMessages(prev => [...prev, { role: 'assistant', content: result.reply }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: `❌ Sorry, I hit an error: ${err.message}` }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <>
            {/* Floating Chat Bubble */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    position: 'fixed',
                    bottom: '24px',
                    right: '24px',
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    background: 'var(--accent)',
                    border: 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.5rem',
                    zIndex: 1000,
                    boxShadow: '0 4px 20px rgba(108, 92, 231, 0.5)',
                    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                }}
                onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.1)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
                title="Ask StrategosAI"
            >
                {isOpen ? '✕' : '🧠'}
            </button>

            {/* Chat Panel */}
            {isOpen && (
                <div style={{
                    position: 'fixed',
                    bottom: '92px',
                    right: '24px',
                    width: '380px',
                    maxHeight: '550px',
                    borderRadius: '16px',
                    background: 'var(--bg-card)',
                    backdropFilter: 'blur(20px)',
                    border: '1px solid var(--border-color)',
                    boxShadow: 'var(--shadow-lg)',
                    display: 'flex',
                    flexDirection: 'column',
                    zIndex: 999,
                    overflow: 'hidden',
                }}>
                    {/* Header */}
                    <div style={{
                        padding: '14px 18px',
                        borderBottom: '1px solid var(--border-color)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        background: 'var(--bg-secondary)',
                    }}>
                        <span style={{ fontSize: '1.2rem' }}>🧠</span>
                        <div>
                            <div style={{ fontWeight: '700', fontSize: '0.95rem', color: 'var(--text-primary)' }}>StrategosAI Analyst</div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }}></span>
                                {competitorName ? `Briefed on ${competitorName}` : 'Online'}
                            </div>
                        </div>
                    </div>

                    {/* Messages */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                        maxHeight: '320px',
                    }}>
                        {messages.map((msg, i) => (
                            <div key={i} style={{
                                display: 'flex',
                                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            }}>
                                <div style={{
                                    maxWidth: '85%',
                                    padding: '10px 14px',
                                    borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                                    background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-secondary)',
                                    color: msg.role === 'user' ? '#fff' : 'var(--text-primary)',
                                    fontSize: '0.875rem',
                                    lineHeight: '1.5',
                                    whiteSpace: 'pre-wrap',
                                }}>
                                    {msg.content}
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                                <div style={{
                                    padding: '12px 16px',
                                    borderRadius: '16px 16px 16px 4px',
                                    background: 'var(--bg-secondary)',
                                    display: 'flex',
                                    gap: '4px',
                                    alignItems: 'center',
                                }}>
                                    {[0, 1, 2].map(i => (
                                        <span key={i} style={{
                                            width: '6px', height: '6px', borderRadius: '50%',
                                            background: 'var(--accent)',
                                            animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                                            display: 'inline-block',
                                        }} />
                                    ))}
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Suggested Questions (only for first message) */}
                    {messages.length === 1 && (
                        <div style={{ padding: '0 16px 8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {[
                                ...BASE_QUESTIONS,
                                ...(reviewData.some(r => r.scraper_status === 'success') ? REVIEW_QUESTIONS : []),
                                ...(adData.some(a => a.scraper_status === 'success') ? AD_QUESTIONS : []),
                                ...(communityIntelData.some(c => c.scraper_status === 'success') ? COMMUNITY_QUESTIONS : []),
                            ].map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => sendMessage(q)}
                                    style={{
                                        textAlign: 'left',
                                        padding: '8px 12px',
                                        background: 'transparent',
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '8px',
                                        color: 'var(--text-secondary)',
                                        fontSize: '0.8rem',
                                        cursor: 'pointer',
                                        transition: 'background 0.15s',
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
                                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Input */}
                    <div style={{
                        padding: '12px 16px',
                        borderTop: '1px solid var(--border-color)',
                        display: 'flex',
                        gap: '8px',
                        alignItems: 'flex-end',
                        background: 'var(--bg-card)'
                    }}>
                        <textarea
                            ref={inputRef}
                            rows={1}
                            placeholder={competitorId ? "Ask anything about this competitor..." : "Open a competitor first to start chatting"}
                            value={inputValue}
                            onChange={e => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={isLoading || !competitorId}
                            style={{
                                flex: 1,
                                background: 'transparent',
                                border: '1px solid var(--border-color)',
                                borderRadius: '10px',
                                color: 'var(--text-primary)',
                                padding: '10px 12px',
                                fontSize: '0.875rem',
                                resize: 'none',
                                outline: 'none',
                                fontFamily: 'inherit',
                                lineHeight: '1.4',
                                maxHeight: '80px',
                                overflowY: 'auto',
                            }}
                        />
                        <button
                            onClick={() => sendMessage()}
                            disabled={isLoading || !inputValue.trim() || !competitorId}
                            style={{
                                width: '38px',
                                height: '38px',
                                borderRadius: '10px',
                                background: inputValue.trim() && !isLoading
                                    ? 'var(--accent)'
                                    : 'var(--bg-secondary)',
                                border: 'none',
                                cursor: inputValue.trim() && !isLoading ? 'pointer' : 'not-allowed',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: inputValue.trim() && !isLoading ? '#fff' : 'var(--text-muted)',
                                fontSize: '1rem',
                                transition: 'background 0.2s',
                                flexShrink: 0,
                            }}
                        >
                            ➤
                        </button>
                    </div>
                </div>
            )}

            <style>{`
                @keyframes bounce {
                    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
                    30% { transform: translateY(-6px); opacity: 1; }
                }
            `}</style>
        </>
    );
}
