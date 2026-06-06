/* PeopleOS Brief - Archive page JS. Loads from /data/archive.json static file. */
(function () {
  'use strict';

  function fmtDate(iso) {
    try {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    } catch {
      return iso;
    }
  }

  function monthLabel(iso) {
    try {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    } catch {
      return iso.slice(0, 7);
    }
  }

  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function groupByMonth(issues) {
    return issues.reduce((groups, issue) => {
      const key = String(issue.issue_date || '').slice(0, 7);
      if (!groups[key]) groups[key] = [];
      groups[key].push(issue);
      return groups;
    }, {});
  }

  function setLoading(on) {
    const el = document.getElementById('archiveLoading');
    if (!el) return;
    el.hidden = !on;
    el.style.display = on ? 'flex' : 'none';
  }

  function showEmpty() {
    const empty = document.getElementById('archiveEmpty');
    if (empty) empty.hidden = false;
  }

  function showError(message) {
    const empty = document.getElementById('archiveEmpty');
    if (!empty) return;
    empty.hidden = false;
    const title = empty.querySelector('h2');
    const copy = empty.querySelector('p');
    if (title) title.textContent = 'Archive could not load.';
    if (copy) copy.textContent = message || 'Please refresh and try again.';
  }

  function renderArchive(issues) {
    const container = document.getElementById('archiveList');
    if (!container) return;

    container.innerHTML = '';
    if (!issues || issues.length === 0) {
      showEmpty();
      return;
    }

    container.hidden = false;
    const groups = groupByMonth(issues);

    Object.keys(groups).sort().reverse().forEach(monthKey => {
      const monthDiv = document.createElement('div');
      monthDiv.className = 'archive-month';

      const label = document.createElement('p');
      label.className = 'month-label';
      label.textContent = monthLabel(monthKey + '-01');
      monthDiv.appendChild(label);

      groups[monthKey].forEach(issue => {
        const row = document.createElement('div');
        row.className = 'archive-issue';
        const sections = issue.section_count || 12;
        const items = issue.item_count || 72;
        const title = issue.title || issue.subject || 'PeopleOS Brief';
        const isDemo = issue._demo === true || /demo fallback/i.test(`${title} ${issue.preheader || ''}`);

        row.innerHTML =
          `<div class="archive-issue-left">` +
            `<div class="archive-issue-date">${fmtDate(issue.issue_date)}</div>` +
            `<div class="archive-issue-subject">${esc(title)}${isDemo ? ' <span class="archive-demo-pill">Demo Fallback</span>' : ''}</div>` +
            (issue.preheader ? `<div class="archive-issue-preheader">${esc(issue.preheader)}</div>` : '') +
            `<div class="archive-issue-meta">${sections} sections · ${items} stories</div>` +
          `</div>` +
          `<a href="/brief/?date=${encodeURIComponent(issue.issue_date)}" class="read-brief-btn">Read brief -></a>`;
        monthDiv.appendChild(row);
      });

      container.appendChild(monthDiv);
    });
  }

  async function init() {
    setLoading(true);
    try {
      const response = await fetch('/data/archive.json?t=' + Date.now(), { cache: 'no-store' });
      if (!response.ok) throw new Error(`archive.json returned HTTP ${response.status}`);
      const data = await response.json();
      renderArchive(data.issues || []);
    } catch (error) {
      showError(error.message);
    } finally {
      setLoading(false);
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
