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
    ai:      '#a855f7',
    trending:'#f59e0b',
    hr:      '#10b981',
    econ:    '#f97316',
    major:   '#ef4444',
  };

  const CAT_LABEL = {
    markets:'Markets', ai:'AI', trending:'Trending',
    hr:'Human Capital', econ:'Economics', major:'Major Updates',
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
    if (!issue) {
      const latest = availableDates[0];
      if (latest && latest !== date) {
        console.log('PeopleOS loaded issue:', latest);
        showDateWarning(date, latest);
        setURLParams({date:null, section:activeSection==='all'?null:activeSection});
        await loadForDate(latest);
      } else {
        console.log('PeopleOS loaded issue:', null);
        showEmpty();
        currentDate = date;
        setURLParams({date,section:activeSection==='all'?null:activeSection});
      }
      return;
    }
    console.log('PeopleOS loaded issue:', date);
    document.title = `PeopleOS Brief — ${date}`;
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
    console.log('PeopleOS latest available date:', target);
    await loadForDate(target);
  }

  // ─── DATE WARNING ───────────────────────────────────────
  function showDateWarning(requestedDate, latestDate) {
    const bar = document.getElementById('dateBar');
    if (!bar) return;
    const existing = document.getElementById('dateWarning');
    if (existing) existing.remove();
    const el = document.createElement('div');
    el.id = 'dateWarning';
    el.style.cssText = 'background:rgba(249,115,22,0.12);border:1px solid rgba(249,115,22,0.3);color:#fdba74;font-size:0.8rem;padding:8px 16px;text-align:center;display:flex;align-items:center;justify-content:center;gap:12px;';
    el.innerHTML = `Requested issue <strong>${requestedDate}</strong> is unavailable. Showing latest available brief (${latestDate}).` +
      ` <button id="viewLatestBriefBtn" style="background:none;border:1px solid rgba(249,115,22,0.35);border-radius:6px;color:#fdba74;cursor:pointer;font-size:0.78rem;padding:4px 8px;">View latest brief</button>` +
      ` <button id="dismissDateWarningBtn" style="background:none;border:none;color:#fdba74;cursor:pointer;font-size:0.9rem;">x</button>`;
    bar.insertAdjacentElement('beforebegin', el);
    document.getElementById('viewLatestBriefBtn')?.addEventListener('click', () => {
      setURLParams({date:null, section:activeSection==='all'?null:activeSection});
      loadLatest();
    });
    document.getElementById('dismissDateWarningBtn')?.addEventListener('click', () => el.remove());
  }

  // ─── STATES ─────────────────────────────────────────────
  function showLoading() {
    const l = document.getElementById('stateLoading');
    const e = document.getElementById('stateEmpty');
    const c = document.getElementById('issueContent');
    if (l) { l.hidden=false; l.style.display='flex'; }
    if (e) { e.hidden=true;  e.style.display='none'; }
    if (c) { c.hidden=true;  c.style.display='none'; }
  }
  function showEmpty() {
    const l = document.getElementById('stateLoading');
    const e = document.getElementById('stateEmpty');
    const c = document.getElementById('issueContent');
    if (l) { l.hidden=true;  l.style.display='none'; }
    if (e) { e.hidden=false; e.style.display=''; }
    if (c) { c.hidden=true;  c.style.display='none'; }
  }

  // ─── RENDER ISSUE ────────────────────────────────────────
  function renderIssue(issue) {
    const l = document.getElementById('stateLoading');
    const e = document.getElementById('stateEmpty');
    const c = document.getElementById('issueContent');
    if (l) { l.hidden=true;  l.style.display='none'; }
    if (e) { e.hidden=true;  e.style.display='none'; }
    if (c) { c.hidden=false; c.style.display=''; }

    const isDemo = issue._demo===true && (issue.total_dashboard_items||0) < 60;
    const banner = document.getElementById('demoBanner');
    if (banner) { banner.hidden=!isDemo; banner.style.display=!isDemo?'none':''; }

    const totalItems    = issue.total_dashboard_items||0;
    const totalSections = issue.total_sections||12;
    const emailItems    = issue.total_email_items||24;

    document.getElementById('issueHeader').innerHTML =
      `<div class="issue-date-badge">${fmtDate(issue.issue_date)}</div>` +
      `<h1 class="issue-subject">${esc(issue.title||issue.subject||'PeopleOS Brief')}</h1>` +
      (issue.executive_summary ? `<p class="executive-summary">${esc(issue.executive_summary)}</p>` : '') +
      `<div class="kpi-strip">` +
        `<div class="kpi-card">` +
          `<div class="kpi-val">${totalSections}</div>` +
          `<div class="kpi-label">Intelligence Sections</div>` +
          `<div class="kpi-micro">Markets · AI · HR · Econ</div>` +
        `</div>` +
        `<div class="kpi-card">` +
          `<div class="kpi-val">${totalItems}</div>` +
          `<div class="kpi-label">Dashboard Signals</div>` +
          `<div class="kpi-micro">Full briefing across all sections</div>` +
        `</div>` +
        `<div class="kpi-card">` +
          `<div class="kpi-val">${emailItems}</div>` +
          `<div class="kpi-label">Email Digest Items</div>` +
          `<div class="kpi-micro">Top 2 per section · Morning cut</div>` +
        `</div>` +
        `<div class="kpi-card">` +
          `<div class="kpi-val">${issue.issue_date||'—'}</div>` +
          `<div class="kpi-label">Issue Date</div>` +
          `<div class="kpi-micro">Daily · 7:00 AM IST</div>` +
        `</div>` +
        `<div class="kpi-card" id="kpiVisitors">` +
          `<div class="kpi-val kpi-live" id="kpiVisitorsVal">—</div>` +
          `<div class="kpi-label">Page Views</div>` +
          `<div class="kpi-micro" id="kpiPageViewsVal" style="font-size:0.72rem;color:#64748b;">Loading…</div>` +
        `</div>` +
        `<div class="kpi-card" id="kpiSubscribers">` +
          `<div class="kpi-val kpi-live" id="kpiSubscribersVal">—</div>` +
          `<div class="kpi-label">Subscribers</div>` +
          `<div class="kpi-micro" id="kpiUniqueVisitorsVal" style="font-size:0.72rem;color:#64748b;">Morning brief readers</div>` +
        `</div>` +
      `</div>`;

    renderSectionCommand(issue);

    const grid = document.getElementById('sectionsGrid');
    grid.innerHTML = '';
    (issue.sections||[]).forEach(section => {
      try { grid.appendChild(renderSectionCard(section)); }
      catch(err) { console.error('Section render error:', section.code, err); }
    });

    applySectionFilter(activeSection);
  }

  // ─── SECTION COMMAND CENTER ──────────────────────────────
  function renderSectionCommand(issue) {
    const el = document.getElementById('sectionCommand');
    if (!el) return;

    const sectionCountMap = {};
    (issue.sections||[]).forEach(s => { sectionCountMap[s.section_id]=(s.items||[]).length; });

    el.innerHTML =
      `<div class="sc-header">` +
        `<div class="sc-title-block">` +
          `<h2 class="sc-title">Intelligence Sections</h2>` +
          `<p class="sc-sub">Select a section to jump directly into its feed.</p>` +
        `</div>` +
        `<button class="sc-all-btn ${activeSection==='all'?'sc-all-btn--active':''}" id="scAllBtn">All Sections</button>` +
      `</div>` +
      `<div class="sc-grid">` +
        Object.entries(SECTION_META).map(([sid, m]) => {
          const count = sectionCountMap[sid]||0;
          const color = CAT_COLOR[m.cat]||'#6366f1';
          const isActive = activeSection===sid;
          return `<button class="sc-card ${isActive?'sc-card--active':''}" data-section="${sid}" style="--sc-color:${color}">` +
            `<div class="sc-card-top">` +
              `<span class="sc-code" style="color:${color};border-color:${color}30;background:${color}12">${m.code}</span>` +
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
        applySectionFilter(sid, true);
        setURLParams({date:currentDate, section:sid});
      });
    });
    document.getElementById('scAllBtn').addEventListener('click', () => {
      applySectionFilter('all');
      setURLParams({date:currentDate, section:null});
    });
  }

  // ─── SECTION CARD (article panel) ───────────────────────
  function renderSectionCard(section) {
    const card = document.createElement('div');
    card.className = 'section-card';
    card.id = 'section-' + section.section_id;
    card.dataset.section = section.section_id;

    const meta    = SECTION_META[section.section_id]||{};
    const color   = CAT_COLOR[meta.cat]||'#6366f1';
    const catLabel= CAT_LABEL[meta.cat]||'';
    const items   = section.items||[];
    const sourceCount = items.filter(i=>i.source_url&&i.source_url!=='#').length;

    card.style.setProperty('--sc-color', color);

    card.innerHTML =
      `<div class="section-card-header">` +
        `<div class="section-card-top">` +
          `<div class="section-card-title-group">` +
            `<span class="section-code-badge" style="color:${color};border-color:${color}30;background:${color}12">${esc(section.code||meta.code||'')}</span>` +
            `<span class="section-name-text">${esc(section.section_name||meta.name||'')}</span>` +
          `</div>` +
          `<div class="section-card-right">` +
            `<span class="section-cat-pill" style="--cat-color:${color}">${catLabel}</span>` +
            `<span class="section-stats">${items.length} updates · ${sourceCount} sources</span>` +
          `</div>` +
        `</div>` +
        (section.section_summary ? `<p class="section-summary-text">${esc(section.section_summary)}</p>` : '') +
      `</div>` +
      `<div class="section-items">${items.map(item=>renderItem(item)).join('')}</div>`;

    return card;
  }

  // ─── ITEM (article card) ─────────────────────────────────
  function renderItem(item) {
    const score   = item.credibility_score||5;
    const scoreClass = credClass(score);
    const sourceUrl  = item.source_url||'#';
    const sourceName = esc(item.source_name||item.source_domain||'');
    const pubDate    = item.published_date&&item.published_date!=='unknown' ? item.published_date : '';

    const insights = [
      item.why_it_matters ? `<div class="insight-row"><span class="insight-tag why">WHY</span><span class="insight-body">${esc(item.why_it_matters)}</span></div>` : '',
      item.peopleos_lens  ? `<div class="insight-row"><span class="insight-tag lens">LENS</span><span class="insight-body">${esc(item.peopleos_lens)}</span></div>` : '',
      item.action         ? `<div class="insight-row"><span class="insight-tag action">ACT</span><span class="insight-body">${esc(item.action)}</span></div>` : '',
    ].filter(Boolean).join('');

    return `<div class="story-item">` +
      `<div class="story-top">` +
        `<span class="story-rank">#${item.rank}</span>` +
        `<span class="cred-dot ${scoreClass}" title="Credibility: ${score}/10"></span>` +
      `</div>` +
      `<p class="story-headline">${esc(item.headline)}</p>` +
      `<p class="story-summary">${esc(item.summary||'')}</p>` +
      (insights ? `<div class="story-insights">${insights}</div>` : '') +
      `<div class="story-footer">` +
        `<a href="${sourceUrl}" target="_blank" rel="noopener noreferrer" class="source-pill">` +
          `<span class="source-arrow">↗</span>` +
          `<span>${sourceName}${pubDate?' · '+pubDate:''}</span>` +
        `</a>` +
      `</div>` +
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
      btn.className = 'date-chip'+(isToday?' date-chip--today':'')+(date===currentDate?' date-chip--active':'');
      btn.textContent = isToday?'Today':isYesterday?'Yesterday':shortDate(date);
      btn.dataset.date = date;
      btn.addEventListener('click', () => {
        if (!availableDates.includes(date)) {
          showDateWarning(date, availableDates[0]);
          setURLParams({date:null, section:activeSection==='all'?null:activeSection});
          loadLatest();
        } else {
          loadForDate(date);
        }
      });
      container.appendChild(btn);
    });
  }

  // ─── SECTION FILTER + SCROLL ────────────────────────────
  function applySectionFilter(sectionId, scroll) {
    activeSection = sectionId;

    // Article panels
    document.querySelectorAll('.section-card').forEach(card => {
      card.classList.toggle('section-card--hidden', sectionId!=='all' && card.dataset.section!==sectionId);
    });

    // Slim filter bar
    document.querySelectorAll('.sf-btn').forEach(btn => {
      btn.classList.toggle('sf-btn--active', btn.dataset.section===sectionId);
    });

    // Command center card states
    document.querySelectorAll('.sc-card').forEach(b => {
      b.classList.toggle('sc-card--active', b.dataset.section===sectionId);
    });
    const allBtn = document.getElementById('scAllBtn');
    if (allBtn) allBtn.classList.toggle('sc-all-btn--active', sectionId==='all');

    // Selected section banner
    const banner = document.getElementById('selectedSectionBanner');
    if (banner) {
      if (sectionId==='all') {
        banner.hidden = true;
        banner.innerHTML = '';
      } else {
        const meta  = SECTION_META[sectionId]||{};
        const color = CAT_COLOR[meta.cat]||'#6366f1';
        const catLabel = CAT_LABEL[meta.cat]||'';
        let count = 0;
        if (currentIssue) {
          const sec = (currentIssue.sections||[]).find(s=>s.section_id===sectionId);
          if (sec) count = (sec.items||[]).length;
        }
        banner.hidden = false;
        banner.style.setProperty('--ssb-color', color);
        banner.innerHTML =
          `<div class="ssb-inner">` +
            `<div class="ssb-left">` +
              `<span class="ssb-code" style="color:${color}">${meta.code||''}</span>` +
              `<div>` +
                `<div class="ssb-name">${meta.name||sectionId}</div>` +
                `<div class="ssb-desc">${meta.desc||''}</div>` +
              `</div>` +
            `</div>` +
            `<div class="ssb-right">` +
              `<span class="ssb-cat" style="color:${color}">${catLabel}</span>` +
              `<span class="ssb-count">${count} updates</span>` +
              `<button class="ssb-all-btn" id="ssbAllBtn">← All Sections</button>` +
            `</div>` +
          `</div>`;
        document.getElementById('ssbAllBtn')?.addEventListener('click', () => {
          applySectionFilter('all');
          setURLParams({date:currentDate, section:null});
        });
      }
    }

    // Scroll to section content
    if (scroll && sectionId!=='all') {
      requestAnimationFrame(() => {
        const target = document.getElementById('selectedSectionBanner') || document.getElementById('section-'+sectionId);
        if (target) target.scrollIntoView({behavior:'smooth', block:'start'});
      });
    }
  }

  // ─── INIT ────────────────────────────────────────────────
  async function init() {
    document.getElementById('datePicker')?.addEventListener('change', function () {
      if (this.value) loadForDate(this.value);
    });
    document.querySelectorAll('.sf-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const sid = btn.dataset.section;
        applySectionFilter(sid, true);
        setURLParams({date:currentDate, section:sid==='all'?null:sid});
      });
    });

    availableDates = await fetchDates();
    renderDateChips();

    const urlSection = getURLParam('section');
    if (urlSection && urlSection!=='all') activeSection = urlSection;

    const urlDate = getURLParam('date');
    console.log('PeopleOS requested date:', urlDate || '(none)');
    console.log('PeopleOS available dates:', availableDates);
    console.log('PeopleOS latest available date:', availableDates[0] || null);

    if (urlDate) {
      // Validate date exists; if not, fallback to latest with warning
      if (availableDates.length > 0 && !availableDates.includes(urlDate)) {
        const latest = availableDates[0];
        console.log('PeopleOS loaded issue:', latest);
        showDateWarning(urlDate, latest);
        setURLParams({date: null, section: urlSection && urlSection!=='all' ? urlSection : null});
        await loadLatest();
      } else {
        await loadForDate(urlDate);
      }
    } else {
      await loadLatest();
    }

    // Scroll to section if loaded from URL param
    if (urlSection && urlSection!=='all') {
      setTimeout(() => {
        const banner = document.getElementById('selectedSectionBanner');
        const card   = document.getElementById('section-'+urlSection);
        const target = (banner && !banner.hidden) ? banner : card;
        if (target) target.scrollIntoView({behavior:'smooth', block:'start'});
      }, 200);
    }

    // Record visit + update live KPI cards (non-blocking)
    recordVisit();
  }

  async function recordVisit() {
    try {
      const res = await fetch('/api/visit', {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: window.location.pathname + window.location.search, referrer: document.referrer || '' })
      });
      const data = res.ok ? await res.json().catch(() => null) : null;
      if (data && data.ok) updateStatsUI(data);
      await loadStats();
    } catch (err) {
      console.warn('PeopleOS visit failed:', err);
      await loadStats();
    }
  }

  async function loadStats() {
    try {
      const res = await fetch('/api/stats?t=' + Date.now(), { cache: 'no-store' });
      const data = res.ok ? await res.json().catch(() => null) : null;
      if (data && data.ok) {
        updateStatsUI(data);
      } else {
        throw new Error((data && data.error) || 'Stats request failed');
      }
    } catch (err) {
      console.warn('PeopleOS stats failed:', err);
      ['kpiVisitorsVal', 'kpiSubscribersVal', 'kpiPageViewsVal', 'kpiUniqueVisitorsVal'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '—';
      });
    }
  }

  function updateStatsUI(data) {
    const pv = data.total_page_views ?? data.total_visits ?? 0;
    const uv = data.unique_visitors_today ?? 0;
    const sb = data.total_subscribers ?? 0;
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl('kpiVisitorsVal', pv.toLocaleString());
    setEl('kpiPageViewsVal', pv.toLocaleString() + ' total · ' + uv.toLocaleString() + ' today');
    setEl('kpiSubscribersVal', sb.toLocaleString());
    setEl('kpiUniqueVisitorsVal', sb.toLocaleString() + ' morning brief readers');
    setEl('readerCountLine', `Join ${sb.toLocaleString()} readers getting the executive cut every morning.`);
    console.log('PeopleOS analytics:', { total_page_views: pv, unique_visitors_today: uv, total_subscribers: sb });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
