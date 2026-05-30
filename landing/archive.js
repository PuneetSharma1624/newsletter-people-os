/* PeopleOS Brief — Archive page JS. Loads from /data/archive.json static file. */
(function () {
  'use strict';

  function fmtDate(iso) {
    try {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    } catch { return iso; }
  }

  function monthLabel(iso) {
    try {
      const d = new Date(iso + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    } catch { return iso.slice(0, 7); }
  }

  function groupByMonth(issues) {
    const groups = {};
    issues.forEach(issue => {
      const key = issue.issue_date.slice(0, 7);
      if (!groups[key]) groups[key] = [];
      groups[key].push(issue);
    });
    return groups;
  }

  function renderArchive(issues) {
    document.getElementById('archiveLoading').hidden = true;
    if (!issues || issues.length === 0) {
      document.getElementById('archiveEmpty').hidden = false;
      return;
    }
    document.getElementById('archiveList').hidden = false;
    const container = document.getElementById('archiveList');
    const groups = groupByMonth(issues);

    Object.keys(groups).sort().reverse().forEach(monthKey => {
      const monthIssues = groups[monthKey];
      const monthDiv = document.createElement('div');
      monthDiv.className = 'archive-month';
      const label = document.createElement('p');
      label.className = 'month-label';
      label.textContent = monthLabel(monthKey + '-01');
      monthDiv.appendChild(label);

      monthIssues.forEach(issue => {
        const row = document.createElement('div');
        row.className = 'archive-issue';
        const sections = issue.section_count || 12;
        const items = issue.item_count || 72;
        row.innerHTML =
          `<div class="archive-issue-left">` +
            `<div class="archive-issue-date">${fmtDate(issue.issue_date)}</div>` +
            `<div class="archive-issue-subject">${esc(issue.title || issue.subject)}</div>` +
            (issue.preheader ? `<div class="archive-issue-preheader">${esc(issue.preheader)}</div>` : '') +
            `<div class="archive-issue-meta">${sections} sections · ${items} stories</div>` +
          `</div>` +
          `<a href="/brief?date=${issue.issue_date}" class="read-brief-btn">Read brief →</a>`;
        monthDiv.appendChild(row);
      });
      container.appendChild(monthDiv);
    });
  }

  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  async function init() {
    try {
      // Load from static file first
      const r = await fetch('/data/archive.json');
      if (r.ok) {
        const data = await r.json();
        const issues = data.issues || [];
        if (issues.length > 0) {
          renderArchive(issues);
          return;
        }
      }
      // Fallback to API
      const r2 = await fetch('/api/archive');
      const data2 = await r2.json();
      renderArchive(data2.archive || []);
    } catch {
      document.getElementById('archiveLoading').hidden = true;
      document.getElementById('archiveEmpty').hidden = false;
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
