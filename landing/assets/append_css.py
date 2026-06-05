import os

css = """

/* ══════════════════════════════════════
   NIGHT-SKY DESIGN SYSTEM
   Appended — all original classes preserved
══════════════════════════════════════ */
:root {
  --night-900: #020817;
  --night-800: #071225;
  --night-700: #0b1f3a;
  --indigo-glow: #4f46e5;
  --blue-glow: #38bdf8;
  --violet-glow: #8b5cf6;
  --text-main: #f8fafc;
  --text-muted-night: #a8b3cf;
  --border-soft: rgba(255,255,255,0.08);
  --card-glass: rgba(8,18,37,0.72);
}

body {
  background: var(--night-900);
  background-image:
    radial-gradient(ellipse 120% 60% at 50% -5%, rgba(79,70,229,0.18) 0%, transparent 55%),
    radial-gradient(ellipse 80% 40% at 80% 10%, rgba(56,189,248,0.07) 0%, transparent 45%);
}

.nav { background: rgba(2,8,23,0.92); border-bottom: 1px solid rgba(56,189,248,0.08); }
.nav-brand::before { background: #38bdf8; box-shadow: 0 0 12px rgba(56,189,248,0.8); }

/* ── HERO ── */
.hero-night {
  position: relative;
  min-height: 88vh;
  display: flex;
  align-items: center;
  overflow: hidden;
}
.hero-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.hero-bg__base {
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 100% 70% at 50% 0%, #0d2252 0%, #071225 40%, #020817 75%);
}
.hero-bg__nebula {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 50% 45% at 70% 30%, rgba(79,70,229,0.12) 0%, transparent 60%),
    radial-gradient(ellipse 35% 30% at 20% 60%, rgba(56,189,248,0.06) 0%, transparent 55%),
    radial-gradient(ellipse 40% 35% at 85% 70%, rgba(139,92,246,0.07) 0%, transparent 55%);
}
.hero-bg__stars {
  position: absolute; top: 0; left: 0;
  width: 100%; height: 65%; object-fit: cover; opacity: 0.85;
}
.hero-bg__moon {
  position: absolute; top: 48px; right: 12%; z-index: 2;
  filter: drop-shadow(0 0 18px rgba(191,219,254,0.25));
}
.hero-bg__hills {
  position: absolute; bottom: 0; left: 0;
  width: 100%; height: 55%; object-fit: cover; object-position: bottom;
}
.hero-night::after {
  content: '';
  position: absolute; bottom: 0; left: 0; right: 0; height: 140px;
  background: linear-gradient(to bottom, transparent, #020817);
  z-index: 3; pointer-events: none;
}
.hero-content {
  position: relative; z-index: 10;
  max-width: 1100px; margin: 0 auto;
  padding: 100px 32px 120px; width: 100%;
  display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: center;
}
.hero-text { display: flex; flex-direction: column; }
.hero-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase;
  color: #38bdf8; margin-bottom: 22px;
}
.eyebrow-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: #38bdf8; box-shadow: 0 0 8px rgba(56,189,248,0.9);
  flex-shrink: 0; animation: pulseGlow 2.4s ease-in-out infinite;
}
@keyframes pulseGlow {
  0%,100% { opacity: 1; box-shadow: 0 0 8px rgba(56,189,248,0.9); }
  50%      { opacity: 0.6; box-shadow: 0 0 4px rgba(56,189,248,0.4); }
}
.hero-headline {
  font-size: clamp(2rem, 4.5vw, 3.2rem);
  font-weight: 800; color: #f0f6fc; line-height: 1.1;
  letter-spacing: -0.04em; margin-bottom: 20px;
  text-shadow: 0 2px 40px rgba(56,189,248,0.12);
}
.hero-sub {
  font-size: 1rem; color: #a8b3cf; line-height: 1.75;
  max-width: 480px; margin-bottom: 32px;
}
.hero-ctas { display: flex; gap: 12px; margin-bottom: 28px; flex-wrap: wrap; }
.btn-hero-primary {
  display: inline-flex; align-items: center;
  background: linear-gradient(135deg, #4f46e5, #38bdf8);
  color: #fff; text-decoration: none;
  font-size: 0.9rem; font-weight: 600; letter-spacing: -0.01em;
  padding: 13px 26px; border-radius: 8px;
  box-shadow: 0 4px 24px rgba(79,70,229,0.35);
  transition: opacity 0.15s, transform 0.12s;
}
.btn-hero-primary:hover { opacity: 0.9; transform: translateY(-2px); }
.btn-hero-secondary {
  display: inline-flex; align-items: center;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14);
  color: #c7d2fe; text-decoration: none;
  font-size: 0.9rem; font-weight: 500; letter-spacing: -0.01em;
  padding: 13px 26px; border-radius: 8px; backdrop-filter: blur(8px);
  transition: background 0.15s, border-color 0.15s, transform 0.12s;
}
.btn-hero-secondary:hover { background: rgba(255,255,255,0.1); border-color: rgba(56,189,248,0.3); transform: translateY(-2px); }
.hero-signal-tags { display: flex; flex-wrap: wrap; gap: 7px; }
.signal-tag {
  font-size: 0.68rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
  padding: 4px 10px; border-radius: 999px; border: 1px solid; opacity: 0.85;
}
.signal-tag--markets { color: #60a5fa; border-color: rgba(96,165,250,0.3); background: rgba(59,130,246,0.08); }
.signal-tag--ai      { color: #c084fc; border-color: rgba(192,132,252,0.3); background: rgba(168,85,247,0.08); }
.signal-tag--hr      { color: #34d399; border-color: rgba(52,211,153,0.3); background: rgba(16,185,129,0.08); }
.signal-tag--econ    { color: #fb923c; border-color: rgba(251,146,60,0.3); background: rgba(249,115,22,0.08); }
.signal-tag--major   { color: #f87171; border-color: rgba(248,113,113,0.3); background: rgba(239,68,68,0.08); }
.hero-illustration {
  position: relative; display: flex; align-items: flex-end;
  justify-content: center; min-height: 380px;
}
.hero-constellation {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%;
  object-fit: contain; opacity: 0.65;
}
.hero-scout {
  position: relative; z-index: 2;
  width: min(340px, 90%); height: auto;
  filter: drop-shadow(0 8px 32px rgba(56,189,248,0.18));
}

/* ── SUBSCRIBE ── */
.subscribe-night { padding: 80px 24px 96px; text-align: center; position: relative; }
.subscribe-night::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse 60% 80% at 50% 50%, rgba(79,70,229,0.07), transparent 70%);
  pointer-events: none;
}
.subscribe-night-inner { position: relative; max-width: 540px; margin: 0 auto; }
.subscribe-eyebrow {
  font-size: 0.68rem; font-weight: 700; color: #38bdf8;
  text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 14px;
}
.subscribe-title {
  font-size: 1.65rem; font-weight: 800; color: #f0f6fc;
  letter-spacing: -0.03em; margin-bottom: 10px; line-height: 1.2;
}
.subscribe-sub { font-size: 0.875rem; color: #a8b3cf; line-height: 1.7; margin-bottom: 8px; }
.subscribe-reader-count { font-size: 0.78rem; color: rgba(168,179,207,0.6); margin-bottom: 24px; }
.subscribe-privacy { font-size: 0.75rem; color: rgba(168,179,207,0.45); margin-top: 14px; }

/* ── FOOTER ── */
.footer-night { border-top: 1px solid rgba(255,255,255,0.06); padding: 24px 32px 32px; }
.footer-night-inner {
  max-width: 1100px; margin: 0 auto;
  display: flex; align-items: center; flex-wrap: wrap; gap: 8px;
  font-size: 0.78rem; color: rgba(168,179,207,0.5);
}
.footer-brand-dot { width: 5px; height: 5px; border-radius: 50%; background: #38bdf8; opacity: 0.5; display: inline-block; }
.footer-brand-name { font-weight: 700; color: rgba(168,179,207,0.7); }
.footer-sep { opacity: 0.35; }
.footer-night a { color: rgba(168,179,207,0.5); text-decoration: none; transition: color 0.15s; }
.footer-night a:hover { color: #c7d2fe; }
.footer-copy { opacity: 0.5; }

/* ── GLASS CARDS ── */
.kpi-card { background: rgba(11,31,58,0.6); border-color: rgba(255,255,255,0.08); backdrop-filter: blur(12px); }
.section-card { background: rgba(8,18,37,0.72); border-color: rgba(255,255,255,0.07); backdrop-filter: blur(8px); }
.sc-card { background: rgba(11,31,58,0.55); border-color: rgba(255,255,255,0.07); backdrop-filter: blur(8px); }
.sc-card:hover { background: rgba(11,31,58,0.82); }
.sc-card--active { background: color-mix(in srgb, var(--sc-color,#4f46e5) 10%, rgba(8,18,37,0.85)); box-shadow: 0 0 0 1px var(--sc-color,#4f46e5), 0 4px 24px rgba(0,0,0,0.5); }
.story-item:hover { background: rgba(56,189,248,0.03); }
.source-pill:hover, .story-source:hover { border-color: rgba(56,189,248,0.3); color: #38bdf8; }

/* ── RESPONSIVE ── */
@media (max-width: 900px) {
  .hero-content { grid-template-columns: 1fr; padding: 80px 24px 100px; }
  .hero-illustration { display: none; }
  .hero-night { min-height: auto; }
  .hero-bg__moon { right: 5%; top: 28px; }
}
@media (max-width: 520px) {
  .hero-headline { font-size: 1.85rem; }
  .hero-sub { font-size: 0.9rem; }
  .hero-ctas { flex-direction: column; }
  .btn-hero-primary, .btn-hero-secondary { width: 100%; justify-content: center; }
  .hero-content { padding: 64px 16px 88px; }
  .hero-bg__moon { display: none; }
  .subscribe-night { padding: 56px 16px 72px; }
}
"""

target = r"C:\Users\hp\OneDrive\Desktop\Claude code\Newsletter People OS\landing\style.css"
with open(target, "a", encoding="utf-8") as f:
    f.write(css)
print("Done")
