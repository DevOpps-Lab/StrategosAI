import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamChatMessage, sendChatMessage } from '../utils/api';

/* ──────────────────────────────────────────────────────────
   Suggested Questions — dynamically picked from available data
   ────────────────────────────────────────────────────────── */
const BASE_QUESTIONS = [
    "What's their biggest weakness I can exploit?",
    "Write and send a cold email to test@example.com",
    "How should I position against them in a sales call?",
    "Who should we target first and why?",
];

const REVIEW_QUESTIONS = [
    "What objections should I address in sales calls?",
    "What do their customers complain about the most?",
];

const AD_QUESTIONS = [
    "What ad angles are they using?",
    "How can I counter their messaging?",
];

const COMMUNITY_QUESTIONS = [
    "Are users complaining about them on Reddit?",
    "Any switching signals from the community?",
    "Show me the HackerNews sentiment breakdown.",
];

/* ──────────────────────────────────────────────────────────
   Context builders — create text summaries from raw data
   ────────────────────────────────────────────────────────── */
function buildReviewSummary(reviewData) {
    if (!reviewData || reviewData.length === 0) return 'No review data available';
    const parts = [];
    for (const r of reviewData) {
        if (r.scraper_status !== 'success') continue;
        parts.push(`Trustpilot: ${r.overall_rating}/5 (${r.review_count} reviews)`);
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

/* ──────────────────────────────────────────────────────────
   Helpers
   ────────────────────────────────────────────────────────── */
const LS_KEY = (id) => `strategosai_chat_${id}`;

/** Parse follow_ups JSON from end of AI response text */
function parseFollowUps(text) {
    if (!text) return { cleanText: text || '', followUps: [] };
    // Look for ```json\n{"follow_ups": [...]}``` at the end
    const regex = /```json\s*\n?\s*\{[\s\S]*?"follow_ups"\s*:\s*\[[\s\S]*?\]\s*\}\s*\n?\s*```\s*$/;
    const match = text.match(regex);
    if (!match) return { cleanText: text, followUps: [] };
    const cleanText = text.slice(0, match.index).trimEnd();
    try {
        const parsed = JSON.parse(match[0].replace(/```json\s*\n?/, '').replace(/\n?\s*```/, ''));
        return { cleanText, followUps: parsed.follow_ups || [] };
    } catch {
        return { cleanText: text, followUps: [] };
    }
}

function getSmartQuestions(analysisData, reviewData, adData, communityIntelData) {
    const questions = [...BASE_QUESTIONS];
    if (reviewData?.some(r => r.scraper_status === 'success')) questions.push(...REVIEW_QUESTIONS);
    if (adData?.some(a => a.scraper_status === 'success')) questions.push(...AD_QUESTIONS);
    if (communityIntelData?.some(c => c.scraper_status === 'success')) questions.push(...COMMUNITY_QUESTIONS);
    return questions;
}

/* ──────────────────────────────────────────────────────────
   Styles
   ────────────────────────────────────────────────────────── */
const styles = {
    bubble: {
        position: 'fixed', bottom: '24px', right: '24px',
        width: '60px', height: '60px', borderRadius: '50%',
        background: 'linear-gradient(135deg, #6c5ce7, #a855f7)',
        border: 'none', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '1.6rem', zIndex: 1000,
        boxShadow: '0 4px 24px rgba(108, 92, 231, 0.5)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
    },
    panel: {
        position: 'fixed', bottom: '96px', right: '24px',
        width: '400px', maxHeight: '600px', borderRadius: '16px',
        background: 'var(--bg-card, #1a1a2e)',
        backdropFilter: 'blur(20px)',
        border: '1px solid var(--border-color, #2a2a4a)',
        boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
        display: 'flex', flexDirection: 'column',
        zIndex: 999, overflow: 'hidden',
    },
    header: {
        padding: '16px 20px',
        borderBottom: '1px solid var(--border-color, #2a2a4a)',
        display: 'flex', alignItems: 'center', gap: '12px',
        background: 'var(--bg-secondary, #16162a)',
    },
    messagesArea: {
        flex: 1, overflowY: 'auto', padding: '16px',
        display: 'flex', flexDirection: 'column', gap: '12px',
        maxHeight: '360px',
    },
    userBubble: {
        maxWidth: '85%', padding: '10px 14px',
        borderRadius: '16px 16px 4px 16px',
        background: 'linear-gradient(135deg, #6c5ce7, #a855f7)',
        color: '#fff', fontSize: '0.875rem', lineHeight: '1.5',
    },
    aiBubble: {
        maxWidth: '90%', padding: '12px 16px',
        borderRadius: '16px 16px 16px 4px',
        background: 'var(--bg-secondary, #16162a)',
        color: 'var(--text-primary, #e0e0ff)',
        fontSize: '0.875rem', lineHeight: '1.7',
        position: 'relative',
    },
    copyBtn: {
        position: 'absolute', top: '6px', right: '6px',
        background: 'transparent', border: 'none',
        cursor: 'pointer', fontSize: '0.8rem',
        color: 'var(--text-muted, #888)',
        opacity: 0, transition: 'opacity 0.2s',
        padding: '4px 6px', borderRadius: '4px',
    },
    chipContainer: {
        display: 'flex', flexWrap: 'wrap', gap: '6px',
        marginTop: '6px',
    },
    chip: {
        padding: '6px 12px',
        background: 'rgba(108, 92, 231, 0.12)',
        border: '1px solid rgba(108, 92, 231, 0.3)',
        borderRadius: '20px',
        color: 'var(--accent, #a855f7)',
        fontSize: '0.75rem', cursor: 'pointer',
        transition: 'all 0.15s',
    },
    inputArea: {
        padding: '12px 16px',
        borderTop: '1px solid var(--border-color, #2a2a4a)',
        display: 'flex', gap: '8px', alignItems: 'flex-end',
        background: 'var(--bg-card, #1a1a2e)',
    },
    textarea: {
        flex: 1, background: 'transparent',
        border: '1px solid var(--border-color, #2a2a4a)',
        borderRadius: '10px', color: 'var(--text-primary, #e0e0ff)',
        padding: '10px 12px', fontSize: '0.875rem', resize: 'none',
        outline: 'none', fontFamily: 'inherit', lineHeight: '1.4',
        maxHeight: '80px', overflowY: 'auto',
    },
    sendBtn: (active) => ({
        width: '38px', height: '38px',
        borderRadius: '10px',
        background: active ? 'linear-gradient(135deg, #6c5ce7, #a855f7)' : 'var(--bg-secondary, #16162a)',
        border: 'none',
        cursor: active ? 'pointer' : 'not-allowed',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: active ? '#fff' : 'var(--text-muted, #888)',
        fontSize: '1rem', transition: 'background 0.2s', flexShrink: 0,
    }),
    errorMsg: {
        padding: '10px 14px', borderRadius: '10px',
        background: 'rgba(255, 71, 87, 0.12)',
        border: '1px solid rgba(255, 71, 87, 0.3)',
        color: '#ff4757', fontSize: '0.85rem',
        display: 'flex', alignItems: 'center', gap: '8px',
    },
    suggestionBtn: {
        textAlign: 'left', padding: '8px 12px',
        background: 'transparent',
        border: '1px solid var(--border-color, #2a2a4a)',
        borderRadius: '8px',
        color: 'var(--text-secondary, #aaa)',
        fontSize: '0.8rem', cursor: 'pointer',
        transition: 'background 0.15s, border-color 0.15s',
    },
};

/* ──────────────────────────────────────────────────────────
   Component
   ────────────────────────────────────────────────────────── */
export default function ChatBot({ competitorId, competitorName, analysisData, reviewData = [], adData = [], communityIntelData = [] }) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);
    const abortRef = useRef(null);

    const welcomeMessage = {
        role: 'assistant',
        content: `👋 I'm **StrategosAI** — your Competitive Intelligence Analyst.\n\nI have a full dossier on **${competitorName || 'your competitor'}**. Ask me about:\n- 🎯 Their pricing weaknesses & how to exploit them\n- ⚔️ Where we win vs. where they win\n- 📧 Draft a cold outreach email in seconds\n\nPick a question below or ask your own.`,
        followUps: [],
    };

    // ── Load from localStorage on mount / competitor change ──
    useEffect(() => {
        if (!competitorId) return;
        const saved = localStorage.getItem(LS_KEY(competitorId));
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    setMessages(parsed);
                    return;
                }
            } catch { /* ignore */ }
        }
        setMessages([welcomeMessage]);
    }, [competitorId, competitorName]);

    // ── Save to localStorage on message change ──
    useEffect(() => {
        if (!competitorId || messages.length === 0) return;
        localStorage.setItem(LS_KEY(competitorId), JSON.stringify(messages));
    }, [messages, competitorId]);

    // ── Auto-scroll & focus ──
    useEffect(() => {
        if (isOpen) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
            inputRef.current?.focus();
        }
    }, [messages, isOpen]);

    // ── Build context ──
    const buildContext = useCallback(() => ({
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
    }), [analysisData, competitorName, reviewData, adData, communityIntelData]);

    // ── Send message (streaming) ──
    const sendMessage = useCallback(async (text) => {
        const messageText = (text || inputValue || '').trim();
        if (!messageText || isLoading || !competitorId) return;

        setError(null);
        const userMessage = { role: 'user', content: messageText, followUps: [] };
        const placeholderAssistant = { role: 'assistant', content: '', followUps: [] };

        setMessages(prev => [...prev, userMessage, placeholderAssistant]);
        setInputValue('');
        setIsLoading(true);

        const historyToSend = messages
            .filter((_, i) => i > 0)  // skip welcome
            .map(m => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content }));

        const context = buildContext();
        let fullText = '';

        const abort = streamChatMessage(
            competitorId, context, historyToSend, messageText,
            // onToken
            (token) => {
                fullText += token;
                setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { ...updated[updated.length - 1], content: fullText };
                    return updated;
                });
            },
            // onDone
            () => {
                const { cleanText, followUps } = parseFollowUps(fullText);
                setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = { role: 'assistant', content: cleanText, followUps };
                    return updated;
                });
                setIsLoading(false);
            },
            // onError — fall back to non-streaming
            async (err) => {
                console.error('Stream error, falling back:', err);
                try {
                    const result = await sendChatMessage(competitorId, context, historyToSend, messageText);
                    const { cleanText, followUps } = parseFollowUps(result.reply);
                    setMessages(prev => {
                        const updated = [...prev];
                        updated[updated.length - 1] = { role: 'assistant', content: cleanText, followUps };
                        return updated;
                    });
                } catch (fallbackErr) {
                    console.error('Fallback also failed:', fallbackErr);
                    setError(`The analyst is unavailable. ${fallbackErr.message || 'Please try again.'}`);
                    setMessages(prev => prev.slice(0, -1)); // remove empty assistant placeholder
                }
                setIsLoading(false);
            }
        );
        abortRef.current = abort;
    }, [inputValue, isLoading, competitorId, messages, buildContext]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text).catch(() => {});
    };

    const smartQuestions = getSmartQuestions(analysisData, reviewData, adData, communityIntelData);
    const isWelcomeState = messages.length <= 1;

    return (
        <>
            {/* ── Floating Chat Bubble ── */}
            <button
                id="chatbot-toggle"
                onClick={() => setIsOpen(!isOpen)}
                style={styles.bubble}
                onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.1)'; e.currentTarget.style.boxShadow = '0 6px 30px rgba(108, 92, 231, 0.7)'; }}
                onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = '0 4px 24px rgba(108, 92, 231, 0.5)'; }}
                title="Ask StrategosAI"
            >
                {isOpen ? '✕' : '🧠'}
            </button>

            {/* ── Chat Panel ── */}
            {isOpen && (
                <div style={styles.panel}>
                    {/* Header */}
                    <div style={styles.header}>
                        <span style={{ fontSize: '1.3rem' }}>🧠</span>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: '700', fontSize: '0.95rem', color: 'var(--text-primary, #e0e0ff)' }}>
                                StrategosAI Analyst
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--accent, #a855f7)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00d26a', display: 'inline-block', animation: 'pulse 2s infinite' }} />
                                {competitorName ? `Briefed on ${competitorName}` : 'Online'}
                            </div>
                        </div>
                        {messages.length > 1 && (
                            <button
                                onClick={() => { setMessages([welcomeMessage]); localStorage.removeItem(LS_KEY(competitorId)); }}
                                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted, #888)', cursor: 'pointer', fontSize: '0.75rem', padding: '4px 8px', borderRadius: '6px' }}
                                title="Clear chat"
                            >
                                🗑️
                            </button>
                        )}
                    </div>

                    {/* Messages */}
                    <div style={styles.messagesArea}>
                        {messages.map((msg, i) => (
                            <div key={i}>
                                <div style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                                    <div
                                        style={msg.role === 'user' ? styles.userBubble : styles.aiBubble}
                                        onMouseEnter={e => { const btn = e.currentTarget.querySelector('.copy-btn'); if (btn) btn.style.opacity = '1'; }}
                                        onMouseLeave={e => { const btn = e.currentTarget.querySelector('.copy-btn'); if (btn) btn.style.opacity = '0'; }}
                                    >
                                        {msg.role === 'assistant' ? (
                                            <>
                                                <button
                                                    className="copy-btn"
                                                    style={styles.copyBtn}
                                                    onClick={() => copyToClipboard(msg.content)}
                                                    title="Copy to clipboard"
                                                >
                                                    📋
                                                </button>
                                                <div className="markdown-content">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                        {msg.content || (isLoading && i === messages.length - 1 ? '' : '')}
                                                    </ReactMarkdown>
                                                </div>
                                            </>
                                        ) : (
                                            msg.content
                                        )}
                                    </div>
                                </div>

                                {/* Follow-up chips under assistant messages */}
                                {msg.role === 'assistant' && msg.followUps?.length > 0 && !isLoading && (
                                    <div style={{ ...styles.chipContainer, paddingLeft: '4px', marginTop: '8px' }}>
                                        {msg.followUps.map((q, j) => (
                                            <button
                                                key={j}
                                                onClick={() => sendMessage(q)}
                                                style={styles.chip}
                                                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(108, 92, 231, 0.25)'; e.currentTarget.style.borderColor = 'var(--accent, #a855f7)'; }}
                                                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(108, 92, 231, 0.12)'; e.currentTarget.style.borderColor = 'rgba(108, 92, 231, 0.3)'; }}
                                            >
                                                {q}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}

                        {/* Typing indicator */}
                        {isLoading && messages[messages.length - 1]?.content === '' && (
                            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                                <div style={{
                                    padding: '12px 16px', borderRadius: '16px 16px 16px 4px',
                                    background: 'var(--bg-secondary, #16162a)',
                                    display: 'flex', gap: '6px', alignItems: 'center',
                                }}>
                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted, #888)', marginRight: '4px' }}>Analyst is thinking</span>
                                    {[0, 1, 2].map(i => (
                                        <span key={i} style={{
                                            width: '6px', height: '6px', borderRadius: '50%',
                                            background: 'var(--accent, #a855f7)',
                                            animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                                            display: 'inline-block',
                                        }} />
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Error message */}
                        {error && (
                            <div style={styles.errorMsg}>
                                <span>⚠️</span>
                                <span style={{ flex: 1 }}>{error}</span>
                                <button
                                    onClick={() => setError(null)}
                                    style={{ background: 'transparent', border: 'none', color: '#ff4757', cursor: 'pointer', fontSize: '0.8rem' }}
                                >
                                    ✕
                                </button>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Suggested questions (welcome state) */}
                    {isWelcomeState && (
                        <div style={{
                            padding: '0 16px 10px',
                            display: 'flex', flexDirection: 'column', gap: '5px',
                            maxHeight: '150px', overflowY: 'auto',
                        }}>
                            {smartQuestions.slice(0, 6).map((q, i) => (
                                <button
                                    key={i}
                                    onClick={() => sendMessage(q)}
                                    style={styles.suggestionBtn}
                                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-secondary, #16162a)'; e.currentTarget.style.borderColor = 'var(--accent, #a855f7)'; }}
                                    onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'var(--border-color, #2a2a4a)'; }}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Input */}
                    <div style={styles.inputArea}>
                        <textarea
                            ref={inputRef}
                            rows={1}
                            placeholder={competitorId ? "Ask anything about this competitor..." : "Open a competitor first to start chatting"}
                            value={inputValue}
                            onChange={e => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            disabled={isLoading || !competitorId}
                            style={styles.textarea}
                        />
                        <button
                            id="chatbot-send"
                            onClick={() => sendMessage()}
                            disabled={isLoading || !inputValue.trim() || !competitorId}
                            style={styles.sendBtn(!isLoading && inputValue.trim() && competitorId)}
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
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.4; }
                }
                .markdown-content h1, .markdown-content h2, .markdown-content h3 {
                    margin: 8px 0 4px; font-size: 0.95rem; color: var(--accent, #a855f7);
                }
                .markdown-content p { margin: 4px 0; }
                .markdown-content ul, .markdown-content ol { margin: 4px 0; padding-left: 20px; }
                .markdown-content li { margin: 2px 0; }
                .markdown-content strong { color: var(--accent, #a855f7); }
                .markdown-content code {
                    background: rgba(108, 92, 231, 0.12); padding: 2px 6px;
                    border-radius: 4px; font-size: 0.82rem;
                }
                .markdown-content pre {
                    background: rgba(0,0,0,0.3); padding: 10px;
                    border-radius: 8px; overflow-x: auto; margin: 6px 0;
                }
                .markdown-content table {
                    border-collapse: collapse; width: 100%; margin: 6px 0;
                    font-size: 0.82rem;
                }
                .markdown-content th, .markdown-content td {
                    border: 1px solid var(--border-color, #2a2a4a);
                    padding: 4px 8px; text-align: left;
                }
                .markdown-content th {
                    background: rgba(108, 92, 231, 0.15);
                    color: var(--accent, #a855f7);
                }
            `}</style>
        </>
    );
}
