import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeCompany } from '../utils/api';
import './Landing.css';

export default function Landing({ onComplete }) {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const heroCanvasRef = useRef(null);
    const ctaCanvasRef = useRef(null);

    const handleSubmit = async (e) => {
        if (e) e.preventDefault();
        if (!url.trim()) return;

        setLoading(true);
        setError('');

        try {
            const company = await analyzeCompany(url.trim());
            // Update app state and navigate to Onboard (App UI)
            if (onComplete) onComplete(company);
            navigate('/app');
        } catch (err) {
            setError(err.message || 'Failed to analyze company');
            setLoading(false);
        }
    };

    // UseEffect for Cursor, Animations, and Observers
    useEffect(() => {
        // --- CURSOR ---
        const cursor = document.getElementById('cursor');
        const ring = document.getElementById('cursor-ring');
        let mx = window.innerWidth / 2, my = window.innerHeight / 2, rx = mx, ry = my;
        
        const handleMouseMove = e => {
            mx = e.clientX;
            my = e.clientY;
            if (cursor) {
                cursor.style.left = mx + 'px';
                cursor.style.top = my + 'px';
            }
        };
        document.addEventListener('mousemove', handleMouseMove);
        
        let cursorAnimFrame;
        const animRing = () => {
            rx += (mx - rx) * 0.13;
            ry += (my - ry) * 0.13;
            if (ring) {
                ring.style.left = rx + 'px';
                ring.style.top = ry + 'px';
            }
            cursorAnimFrame = requestAnimationFrame(animRing);
        };
        animRing();

        // --- HERO PARTICLES ---
        const hc = heroCanvasRef.current;
        let pAnimFrame;
        if (hc) {
            const hx = hc.getContext('2d');
            const resizeHC = () => { hc.width = hc.offsetWidth; hc.height = hc.offsetHeight; };
            resizeHC();
            window.addEventListener('resize', resizeHC);

            class P {
                constructor() { this.reset(); }
                reset() {
                    this.x = Math.random() * hc.width;
                    this.y = Math.random() * hc.height;
                    this.r = Math.random() * 1.4 + 0.4;
                    this.vx = (Math.random() - 0.5) * 0.28;
                    this.vy = (Math.random() - 0.5) * 0.28;
                    this.a = Math.random() * 0.3 + 0.05;
                    this.c = Math.random() > 0.55 ? '196,101,58' : '26,24,20';
                }
                update() {
                    this.x += this.vx; this.y += this.vy;
                    if (this.x < 0 || this.x > hc.width || this.y < 0 || this.y > hc.height) this.reset();
                }
                draw() {
                    hx.beginPath(); hx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
                    hx.fillStyle = `rgba(${this.c},${this.a})`; hx.fill();
                }
            }
            const particles = Array.from({ length: 90 }, () => new P());
            const loopParticles = () => {
                hx.clearRect(0, 0, hc.width, hc.height);
                for (let i = 0; i < particles.length; i++) {
                    for (let j = i + 1; j < particles.length; j++) {
                        const dx = particles[i].x - particles[j].x, dy = particles[i].y - particles[j].y, d = Math.sqrt(dx * dx + dy * dy);
                        if (d < 110) { hx.beginPath(); hx.moveTo(particles[i].x, particles[i].y); hx.lineTo(particles[j].x, particles[j].y); hx.strokeStyle = `rgba(196,101,58,${0.055 * (1 - d / 110)})`; hx.lineWidth = 0.5; hx.stroke(); }
                    }
                    particles[i].update(); particles[i].draw();
                }
                pAnimFrame = requestAnimationFrame(loopParticles);
            };
            loopParticles();
            
            // Cleanup particle resize
            const oldCleanup = () => window.removeEventListener('resize', resizeHC);
            hc._cleanup = oldCleanup;
        }

        // --- CTA STARS ---
        const cc = ctaCanvasRef.current;
        let ccAnimFrame;
        if (cc) {
            const cx = cc.getContext('2d');
            const resizeCC = () => { cc.width = cc.offsetWidth; cc.height = cc.offsetHeight; };
            resizeCC();
            window.addEventListener('resize', resizeCC);
            const stars = Array.from({ length: 70 }, () => ({ x: Math.random(), y: Math.random(), r: Math.random() * 1.1 + 0.2, a: Math.random() * 0.4, va: (Math.random() - 0.5) * 0.008 }));
            const starLoop = () => {
                cx.clearRect(0, 0, cc.width, cc.height);
                stars.forEach(s => {
                    s.a = Math.max(0.01, Math.min(0.45, s.a + s.va));
                    if (s.a <= 0.01 || s.a >= 0.45) s.va *= -1;
                    cx.beginPath(); cx.arc(s.x * cc.width, s.y * cc.height, s.r, 0, Math.PI * 2);
                    cx.fillStyle = `rgba(255,255,255,${s.a})`; cx.fill();
                });
                ccAnimFrame = requestAnimationFrame(starLoop);
            };
            starLoop();
            
            // Cleanup star resize
            cc._cleanup = () => window.removeEventListener('resize', resizeCC);
        }

        // --- OBSERVERS ---
        const allReveals = document.querySelectorAll('.reveal,.reveal-left,.reveal-right');
        const io = new IntersectionObserver(entries => { entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } }); }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
        allReveals.forEach(el => io.observe(el));

        const dnaCard = document.getElementById('dna-card');
        const dnaRows = document.querySelectorAll('.dna-row');
        if (dnaCard) {
            const dnaObs = new IntersectionObserver(entries => { if (entries[0].isIntersecting) { dnaRows.forEach((r, i) => setTimeout(() => r.classList.add('animate'), i * 130)); dnaObs.disconnect(); } }, { threshold: 0.3 });
            dnaObs.observe(dnaCard);
        }

        const compCard = document.getElementById('comp-card');
        const bars = document.querySelectorAll('.comp-bar');
        if (compCard) {
            const compObs = new IntersectionObserver(entries => { if (entries[0].isIntersecting) { bars.forEach((b, i) => setTimeout(() => { b.style.width = b.dataset.w + '%'; }, i * 130)); compObs.disconnect(); } }, { threshold: 0.3 });
            compObs.observe(compCard);
        }

        const scoutCard = document.getElementById('scout-card');
        const nodes = document.querySelectorAll('.s-node');
        if (scoutCard) {
            const scoutObs = new IntersectionObserver(entries => { if (entries[0].isIntersecting) { nodes.forEach((n, i) => setTimeout(() => n.classList.add('animate'), 200 + i * 140)); scoutObs.disconnect(); } }, { threshold: 0.3 });
            scoutObs.observe(scoutCard);
        }

        document.querySelectorAll('.counter').forEach(el => {
            const cntObs = new IntersectionObserver(entries => {
                if (entries[0].isIntersecting) {
                    const target = +el.dataset.target, dur = 1800, start = performance.now();
                    const tick = (now) => { const t = Math.min((now - start) / dur, 1), ease = 1 - Math.pow(1 - t, 3); el.textContent = Math.floor(ease * target); if (t < 1) requestAnimationFrame(tick); else el.textContent = target; };
                    requestAnimationFrame(tick);
                    cntObs.disconnect();
                }
            }, { threshold: 0.5 });
            cntObs.observe(el);
        });

        // BENTO GLOW
        const handleBentoHover = e => {
            const card = e.currentTarget;
            const r = card.getBoundingClientRect();
            card.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
            card.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
        };
        const bentoCards = document.querySelectorAll('.bento-card');
        bentoCards.forEach(c => c.addEventListener('mousemove', handleBentoHover));

        // CLEANUP
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            cancelAnimationFrame(cursorAnimFrame);
            if (pAnimFrame) cancelAnimationFrame(pAnimFrame);
            if (ccAnimFrame) cancelAnimationFrame(ccAnimFrame);
            if (hc && hc._cleanup) hc._cleanup();
            if (cc && cc._cleanup) cc._cleanup();
            bentoCards.forEach(c => c.removeEventListener('mousemove', handleBentoHover));
            io.disconnect();
        };
    }, []);

    return (
        <div className="landing-page">
            <div id="cursor"></div>
            <div id="cursor-ring"></div>
            <div className="landing-grain"></div>

            <nav>
                <a href="#" onClick={(e) => e.preventDefault()} className="nav-logo">
                    <div className="logo-mark">S</div>
                    <span className="logo-name">StrategosAI</span>
                </a>
                <ul className="nav-links">
                    <li><a href="#" onClick={(e) => e.preventDefault()}>Onboard</a></li>
                    <li><a href="#" onClick={(e) => e.preventDefault()}>Scout</a></li>
                    <li><a href="#" onClick={(e) => e.preventDefault()}>Analyze</a></li>
                    <li><a href="#" onClick={(e) => e.preventDefault()}>Dashboard</a></li>
                </ul>
                <div className="nav-cta">
                    <button onClick={() => navigate('/app')} className="btn-ghost" style={{ cursor: 'none' }}>Sign in</button>
                    <button onClick={() => navigate('/app')} className="btn-primary" style={{ cursor: 'none' }}>Get started →</button>
                </div>
            </nav>

            <section className="hero">
                <canvas id="hero-canvas" ref={heroCanvasRef}></canvas>
                <div className="hero-orb orb-1"></div>
                <div className="hero-orb orb-2"></div>
                <div className="hero-orb orb-3"></div>
                <div className="hero-grid"></div>

                <div className="hero-float-cards">
                    <div className="float-card fc-1"><span className="fc-icon">🧬</span><div><div className="fc-label">DNA Extracted</div><div className="fc-sub">acme.com · 2s ago</div></div></div>
                    <div className="float-card fc-2"><span className="fc-icon">🔭</span><div><div className="fc-label">12 competitors found</div><div className="fc-sub">Scout complete</div></div></div>
                    <div className="float-card fc-3"><span className="fc-icon">⚡</span><div><div className="fc-label">3 pricing gaps</div><div className="fc-sub">Advantage identified</div></div></div>
                    <div className="float-card fc-4"><span className="fc-icon">📊</span><div><div className="fc-label">Dashboard live</div><div className="fc-sub">Updated 5m ago</div></div></div>
                </div>

                <div className="eyebrow"><div className="eyebrow-dot"></div>Competitive Intelligence, Automated</div>
                <h1 className="hero-title">Know your competitors<br />before they <em>know you</em></h1>
                <p className="hero-sub">Enter your URL. StrategosAI extracts your company DNA — features, pricing, positioning — then scouts the competitive landscape automatically.</p>
                
                <form className="hero-input-row" onSubmit={handleSubmit}>
                    <input 
                        type="url" 
                        placeholder="https://yourcompany.com" 
                        id="hero-input"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        disabled={loading}
                        required
                    />
                    <button 
                        type="submit" 
                        className="btn-extract" 
                        id="extract-btn"
                        disabled={loading}
                        style={{ background: loading ? '#B8942E' : '' }}
                    >
                        {loading ? '⏳ Analyzing...' : '⚡ Extract DNA'}
                    </button>
                </form>
                {error && <p style={{ color: 'var(--accent)', marginTop: '10px', fontSize: '14px', zIndex: 10, position: 'relative' }}>{error}</p>}
                <p className="hero-meta">Free to try · No credit card · Results in <span>~30 seconds</span></p>
            </section>

            <div className="logos-strip">
                <div className="logos-label">Trusted by growth teams at</div>
                <div style={{ overflow: 'hidden' }}>
                    <div className="logos-marquee">
                        <div className="logo-item">Vercel</div><div className="logo-item">Linear</div><div className="logo-item">Retool</div><div className="logo-item">Loom</div><div className="logo-item">Figma</div><div className="logo-item">Notion</div><div className="logo-item">Pitch</div><div className="logo-item">Raycast</div>
                        <div className="logo-item">Vercel</div><div className="logo-item">Linear</div><div className="logo-item">Retool</div><div className="logo-item">Loom</div><div className="logo-item">Figma</div><div className="logo-item">Notion</div><div className="logo-item">Pitch</div><div className="logo-item">Raycast</div>
                    </div>
                </div>
            </div>

            <section className="section-wrap">
                <div className="steps-header">
                    <div className="reveal"><div className="section-tag">How it works</div><div className="section-title">Four steps from URL<br />to strategic clarity</div></div>
                    <p className="steps-desc reveal">StrategosAI turns a single URL into a full competitive map — automatically, in minutes.</p>
                </div>
                <div className="steps-grid">
                    <div className="step-card reveal" style={{ transitionDelay: '0ms' }}><div className="step-num">01</div><div className="step-icon">🧬</div><div className="step-title">Company DNA</div><p className="step-desc">Paste your URL. We extract features, pricing tiers, positioning, and ideal customer profile instantly.</p></div>
                    <div className="step-card reveal" style={{ transitionDelay: '100ms' }}><div className="step-num">02</div><div className="step-icon">🔭</div><div className="step-title">Scout</div><p className="step-desc">AI scans for direct and indirect competitors, surfacing companies you may not even know exist yet.</p></div>
                    <div className="step-card reveal" style={{ transitionDelay: '200ms' }}><div className="step-num">03</div><div className="step-icon">⚡</div><div className="step-title">Analyze</div><p className="step-desc">Side-by-side breakdowns of positioning gaps, pricing advantages, and messaging differentiators.</p></div>
                    <div className="step-card reveal" style={{ transitionDelay: '300ms' }}><div className="step-num">04</div><div className="step-icon">📊</div><div className="step-title">Dashboard</div><p className="step-desc">A living intelligence board that updates as competitors evolve — never be caught off guard again.</p></div>
                </div>
            </section>

            <section className="section-wrap" style={{ paddingTop: 0 }}>
                <div className="reveal" style={{ marginBottom: 56 }}><div className="section-tag">Features</div><div className="section-title">Built for teams<br />who move fastest</div></div>
                <div className="bento-grid">
                    <div className="bento-card span-col reveal-left" id="dna-card">
                        <div className="bento-tag">Company DNA</div>
                        <div className="bento-title">Extract your full market identity in one click</div>
                        <p className="bento-desc">StrategosAI reads your website like a senior strategist — pulling out what matters for competitive positioning.</p>
                        <div className="dna-visual">
                            <div className="dna-row"><span className="dna-label">CATEGORY</span><span className="dna-value">Project Management <span className="dna-pill">SaaS</span></span></div>
                            <div className="dna-row"><span className="dna-label">ICP</span><span className="dna-value">Mid-market engineering teams</span></div>
                            <div className="dna-row"><span className="dna-label">PRICING</span><span className="dna-value">Freemium → $12/seat/mo <span className="dna-pill">PLG</span></span></div>
                            <div className="dna-row"><span className="dna-label">KEY FEATURES</span><span className="dna-value">Kanban, Sprints, Roadmaps</span></div>
                            <div className="dna-row"><span className="dna-label">DIFFERENTIATOR</span><span className="dna-value">Speed-first UX <span className="dna-pill">Top</span></span></div>
                        </div>
                    </div>
                    <div className="bento-card reveal-right" id="scout-card">
                        <div className="bento-tag">Scout Mode</div>
                        <div className="bento-title">Find competitors you didn't know existed</div>
                        <p className="bento-desc">AI scans funding data and product signals to surface the full competitive field.</p>
                        <div className="scout-nodes">
                            <div className="s-center">🔭</div>
                            <div className="s-node" id="sn1" style={{ top: 8, left: 16 }}><span className="s-dot" style={{ background: '#C4653A' }}></span>Asana</div>
                            <div className="s-node" id="sn2" style={{ top: 8, right: 16 }}><span className="s-dot" style={{ background: '#B8942E' }}></span>Monday</div>
                            <div className="s-node" id="sn3" style={{ bottom: 8, left: 16 }}><span className="s-dot" style={{ background: '#6B8CBA' }}></span>ClickUp</div>
                            <div className="s-node" id="sn4" style={{ bottom: 8, right: 16 }}><span className="s-dot" style={{ background: '#7BAE8A' }}></span>Notion</div>
                            <div className="s-node" id="sn5" style={{ top: '50%', left: 0, transform: 'translateY(-50%)' }}><span className="s-dot" style={{ background: '#C4653A' }}></span>Linear</div>
                        </div>
                    </div>
                    <div className="bento-card dark reveal-right" id="comp-card">
                        <div className="bento-tag">Competitive Analysis</div>
                        <div className="bento-title">See exactly where you win</div>
                        <p className="bento-desc">Instant positioning gap analysis across pricing, features, and messaging.</p>
                        <div className="competitor-visual">
                            <div className="comp-row"><span className="comp-name">You</span><div className="comp-bar-bg"><div className="comp-bar" data-w="82" style={{ background: 'linear-gradient(90deg,#C4653A,#E8856A)' }}></div></div><span className="comp-score">82</span></div>
                            <div className="comp-row"><span className="comp-name">Asana</span><div className="comp-bar-bg"><div className="comp-bar" data-w="71" style={{ background: 'rgba(255,255,255,.3)' }}></div></div><span className="comp-score">71</span></div>
                            <div className="comp-row"><span className="comp-name">Monday</span><div className="comp-bar-bg"><div className="comp-bar" data-w="65" style={{ background: 'rgba(255,255,255,.2)' }}></div></div><span class="comp-score">65</span></div>
                            <div className="comp-row"><span className="comp-name">ClickUp</span><div className="comp-bar-bg"><div className="comp-bar" data-w="58" style={{ background: 'rgba(255,255,255,.15)' }}></div></div><span className="comp-score">58</span></div>
                            <div className="comp-row"><span className="comp-name">Linear</span><div className="comp-bar-bg"><div className="comp-bar" data-w="52" style={{ background: 'rgba(255,255,255,.12)' }}></div></div><span className="comp-score">52</span></div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="stats-bar reveal">
                <div className="stat-item"><div className="stat-num"><span className="counter" data-target="4200">0</span><span className="stat-accent">+</span></div><div className="stat-label">Companies analyzed</div></div>
                <div className="stat-item"><div className="stat-num"><span className="counter" data-target="28">0</span><span className="stat-accent">s</span></div><div className="stat-label">Average analysis time</div></div>
                <div className="stat-item"><div className="stat-num"><span className="counter" data-target="97">0</span><span className="stat-accent">%</span></div><div className="stat-label">Accuracy rate</div></div>
                <div className="stat-item"><div className="stat-num"><span className="counter" data-target="140">0</span><span className="stat-accent">+</span></div><div className="stat-label">Markets covered</div></div>
            </div>

            <section className="section-wrap" style={{ paddingTop: 0 }}>
                <div className="reveal"><div className="section-tag">What people say</div><div className="section-title">Teams who move fast<br />love StrategosAI</div></div>
                <div className="testimonials-grid">
                    <div className="testimonial reveal" style={{ transitionDelay: '0ms' }}><div className="testimonial-stars">★★★★★</div><p className="testimonial-text">"We ran a full competitive analysis in 20 minutes for a board meeting. Would have taken two analysts a week before StrategosAI."</p><div className="testimonial-author"><div className="author-avatar">JM</div><div><div className="author-name">Jordan Mack</div><div className="author-role">VP Product · Cascade</div></div></div></div>
                    <div className="testimonial reveal" style={{ transitionDelay: '120ms' }}><div className="testimonial-stars">★★★★★</div><p className="testimonial-text">"The DNA extraction is scarily accurate. It found positioning angles in our copy we hadn't even consciously decided on."</p><div className="testimonial-author"><div className="author-avatar">SR</div><div><div className="author-name">Sofia Ruiz</div><div className="author-role">Head of Strategy · Luma</div></div></div></div>
                    <div className="testimonial reveal" style={{ transitionDelay: '240ms' }}><div className="testimonial-stars">★★★★★</div><p className="testimonial-text">"Scout mode found three competitors we'd completely missed. One was undercutting us by 40% in a segment we thought we owned."</p><div className="testimonial-author"><div className="author-avatar">AK</div><div><div className="author-name">Arjun Kapoor</div><div className="author-role">CEO · Fieldwork</div></div></div></div>
                </div>
            </section>

            <div className="cta-wrap reveal">
                <canvas id="cta-canvas" ref={ctaCanvasRef}></canvas>
                <div className="cta-glow"></div>
                <h2>Start with your URL.<br />Get a <em>full playbook</em>.</h2>
                <p>No setup, no integrations required. Paste your website and see your competitive landscape in minutes.</p>
                <div className="cta-buttons">
                    <button className="btn-cta-primary" onClick={() => navigate('/app')}>⚡ Extract my DNA — Free</button>
                    <button className="btn-cta-ghost" onClick={() => navigate('/app')}>See a live demo</button>
                </div>
            </div>

            <footer>
                <a href="#" onClick={(e) => e.preventDefault()} className="footer-logo"><div className="logo-mark">S</div><span className="logo-name">StrategosAI</span></a>
                <ul className="footer-links"><li><a href="#" onClick={(e) => e.preventDefault()}>Product</a></li><li><a href="#" onClick={(e) => e.preventDefault()}>Pricing</a></li><li><a href="#" onClick={(e) => e.preventDefault()}>Blog</a></li><li><a href="#" onClick={(e) => e.preventDefault()}>Privacy</a></li><li><a href="#" onClick={(e) => e.preventDefault()}>Terms</a></li></ul>
                <span className="footer-copy">© 2025 StrategosAI</span>
            </footer>

            <div className="floating-badge"><div className="badge-dot"></div>Review mode active</div>
        </div>
    );
}
