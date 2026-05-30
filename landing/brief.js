/* PeopleOS Brief — Dashboard JS
   Loads from /data/ static JSON files. No API calls for guests.
   No API keys exposed. Works for all visitors.
*/
(function () {
  'use strict';

  let currentDate = null;
  let availableDates = [];
  let activeSection = 'all';

  // ─── UTILS ──────────────────────────────────────────────
  function fmtDate(iso) {
    try {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    } catch { return iso; }
  }

  function shortDate(iso) {
    try {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch { return iso; }
  }

  function todayISO() {
    return new Date().toISOString().split('T')[0];
  }

  function prevDay(iso) {
    const d = new Date(iso + 'T00:00:00');
    d.setDate(d.getDate() - 1);
    return d.toISOString().split('T')[0];
  }

  function getURLDate() {
    return new URLSearchParams(window.location.search).get('date');
  }

  function setURLDate(date) {
    const url = new URL(window.location.href);
    url.searchParams.set('date', date);
    window.history.replaceState({}, '', url.toString());
  }

  function credClass(score) {
    if (score >= 8) return 'cred-high';
    if (score >= 5) return 'cred-mid';
    return 'cred-low';
  }

  // ─── FETCH STATIC FILES ─────────────────────────────────
  // All reads come from /data/ static files — no Supabase, no Groq, no API keys needed.

  async function fetchDates() {
    try {
      const r = await fetch('/data/dates.json');
      if (!r.ok) return [];
      const d = await r.json();
      return d.dates || [];
    } catch { return []; }
  }

  async function fetchIssue(date) {
    try {
      const r = await fetch(`/data/issues/${date}.json`);
      if (!r.ok) return null;
      return await r.json();
    } catch { return null; }
  }

  // ─── LOAD FLOW ──────────────────────────────────────────
  async function loadForDate(date) {
    showLoading();
    const issue = await fetchIssue(date);
    if (!issue) {
      showEmpty();
      currentDate = date;
      setURLDate(date);
      return;
    }
    renderIssue(issue);
    currentDate = date;
    setURLDate(date);
    renderDateChips();
  }

  async function loadLatest() {
    showLoading();
    const dates = await fetchDates();
    availableDates = dates;

    if (!dates || dates.length === 0) {
      showEmpty();
      return;
    }

    const today = todayISO();
    const target = dates.includes(today) ? today : dates[0];
    await loadForDate(target);
  }

  // ─── RENDER ─────────────────────────────────────────────
  function showLoading() {
    document.getElementById('stateLoading').hidden = false;
    document.getElementById('stateEmpty').hidden = true;
    document.getElementById('issueContent').hidden = true;
  }

  function showEmpty() {
    document.getElementById('stateLoading').hidden = true;
    document.getElementById('stateEmpty').hidden = false;
    document.getElementById('issueContent').hidden = true;
  }

  function renderIssue(issue) {
    document.getElementById('stateLoading').hidden = true;
    document.getElementById('stateEmpty').hidden = true;
    document.getElementById('issueContent').hidden = false;

    const demo = issue._demo === true;
    document.getElementById('demoBanner').hidden = !demo;

    // Header
    const totalItems = issue.total_dashboard_items || 0;
    document.getElementById('issueHeader').innerHTML =
      `<div class="issue-date-badge">${fmtDate(issue.issue_date)}</div>` +
      `<h1 class="issue-subject">${esc(issue.title || issue.subject || '')}</h1>` +
      (issue.executive_summary ? `<p class="executive-summary">${esc(issue.executive_summary)}</p>` : '') +
      (totalItems ? `<p style="font-size:0.8rem;color:var(--text-dim);margin-top:8px;">${totalItems} intelligence items across ${issue.total_sections || 12} sections</p>` : '');

    // Sections
    const grid = document.getElementById('sectionsGrid');
    grid.innerHTML = '';
    (issue.sections || []).forEach(section => {
      grid.appendChild(renderSectionCard(section));
    });

    // Subscribe CTA inside dashboard
    const ctaBlock = document.createElement('div');
    ctaBlock.className = 'dashboard-subscribe-cta';
    ctaBlock.innerHTML = `
      <div class="dsub-inner">
        <p class="dsub-title">Want this in your inbox every morning?</p>
        <p class="dsub-sub">Subscribe free. One sharp brief. 7:00 AM IST.</p>
        <a href="/" class="dsub-btn">Subscribe free →</a>
      </div>`;
    grid.appendChild(ctaBlock);

    applySectionFilter(activeSection);
  }

  function renderSectionCard(section) {
    const card = document.createElement('div');
    card.className = 'section-card';
    card.dataset.section = section.section_id;

    const items = (section.items || []);
    const itemsHtml = items.map(item => renderItem(item)).join('');

    card.innerHTML =
      `<div class="section-card-header">` +
        `<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">` +
          `<span style="font-size:0.7rem;font-weight:800;color:var(--text-dim);">${esc(section.code || '')}</span>` +
          `<span class="section-badge">${esc(section.section_name)}</span>` +
          `<span style="font-size:0.7rem;color:var(--text-dim);margin-left:auto;">${items.length} items</span>` +
        `</div>` +
        `<p class="section-summary-text">${esc(section.section_summary || '')}</p>` +
      `</div>` +
      `<div class="section-items">${itemsHtml}</div>`;
    return card;
  }

  function renderItem(item) {
    const score = item.credibility_score || 5;
    const sourceUrl = item.source_url || '#';
    const sourceName = item.source_name || item.source_domain || '';
    const credDot = `<span class="credibility-dot ${credClass(score)}" title="Credibility: ${score}/10"></span>`;
    const pubDate = item.published_date && item.published_date !== 'unknown' ? `<span style="font-size:0.7rem;color:var(--text-dim);margin-left:6px;">${item.published_date}</span>` : '';

    return `<div class="story-item">` +
      `<div class="story-rank">#${item.rank}</div>` +
      `<p class="story-headline">${esc(item.headline)}</p>` +
      `<p class="story-summary">${esc(item.summary || '')}</p>` +
      `<div class="story-meta">` +
        (item.why_it_matters ? `<div class="story-meta-row"><span class="meta-label meta-label--why">Why it matters</span><span class="meta-text">${esc(item.why_it_matters)}</span></div>` : '') +
        (item.peopleos_lens ? `<div class="story-meta-row"><span class="meta-label meta-label--lens">PeopleOS Lens</span><span class="meta-text">${esc(item.peopleos_lens)}</span></div>` : '') +
        (item.action ? `<div class="story-meta-row"><span class="meta-label meta-label--action">Action</span><span class="meta-text">${esc(item.action)}</span></div>` : '') +
      `</div>` +
      `<a href="${sourceUrl}" target="_blank" rel="noopener" class="story-source">${credDot} ↗ ${esc(sourceName)}${pubDate}</a>` +
    `</div>`;
  }

  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ─── DATE CHIPS ─────────────────────────────────────────
  function renderDateChips() {
    const today = todayISO();
    const container = document.getElementById('dateChips');
    if (!container) return;
    container.innerHTML = '';

    const chipDates = [];
    if (!availableDates.includes(today)) chipDates.push(today);
    availableDates.slice(0, 7).forEach(d => { if (!chipDates.includes(d)) chipDates.push(d); });

    chipDates.forEach(date => {
      const btn = document.createElement('button');
      const isToday = date === today;
      const isYesterday = date === prevDay(today);
      btn.className = 'date-chip' +
        (isToday ? ' date-chip--today' : '') +
        (date === currentDate ? ' date-chip--active' : '');
      btn.textContent = isToday ? 'Today' : isYesterday ? 'Yesterday' : shortDate(date);
      btn.dataset.date = date;
      btn.addEventListener('click', () => loadForDate(date));
      container.appendChild(btn);
    });
  }

  // ─── SECTION FILTER ─────────────────────────────────────
  function applySectionFilter(sectionId) {
    activeSection = sectionId;
    document.querySelectorAll('.section-card').forEach(card => {
      card.classList.toggle('section-card--hidden',
        sectionId !== 'all' && card.dataset.section !== sectionId);
    });
    document.querySelectorAll('.sf-btn').forEach(btn => {
      btn.classList.toggle('sf-btn--active', btn.dataset.section === sectionId);
    });
  }

  // ─── INIT ────────────────────────────────────────────────
  async function init() {
    document.getElementById('datePicker')?.addEventListener('change', function () {
      if (this.value) loadForDate(this.value);
    });
    document.querySelectorAll('.sf-btn').forEach(btn => {
      btn.addEventListener('click', () => applySectionFilter(btn.dataset.section));
    });

    availableDates = await fetchDates();
    renderDateChips();

    const urlDate = getURLDate();
    if (urlDate) {
      await loadForDate(urlDate);
    } else {
      await loadLatest();
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
