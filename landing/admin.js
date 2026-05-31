/* PeopleOS Brief — Admin JS
   Login page + post-login dashboard with tabs, notifications, subscriber list.
   Detects page by checking for #loginForm vs #logBox.
*/
(function () {
  'use strict';

  // ══════════════════════════════════════════════════════════════
  // LOGIN PAGE
  // ══════════════════════════════════════════════════════════════
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    if (sessionStorage.getItem('admin_token') || localStorage.getItem('admin_token')) {
      window.location.href = '/admin/dashboard/';
      return;
    }

    loginForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const btn      = document.getElementById('loginBtn');
      const msg      = document.getElementById('msg');
      const tokenVal = (document.getElementById('tokenInput').value || '').trim();

      if (!tokenVal) {
        msg.textContent = 'Token is required.';
        msg.className   = 'msg error';
        return;
      }

      btn.disabled    = true;
      btn.textContent = 'Authenticating…';
      msg.textContent = '';
      msg.className   = 'msg';

      let data;
      try {
        const res = await fetch('/api/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: tokenVal }),
        });
        try { data = await res.json(); }
        catch (_) { data = { ok: false, error: `Server error (HTTP ${res.status})` }; }
      } catch (netErr) {
        msg.textContent = 'Cannot reach server: ' + (netErr.message || 'network error');
        msg.className   = 'msg error';
        btn.disabled    = false;
        btn.textContent = 'Authenticate';
        return;
      }

      if (data.ok || data.success) {
        sessionStorage.setItem('admin_token', data.session || tokenVal);
        localStorage.setItem('admin_token',   data.session || tokenVal);
        window.location.href = '/admin/dashboard/';
      } else {
        msg.textContent = data.error || data.message || 'Invalid token.';
        msg.className   = 'msg error';
        btn.disabled    = false;
        btn.textContent = 'Authenticate';
      }
    });

    return; // done with login page
  }

  // ══════════════════════════════════════════════════════════════
  // DASHBOARD PAGE
  // ══════════════════════════════════════════════════════════════
  const token = sessionStorage.getItem('admin_token') || localStorage.getItem('admin_token');
  if (!token) { window.location.href = '/admin/'; return; }

  function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
  }

  // ─── LOG ────────────────────────────────────────────────────
  function addLog(msg, type) {
    const box = document.getElementById('logBox');
    if (!box) return;
    const line = document.createElement('div');
    line.className = `log-line ${type || 'info'}`;
    const ts = new Date().toLocaleTimeString();
    line.textContent = `[${ts}] ${msg}`;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
  }

  function setStatEl(id, value, cls) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value;
    el.className   = 'stat-value' + (cls ? ' ' + cls : '');
  }

  // ─── TABS ───────────────────────────────────────────────────
  function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.toggle('tab-btn--active', b.dataset.tab === tabId);
    });
    document.querySelectorAll('.tab-panel').forEach(p => {
      p.hidden = (p.id !== 'tab-' + tabId);
    });
    if (tabId === 'subscribers') loadSubscribers();
  }
  window.switchTab = switchTab;

  // ─── ADMIN STATS ────────────────────────────────────────────
  async function loadAdminStats() {
    try {
      const res = await fetch('/api/admin/stats', { headers: authHeaders() });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      if (!data.ok) return;

      setKpi('admKpiVisits',     data.total_visits  ?? '—');
      setKpi('admKpiTodayVisits',data.today_visits  ?? '—');
      setKpi('admKpiSubs',       data.total_subscribers ?? '—');
      setKpi('admKpiNewToday',   data.new_today     ?? '—');

      const lastEl = document.getElementById('admKpiLastSub');
      if (lastEl && data.last_subscriber) {
        const email = data.last_subscriber.email || '';
        const when  = data.last_subscriber.created_at
          ? new Date(data.last_subscriber.created_at).toLocaleString()
          : '';
        lastEl.textContent = email ? `${email.split('@')[0]}@… · ${when}` : '—';
      }
    } catch (_) {}
  }

  function setKpi(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = typeof val === 'number' ? val.toLocaleString() : val;
  }

  // ─── STATUS ─────────────────────────────────────────────────
  async function loadStatus() {
    try {
      const res = await fetch('/api/admin/status', { headers: authHeaders() });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      if (!data.ok) { addLog('Status load failed: ' + data.message, 'err'); return; }

      setStatEl('statToday', data.today || '—');
      setStatEl('statTodayExists', data.today_exists ? 'Published ✓' : 'Not yet',
                data.today_exists ? 'ok' : 'warn');
      setStatEl('statLatest', data.latest_date || 'None',
                data.latest_date ? 'ok' : 'warn');

      const gs     = data.generation_status || {};
      const status = gs.status || 'not_started';
      const sCls   = { complete:'ok', running:'warn', failed:'fail', not_started:'' }[status] || '';
      setStatEl('statGenStatus', status, sCls);
      setStatEl('statCount',  data.total_archived || '0');
      setStatEl('statGithub', data.github_configured ? 'Configured ✓' : 'Not configured',
                data.github_configured ? 'ok' : 'warn');

      const note = document.getElementById('githubNote');
      if (note) note.style.display = data.github_configured ? 'none' : 'block';

      addLog(`Status: today=${data.today_exists ? 'exists' : 'missing'}, generation=${status}`, 'info');
    } catch (e) {
      addLog('Status load error: ' + e.message, 'err');
    }
  }

  // ─── NOTIFICATIONS ──────────────────────────────────────────
  let _notifCount = 0;

  async function loadNotifications() {
    try {
      const res = await fetch('/api/admin/notifications', { headers: authHeaders() });
      if (res.status === 401) return;
      const data = await res.json();
      if (!data.ok) return;

      _notifCount = data.new_subscriber_count || 0;
      const badge = document.getElementById('notifBadge');
      const btn   = document.getElementById('notifBtn');
      if (badge) {
        badge.textContent = _notifCount > 99 ? '99+' : String(_notifCount);
        badge.hidden      = _notifCount === 0;
      }
      if (btn) btn.title = _notifCount > 0 ? `${_notifCount} new subscriber${_notifCount > 1 ? 's' : ''}` : 'No new subscribers';

      // Populate panel list
      const list = document.getElementById('notifList');
      if (list) {
        if (_notifCount === 0) {
          list.innerHTML = '<div class="notif-empty">No new subscribers since last check.</div>';
        } else {
          list.innerHTML = data.latest_subscribers.map(s => {
            const when = s.subscribed_at ? new Date(s.subscribed_at).toLocaleString() : '';
            return `<div class="notif-item">
              <span class="notif-email">${esc(s.email)}</span>
              <span class="notif-meta">${esc(s.source||'dashboard')} · ${when}</span>
            </div>`;
          }).join('');
        }
      }
    } catch (_) {}
  }

  function toggleNotifPanel() {
    const panel = document.getElementById('notifPanel');
    if (panel) panel.hidden = !panel.hidden;
  }

  async function markNotificationsSeen() {
    try {
      await fetch('/api/admin/notifications/mark-seen', {
        method: 'POST', headers: authHeaders(),
      });
      _notifCount = 0;
      const badge = document.getElementById('notifBadge');
      if (badge) badge.hidden = true;
      const list = document.getElementById('notifList');
      if (list) list.innerHTML = '<div class="notif-empty">All caught up.</div>';
      const panel = document.getElementById('notifPanel');
      if (panel) panel.hidden = true;
    } catch (_) {}
  }

  // Close notif panel on outside click
  document.addEventListener('click', e => {
    const wrap = document.getElementById('notifWrap');
    if (wrap && !wrap.contains(e.target)) {
      const panel = document.getElementById('notifPanel');
      if (panel) panel.hidden = true;
    }
  });

  function esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // ─── TRIGGER ────────────────────────────────────────────────
  async function trigger(mode, force) {
    addLog(`Triggering: mode=${mode}${force ? ' (force)' : ''}…`, 'info');
    try {
      const res = await fetch('/api/admin/trigger', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ mode, force: !!force }),
      });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      if (data.ok) {
        addLog(`✓ ${data.message}`, 'ok');
        addLog('GitHub Actions workflow triggered. Check Actions tab for progress.', 'info');
      } else {
        addLog(`✗ ${data.message}`, 'err');
        if (data.fallback) addLog(`Manual: ${data.fallback}`, 'warn');
      }
      setTimeout(loadStatus, 3000);
    } catch (e) {
      addLog('Trigger error: ' + e.message, 'err');
    }
  }

  async function triggerTest() {
    const email = prompt('Test email address:');
    if (!email) return;
    addLog(`Sending test email to ${email}…`, 'info');
    try {
      const res = await fetch('/api/admin/trigger', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ mode: 'test_email', test_email: email }),
      });
      const data = await res.json();
      addLog(data.ok ? `✓ ${data.message}` : `✗ ${data.message}`, data.ok ? 'ok' : 'err');
    } catch (e) {
      addLog('Test email error: ' + e.message, 'err');
    }
  }

  async function refreshIndex() {
    addLog('Refreshing archive index…', 'info');
    try {
      await fetch('/api/admin/trigger', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ mode: 'generate_today' }),
      });
      addLog('Index refresh triggered.', 'info');
    } catch (e) {
      addLog('Error: ' + e.message, 'err');
    }
  }

  function confirmLiveSend() {
    const overlay = document.getElementById('confirmOverlay');
    const title   = document.getElementById('confirmTitle');
    const msgEl   = document.getElementById('confirmMsg');
    const okBtn   = document.getElementById('confirmOkBtn');
    if (!overlay) return;
    title.textContent = 'Trigger Live Send?';
    msgEl.textContent = 'This will send the newsletter to ALL active subscribers. Cannot be undone.';
    okBtn.onclick = async () => {
      closeConfirm();
      addLog('Triggering live send…', 'warn');
      try {
        const res = await fetch('/api/admin/trigger', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ mode: 'send_live', confirm_live_send: true }),
        });
        const data = await res.json();
        addLog(data.ok ? `✓ ${data.message}` : `✗ ${data.message}`, data.ok ? 'ok' : 'err');
      } catch (e) {
        addLog('Live send error: ' + e.message, 'err');
      }
    };
    overlay.classList.add('show');
  }

  function closeConfirm() {
    const overlay = document.getElementById('confirmOverlay');
    if (overlay) overlay.classList.remove('show');
  }

  function logout() {
    sessionStorage.removeItem('admin_token');
    localStorage.removeItem('admin_token');
    window.location.href = '/admin/';
  }

  // ─── SUBSCRIBERS TAB ────────────────────────────────────────
  let _subFilter = { status: 'all', since: '' };

  async function loadSubscribers() {
    const tbody   = document.getElementById('subTableBody');
    const countEl = document.getElementById('subCount');
    if (!tbody) return;

    // Show skeleton
    tbody.innerHTML = '<tr><td colspan="6" class="sub-loading">Loading subscribers…</td></tr>';
    if (countEl) countEl.textContent = '';

    const status = document.getElementById('subStatusFilter')?.value || 'all';
    const since  = document.getElementById('subSinceFilter')?.value  || '';
    _subFilter   = { status, since };

    let url = '/api/admin/subscribers';
    const parts = [];
    if (status !== 'all') parts.push(`status=${encodeURIComponent(status)}`);
    if (since) parts.push(`since=${encodeURIComponent(since)}`);
    if (parts.length) url += '?' + parts.join('&');

    try {
      const res = await fetch(url, { headers: authHeaders() });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();

      if (!data.ok) {
        tbody.innerHTML = `<tr><td colspan="6" class="sub-error">Error: ${esc(data.message)}</td></tr>`;
        return;
      }

      const subs = data.subscribers || [];
      if (countEl) countEl.textContent = `${subs.length.toLocaleString()} result${subs.length !== 1 ? 's' : ''}`;

      if (subs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="sub-empty">No subscribers found for this filter.</td></tr>';
        return;
      }

      tbody.innerHTML = subs.map(s => {
        const statusCls = s.status === 'active' ? 'sub-status-active' : 'sub-status-unsub';
        const subDate   = s.created_at ? new Date(s.created_at).toLocaleDateString() : '—';
        const lastEmail = s.last_email_sent_at ? new Date(s.last_email_sent_at).toLocaleDateString() : '—';
        const unsubDate = s.unsubscribed_at ? new Date(s.unsubscribed_at).toLocaleDateString() : '—';
        return `<tr>
          <td class="sub-td sub-td-email">${esc(s.email)}</td>
          <td class="sub-td"><span class="sub-status ${statusCls}">${esc(s.status)}</span></td>
          <td class="sub-td">${esc(s.source || 'web')}</td>
          <td class="sub-td">${subDate}</td>
          <td class="sub-td">${lastEmail}</td>
          <td class="sub-td">${s.status === 'unsubscribed' ? unsubDate : '—'}</td>
        </tr>`;
      }).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="6" class="sub-error">Network error: ${esc(e.message)}</td></tr>`;
    }
  }

  function applySubscriberFilter() { loadSubscribers(); }

  // ─── EXPOSE GLOBALS ─────────────────────────────────────────
  window.trigger             = trigger;
  window.triggerTest         = triggerTest;
  window.refreshIndex        = refreshIndex;
  window.confirmLiveSend     = confirmLiveSend;
  window.closeConfirm        = closeConfirm;
  window.logout              = logout;
  window.loadStatus          = loadStatus;
  window.toggleNotifPanel    = toggleNotifPanel;
  window.markNotificationsSeen = markNotificationsSeen;
  window.applySubscriberFilter = applySubscriberFilter;
  window.loadSubscribers     = loadSubscribers;

  // ─── INIT ───────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    loadAdminStats();
    loadNotifications();
    loadStatus();
  });
})();
