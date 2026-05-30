/* PeopleOS Brief — Dashboard JS
   Loads /data/dates.json and /data/issues/YYYY-MM-DD.json.
   No API keys. No Groq/Tavily/Supabase calls for public visitors.
   Supports: ?date=YYYY-MM-DD  and  ?section=section_id
*/
(function () {
  'use strict';

  const SECTION_META = {
    india_stock_market:  { code:'S1',  name:'India Stock Market',  icon:'📈', desc:'Nifty, Sensex, sectors, FII flows, RBI moves.',         cat:'markets' },
    us_stock_market:     { code:'S2',  name:'US Stock Market',     icon:'🗽', desc:'S&P 500, Nasdaq, big tech, Fed, earnings.',              cat:'markets' },
    global_markets:      { code:'S3',  name:'Global Markets',      icon:'🌐', desc:'Europe, Asia, oil, currencies, bonds, EM.',              cat:'markets' },
    ai_news:             { code:'S4',  name:'AI News',             icon:'🤖', desc:'Model launches, enterprise AI, regulation, products.',   cat:'ai'      },
    ai_research_papers:  { code:'S5',  name:'AI Research Papers',  icon:'🔬', desc:'ArXiv papers, agents, benchmarks, safety, LLMs.',        cat:'ai'      },
    trending_topics:     { code:'S6',  name:'Trending Topics',     icon:'🔥', desc:'High-signal stories, tech, business, culture.',          cat:'trending'},
    hr_news_india:       { code:'S7',  name:'HR News India',       icon:'🇮🇳', desc:'Hiring, layoffs, compensation, labor market, policy.',   cat:'hr'      },
    global_hr_news:      { code:'S8',  name:'Global HR News',      icon:'🌍', desc:'Workforce, talent, employee experience, WFH.',           cat:'hr'      },
    hr_research_papers:  { code:'S9',  name:'HR Research Papers',  icon:'📚', desc:'People analytics, leadership, culture, org behavior.',   cat:'hr'      },
    macroeconomics:      { code:'S10', name:'Macroeconomics',      icon:'🏦', desc:'Inflation, rates, GDP, central banks, trade.',           cat:'econ'    },
    microeconomics:      { code:'S11', name:'Microeconomics',      icon:'🏭', desc:'Pricing, competition, firm behavior, market structure.', cat:'econ'    },
    major_updates:       { code:'S12', name:'Major Updates',       icon:'⚡', desc:'Breaking news and high-impact cross-domain updates.',    cat:'major'   },
  };

  const CAT_COLOR = {
    markets: '#3b82f6',
    ai:      '#8b5cf6',
    trending:'#f59e0b',
    hr:      '#22c55e',
    econ:    '#f97316',
    major:   '#ef4444',
  };

  let currentDate = null;
  let availableDates = [];
  let activeSection = 'all';
  let currentIssue = null;

  // ─── UTILS ──────────────────────────────────────────────
  function fmtDate(iso) {
    try { const d = new Date(iso+'T00:00:00'); return d.toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'}); } catch { return iso; }
  }
  function shortDate(iso) {
    try { const d = new Date(iso+'T00:00:00'); return d.toLocaleDateString('en-US',{month:'short',day:'numeric'}); } catch { return iso; }
  }
  function todayISO() { return new Date().toISOString().split('T')[0]; }
  function prevDay(iso) { const d = new Date(iso+'T00:00:00'); d.setDate(d.getDate()-1); return d.toISOString().split('T')[0]; }

  function getURLParam(key) { return new URLSearchParams(window.location.search).get(key); }
  function setURLParams(params) {
    const url = new URL(window.location.href);
    Object.entries(params).forEach(([k,v]) => { if (v) url.searchParams.set(k,v); else url.searchParams.delete(k); });
    window.history.replaceState({}, '', url.toString());
  }
  function credClass(score) { return score>=8?'cred-high':score>=5?'cred-mid':'cred-low'; }
  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ─── FETCH ──────────────────────────────────────────────
  async function fetchDates() {
    try { const r = await fetch('/data/dates.json'); if (!r.ok) return []; const d = await r.json(); return d.dates||[]; } catch { return []; }
  }
  async function fetchIssue(date) {
    try { const r = await fetch(`/data/issues/${date}.json`); if (!r.ok) return null; return await r.json(); } catch { return null; }
  }

  // ─── LOAD ───────────────────────────────────────────────
  async function loadForDate(date) {
    showLoading();
    const issue = await fetchIssue(date);
    if (!issue) { showEmpty(); currentDate=date; setURLParams({date,section:activeSection==='all'?null:activeSection}); return; }
    currentIssue = issue;
    renderIssue(issue);
    currentDate = date;
    setURLParams({date, section: activeSection==='all'?null:activeSection});
    renderDateChips();
  }

  async function loadLatest() {
    showLoading();
    const dates = await fetchDates();
    availableDates = dates;
    if (!dates||dates.length===0) { showEmpty(); return; }
    const today = todayISO();
    const target = dates.includes(today) ? today : dates[0];
    await loadForDate(target);
  }

  // ─── STATES ─────────────────────────────────────────────
  function showLoading() {
    document.getElementById('stateLoading').hidden=false;
    document.getElementById('stateEmpty').hidden=true;
    document.getElementById('issueContent').hidden=true;
  }
  function showEmpty() {
    document.getElementById('stateLoading').hidden=true;
    document.getElementById('stateEmpty').hidden=false;
    document.getElementById('issueContent').hidden=true;
  }

  // ─── RENDER ISSUE ────────────────────────────────────────
  function renderIssue(issue) {
    document.getElementById('stateLoading').hidden=true;
    document.getElementById('stateEmpty').hidden=true;
    document.getElementById('issueContent').hidden=false;
    document.getElementById('demoBanner').hidden = issue._demo!==true;

    const totalItems = issue.total_dashboard_items||0;
    const totalSections = issue.total_sections||12;
    const emailItems = issue.total_email_items||24;

    document.getElementById('issueHeader').innerHTML =
      `<div class="issue-date-badge">${fmtDate(issue.issue_date)}</div>` +
      `<h1 class="issue-subject">${esc(issue.title||issue.subject||'')}</h1>` +
      (issue.executive_summary ? `<p class="executive-summary">${esc(issue.executive_summary)}</p>` : '') +
      `<div class="kpi-strip">` +
        `<div class="kpi-card"><div class="kpi-val">${totalSections}</div><div class="kpi-label">Sections</div></div>` +
        `<div class="kpi-card"><div class="kpi-val">${totalItems}</div><div class="kpi-label">Dashboard Items</div></div>` +
        `<div class="kpi-card"><div class="kpi-val">${emailItems}</div><div class="kpi-label">Email Items</div></div>` +
        `<div class="kpi-card"><div class="kpi-val">${issue.issue_date||''}</div><div class="kpi-label">Issue Date</div></div>` +
      `</div>`;

    renderSectionCommand(issue);

    const grid = document.getElementById('sectionsGrid');
    grid.innerHTML = '';
    (issue.sections||[]).forEach(section => grid.appendChild(renderSectionCard(section)));
    applySectionFilter(activeSection);
  }

  // ─── SECTION COMMAND CENTER ──────────────────────────────
  function renderSectionCommand(issue) {
    const el = document.getElementById('sectionCommand');
    if (!el) return;

    const sectionCountMap = {};
    (issue.sections||[]).forEach(s => { sectionCountMap[s.section_id] = (s.items||[]).length; });

    el.innerHTML =
      `<div class="sc-header">` +
        `<h2 class="sc-title">Intelligence Sections</h2>` +
        `<p class="sc-sub">Jump directly into markets, AI, HR, research, economics, or major updates.</p>` +
        `<button class="sc-all-btn ${activeSection==='all'?'sc-all-btn--active':''}" id="scAllBtn">All Sections</button>` +
      `</div>` +
      `<div class="sc-grid">` +
        Object.entries(SECTION_META).map(([sid, m]) => {
          const count = sectionCountMap[sid] || 0;
          const color = CAT_COLOR[m.cat] || '#7c6af7';
          const isActive = activeSection === sid;
          return `<button class="sc-card ${isActive?'sc-card--active':''}" data-section="${sid}" data-color="${color}" style="--sc-color:${color}">` +
            `<div class="sc-card-top">` +
              `<span class="sc-code">${m.code}</span>` +
              `<span class="sc-icon">${m.icon}</span>` +
            `</div>` +
            `<div class="sc-name">${m.name}</div>` +
            `<div class="sc-count">${count} updates</div>` +
            `<div class="sc-desc">${m.desc}</div>` +
          `</button>`;
        }).join('') +
      `</div>`;

    el.querySelectorAll('.sc-card').forEach(btn => {
      btn.addEventListener('click', () => {
        const sid = btn.dataset.section;
        applySectionFilter(sid);
        setURLParams({date:currentDate, section:sid});
        el.querySelectorAll('.sc-card').forEach(b => b.classList.toggle('sc-card--active', b.dataset.section===sid));
        document.getElementById('scAllBtn').classList.remove('sc-all-btn--active');
      });
    });
    document.getElementById('scAllBtn').addEventListener('click', () => {
      applySectionFilter('all');
      setURLParams({date:currentDate, section:null});
      el.querySelectorAll('.sc-card').forEach(b => b.classList.remove('sc-card--active'));
      document.getElementById('scAllBtn').classList.add('sc-all-btn--active');
    });
  }

  // ─── SECTION CARD (article panel) ───────────────────────
  function renderSectionCard(section) {
    const card = document.createElement('div');
    card.className = 'section-card';
    card.dataset.section = section.section_id;

    const meta = SECTION_META[section.section_id] || {};
    const color = CAT_COLOR[meta.cat] || '#7c6af7';
    const items = section.items || [];
    const sourceCount = items.filter(i => i.source_url && i.source_url !== '#').length;
    const itemsHtml = items.map(item => renderItem(item)).join('');

    card.innerHTML =
      `<div class="section-card-header" style="border-left:3px solid ${color}">` +
        `<div class="section-card-top">` +
          `<div>` +
            `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">` +
              `<span class="section-code-badge" style="color:${color};border-color:${color}20;background:${color}12">${esc(section.code||'')}</span>` +
              `<span class="section-name-text">${esc(section.section_name)}</span>` +
              `<span class="section-icon-label">${meta.icon||''}</span>` +
            `</div>` +
            `<p class="section-summary-text">${esc(section.section_summary||'')}</p>` +
          `</div>` +
          `<div class="section-card-stats">` +
            `<span class="sc-stat">${items.length} updates</span>` +
            `<span class="sc-stat sc-stat--dim">${sourceCount} sources</span>` +
          `</div>` +
        `</div>` +
      `</div>` +
      `<div class="section-items">${itemsHtml}</div>`;
    return card;
  }

  function renderItem(item) {
    const score = item.credibility_score||5;
    const sourceUrl = item.source_url||'#';
    const sourceName = item.source_name||item.source_domain||'';
    const credDot = `<span class="credibility-dot ${credClass(score)}" title="Credibility: ${score}/10"></span>`;
    const pubDate = item.published_date&&item.published_date!=='unknown'
      ? `<span style="font-size:0.7rem;color:var(--text-dim);margin-left:6px;">${item.published_date}</span>` : '';

    return `<div class="story-item">` +
      `<div class="story-rank">#${item.rank}</div>` +
      `<p class="story-headline">${esc(item.headline)}</p>` +
      `<p class="story-summary">${esc(item.summary||'')}</p>` +
      `<div class="story-meta">` +
        (item.why_it_matters?`<div class="story-meta-row"><span class="meta-label meta-label--why">Why it matters</span><span class="meta-text">${esc(item.why_it_matters)}</span></div>`:'') +
        (item.peopleos_lens?`<div class="story-meta-row"><span class="meta-label meta-label--lens">PeopleOS Lens</span><span class="meta-text">${esc(item.peopleos_lens)}</span></div>`:'') +
        (item.action?`<div class="story-meta-row"><span class="meta-label meta-label--action">Action</span><span class="meta-text">${esc(item.action)}</span></div>`:'') +
      `</div>` +
      `<a href="${sourceUrl}" target="_blank" rel="noopener" class="story-source">${credDot} ↗ ${esc(sourceName)}${pubDate}</a>` +
    `</div>`;
  }

  // ─── DATE CHIPS ─────────────────────────────────────────
  function renderDateChips() {
    const today = todayISO();
    const container = document.getElementById('dateChips');
    if (!container) return;
    container.innerHTML = '';
    const chipDates = [];
    if (!availableDates.includes(today)) chipDates.push(today);
    availableDates.slice(0,7).forEach(d => { if (!chipDates.includes(d)) chipDates.push(d); });
    chipDates.forEach(date => {
      const btn = document.createElement('button');
      const isToday = date===today;
      const isYesterday = date===prevDay(today);
      btn.className = 'date-chip' + (isToday?' date-chip--today':'') + (date===currentDate?' date-chip--active':'');
      btn.textContent = isToday?'Today':isYesterday?'Yesterday':shortDate(date);
      btn.dataset.date = date;
      btn.addEventListener('click', () => loadForDate(date));
      container.appendChild(btn);
    });
  }

  // ─── SECTION FILTER ─────────────────────────────────────
  function applySectionFilter(sectionId) {
    activeSection = sectionId;
    document.querySelectorAll('.section-card').forEach(card => {
      card.classList.toggle('section-card--hidden', sectionId!=='all' && card.dataset.section!==sectionId);
    });
    document.querySelectorAll('.sf-btn').forEach(btn => {
      btn.classList.toggle('sf-btn--active', btn.dataset.section===sectionId);
    });
    // Update slim filter bar active state too
    document.querySelectorAll('.sc-card').forEach(b => {
      b.classList.toggle('sc-card--active', b.dataset.section===sectionId);
    });
    const allBtn = document.getElementById('scAllBtn');
    if (allBtn) allBtn.classList.toggle('sc-all-btn--active', sectionId==='all');
  }

  // ─── INIT ────────────────────────────────────────────────
  async function init() {
    document.getElementById('datePicker')?.addEventListener('change', function () {
      if (this.value) loadForDate(this.value);
    });
    document.querySelectorAll('.sf-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const sid = btn.dataset.section;
        applySectionFilter(sid);
        setURLParams({date:currentDate, section:sid==='all'?null:sid});
      });
    });

    availableDates = await fetchDates();
    renderDateChips();

    // Read URL params
    const urlSection = getURLParam('section');
    if (urlSection) activeSection = urlSection;

    const urlDate = getURLParam('date');
    if (urlDate) {
      await loadForDate(urlDate);
    } else {
      await loadLatest();
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
