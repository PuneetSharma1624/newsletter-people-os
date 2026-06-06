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
        const res = await fetch('/api/admin?action=status', {
          method: 'GET',
          headers: { 'Authorization': `Bearer ${tokenVal}` },
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

      if (data.ok) {
        sessionStorage.setItem('admin_token', tokenVal);
        localStorage.setItem('admin_token',   tokenVal);
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
  const ADMIN_REFRESH_INTERVAL_MS = 30000;
  let adminRefreshTimer = null;

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
      const res = await fetch('/api/admin?action=stats', { headers: authHeaders() });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      if (!data.ok) {
        addLog('Admin stats failed: ' + (data.message || data.error || 'unknown'), 'err');
        ['admKpiVisits', 'admKpiTodayVisits', 'admKpiSubs', 'admKpiNewToday'].forEach(id => setKpi(id, 'Error'));
        return;
      }

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
    } catch (e) {
      addLog('Admin stats error: ' + e.message, 'err');
    }
  }

  function setKpi(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = typeof val === 'number' ? val.toLocaleString() : val;
  }

  // ─── STATUS ─────────────────────────────────────────────────
  async function loadStatus() {
    try {
      const res = await fetch('/api/admin?action=status', { headers: authHeaders() });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      if (!data.ok) { addLog('Status load failed: ' + data.message, 'err'); return; }

      setStatEl('statToday', data.today || '—');
      setStatEl('statTodayExists', data.today_exists ? 'Published ✓' : 'Not yet',
                data.today_exists ? 'ok' : 'warn');

      const gs = data.generation_status || {};
      const latestComplete = gs.latest_complete_issue_date || data.latest_date || 'None';
      setStatEl('statLatest', latestComplete, latestComplete !== 'None' ? 'ok' : 'warn');
      if (!data.today_exists && data.latest_info) {
        const demoNote = data.latest_info.is_demo ? ' Latest available issue is demo fallback.' : '';
        addLog(`Today's issue is missing. Latest available issue is ${data.latest_info.date}.${demoNote}`, data.latest_info.is_demo ? 'warn' : 'info');
      }

      const genStatus = gs.generation_status || gs.status || 'not_started';
      const genCls = { complete:'ok', in_progress:'warn', running:'warn', failed:'fail',
                       retrying:'warn', not_started:'', skipped_already_complete:'ok' }[genStatus] || '';
      setStatEl('statGenStatus', genStatus.replace(/_/g,' '), genCls);

      // 7:00 run indicator
      const attempt = gs.last_generation_attempt || '';
      const ran0700 = attempt === 'scheduled_0700' && genStatus === 'complete' && gs.latest_complete_issue_date === data.today;
      setStatEl('stat0700', ran0700 ? 'Complete ✓' : (genStatus === 'in_progress' ? 'Running…' : 'Not run'), ran0700 ? 'ok' : (genStatus === 'in_progress' ? 'warn' : ''));

      // 7:15 retry indicator
      const ran0715 = attempt === 'retry_0715';
      setStatEl('stat0715', ran0715 ? (genStatus === 'complete' ? 'Retried ✓' : 'Retrying…') : 'Not needed', ran0715 && genStatus === 'complete' ? 'ok' : '');

      // Production (shown as unknown until manually checked)
      setStatEl('statProduction', '— check manually');

      // Email status
      const emailStatus = gs.last_email_status || 'not_sent';
      const emailDate   = gs.last_email_sent_date || '';
      const emailToday  = emailDate === data.today;
      const emailCls    = emailStatus === 'sent' && emailToday ? 'ok' : emailStatus === 'failed' ? 'fail' : '';
      setStatEl('statEmailSent',
        emailStatus === 'sent' && emailToday ? 'Sent ✓' :
        emailStatus === 'skipped_already_sent' ? 'Already sent' :
        emailStatus === 'skipped_issue_missing' ? 'Skipped (no issue)' :
        emailStatus === 'skipped_issue_not_deployed' ? 'Skipped (not live)' :
        emailStatus === 'failed' ? 'Failed ✗' : 'Not sent', emailCls);

      // Last error
      const lastErr = gs.last_generation_error || gs.last_error || '';
      setStatEl('statLastError', lastErr || '—', lastErr ? 'fail' : '');

      setStatEl('statCount', data.total_archived || '0');

      const note = document.getElementById('githubNote');
      if (note) note.style.display = data.github_configured ? 'none' : 'block';

      addLog(`Status: today=${data.today_exists ? 'exists' : 'missing'}, gen=${genStatus}, email=${emailStatus}`, 'info');
    } catch (e) {
      addLog('Status load error: ' + e.message, 'err');
    }
  }

  // ─── NOTIFICATIONS ──────────────────────────────────────────
  let _notifCount = 0;

  async function loadNotifications() {
    try {
      const res = await fetch('/api/admin?action=stats', { headers: authHeaders() });
      if (res.status === 401) return;
      const data = await res.json();
      if (!data.ok) return;

      // Use new_today as notification count
      _notifCount = data.new_today || 0;
      const badge = document.getElementById('notifBadge');
      const btn   = document.getElementById('notifBtn');
      if (badge) {
        badge.textContent = _notifCount > 99 ? '99+' : String(_notifCount);
        badge.hidden      = _notifCount === 0;
      }
      if (btn) btn.title = _notifCount > 0 ? `${_notifCount} new subscriber${_notifCount > 1 ? 's' : ''} today` : 'No new subscribers today';

      const list = document.getElementById('notifList');
      if (list) {
        if (_notifCount === 0) {
          list.innerHTML = '<div class="notif-empty">No new subscribers today.</div>';
        } else if (data.last_subscriber) {
          const s = data.last_subscriber;
          const when = s.created_at ? new Date(s.created_at).toLocaleString() : '';
          list.innerHTML = `<div class="notif-item">
            <span class="notif-email">${esc(s.email || '')}</span>
            <span class="notif-meta">Latest · ${when}</span>
          </div><div class="notif-item"><span class="notif-meta">${_notifCount} new subscriber${_notifCount > 1 ? 's' : ''} today total</span></div>`;
        }
      }
    } catch (_) {}
  }

  function toggleNotifPanel() {
    const panel = document.getElementById('notifPanel');
    if (panel) panel.hidden = !panel.hidden;
  }

  function markNotificationsSeen() {
    _notifCount = 0;
    const badge = document.getElementById('notifBadge');
    if (badge) badge.hidden = true;
    const list = document.getElementById('notifList');
    if (list) list.innerHTML = '<div class="notif-empty">All caught up.</div>';
    const panel = document.getElementById('notifPanel');
    if (panel) panel.hidden = true;
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

  // ─── ACTION LOG UTILITY ─────────────────────────────────────
  async function logAction(actionName, status, details = {}) {
    try {
      await fetch('/api/admin?action=log', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          action_name: actionName,
          action_type: details.type || 'admin',
          status,
          request_payload:  details.request  || null,
          response_payload: details.response || null,
          error_message:    details.error    || null,
        }),
      });
    } catch (e) {
      console.warn('logAction failed:', e.message);
    }
  }

  // ─── LOAD ACTION LOGS ───────────────────────────────────────
  async function loadActionLogs() {
    const panel = document.getElementById('actionLogsPanel');
    if (!panel) return;
    panel.innerHTML = '<div style="color:var(--text-dim);font-size:0.8rem;padding:8px 0;">Loading…</div>';
    try {
      const res = await fetch('/api/admin?action=logs', { headers: authHeaders() });
      const data = await res.json();
      if (!data.ok || !data.logs?.length) {
        panel.innerHTML = '<div style="color:var(--text-dim);font-size:0.8rem;padding:8px 0;">No action logs yet.</div>';
        return;
      }
      panel.innerHTML = data.logs.map(l => {
        const ts = l.created_at ? new Date(l.created_at).toLocaleString() : '';
        const cls = l.status === 'success' ? 'ok' : l.status === 'error' ? 'err' : 'info';
        return `<div class="log-line ${cls}">[${ts}] ${esc(l.action_name)} — ${esc(l.status)}${l.error_message ? ' | ' + esc(l.error_message) : ''}</div>`;
      }).join('');
    } catch (e) {
      panel.innerHTML = `<div style="color:var(--danger);font-size:0.8rem;">Failed to load logs: ${esc(e.message)}</div>`;
    }
  }

  // ─── TEST SUBSCRIBE ─────────────────────────────────────────
  async function testSubscribeAdminEmail() {
    const email = 'heyypuneet@gmail.com';
    addLog(`Test subscribe: ${email}…`, 'info');
    await logAction('test_subscribe', 'started', { request: { email } });

    // Get before count
    let beforeCount = '?';
    try {
      const sr = await fetch('/api/stats?t=' + Date.now(), { cache: 'no-store' });
      const sd = await sr.json();
      beforeCount = sd.total_subscribers ?? '?';
    } catch (_) {}

    try {
      const res = await fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: 'admin_test' }),
      });
      const data = await res.json();
      addLog(`Subscribe response: ok=${data.ok} status=${data.status||''} msg=${data.message||data.error||''}`, data.ok ? 'ok' : 'err');

      // Refetch stats
      let afterCount = '?';
      try {
        await new Promise(r => setTimeout(r, 600));
        const sr2 = await fetch('/api/stats?t=' + Date.now(), { cache: 'no-store' });
        const sd2 = await sr2.json();
        afterCount = sd2.total_subscribers ?? '?';
      } catch (_) {}

      addLog(`Subscriber count: before=${beforeCount} after=${afterCount}`, 'info');
      await logAction('test_subscribe', data.ok ? 'success' : 'error', {
        request: { email },
        response: { ok: data.ok, status: data.status, message: data.message },
        error: data.ok ? null : (data.error || data.message),
      });
    } catch (e) {
      addLog('Test subscribe error: ' + e.message, 'err');
      await logAction('test_subscribe', 'error', { error: e.message });
    }
  }
  window.testSubscribeAdminEmail = testSubscribeAdminEmail;

  // ─── DEMO REFRESH ───────────────────────────────────────────
  async function simulateDemoRefresh() {
    addLog('Simulate demo refresh…', 'info');
    await logAction('demo_refresh', 'started');
    try {
      const res = await fetch('/api/admin?action=demo_refresh', {
        method: 'POST', headers: authHeaders(),
      });
      const data = await res.json();
      if (data.ok) {
        addLog(`✓ Demo refresh: ${data.message}`, 'ok');
        await logAction('demo_refresh', 'success', { response: data });
      } else {
        addLog(`Demo refresh: ${data.error}`, data.mode === 'production' ? 'warn' : 'err');
        if (data.mode === 'production') addLog('Use Trigger Production Refresh to dispatch GitHub Actions.', 'info');
        await logAction('demo_refresh', 'error', { error: data.error });
      }
    } catch (e) {
      addLog('Demo refresh error: ' + e.message, 'err');
      await logAction('demo_refresh', 'error', { error: e.message });
    }
  }
  window.simulateDemoRefresh = simulateDemoRefresh;

  // ─── CHECK TODAY'S ISSUE ─────────────────────────────────────
  async function checkTodayIssue() {
    addLog('Checking today\'s issue…', 'info');
    await logAction('check_today_issue', 'started');
    try {
      const res = await fetch('/api/admin?action=status', { headers: authHeaders() });
      const data = await res.json();
      if (data.ok) {
        const today = data.today || '';
        const exists = data.today_exists;
        addLog(`Today (IST): ${today} | exists: ${exists ? '✓' : '✗'}`, exists ? 'ok' : 'warn');
        const gs = data.generation_status || {};
        addLog(`Gen status: ${gs.generation_status || gs.status || '?'} | sections: ${gs.sections_complete || '?'}`, 'info');
        await logAction('check_today_issue', 'success', { response: { today, exists } });
      } else {
        addLog('Status check failed: ' + (data.message || 'unknown'), 'err');
        await logAction('check_today_issue', 'error', { error: data.message });
      }
    } catch (e) {
      addLog('Check error: ' + e.message, 'err');
      await logAction('check_today_issue', 'error', { error: e.message });
    }
  }
  window.checkTodayIssue = checkTodayIssue;

  // ─── CHECK PRODUCTION JSON ───────────────────────────────────
  async function checkProductionJson() {
    addLog('Checking production JSON…', 'info');
    await logAction('check_production_json', 'started');
    try {
      const res = await fetch('/api/admin?action=status', { headers: authHeaders() });
      const data = await res.json();
      const today = data.today || new Date().toISOString().split('T')[0];
      const baseUrl = window.location.origin;
      const url = `${baseUrl}/data/issues/${today}.json`;
      addLog(`Fetching: ${url}`, 'info');
      const r2 = await fetch(url + '?t=' + Date.now(), { cache: 'no-store' });
      if (r2.ok) {
        const issue = await r2.json();
        addLog(`✓ Production JSON live: sections=${issue.total_sections} items=${issue.total_dashboard_items}`, 'ok');
        await logAction('check_production_json', 'success', { response: { url, sections: issue.total_sections } });
      } else {
        addLog(`✗ Production JSON not available (HTTP ${r2.status}): ${url}`, 'err');
        await logAction('check_production_json', 'error', { error: `HTTP ${r2.status}` });
      }
    } catch (e) {
      addLog('Production JSON check error: ' + e.message, 'err');
      await logAction('check_production_json', 'error', { error: e.message });
    }
  }
  window.checkProductionJson = checkProductionJson;

  async function checkLatestJson() {
    addLog('Checking latest available JSON…', 'info');
    await logAction('check_latest_json', 'started');
    try {
      const datesRes = await fetch('/data/dates.json?t=' + Date.now(), { cache: 'no-store' });
      if (!datesRes.ok) {
        addLog(`✗ dates.json unavailable (HTTP ${datesRes.status})`, 'err');
        await logAction('check_latest_json', 'error', { error: `dates HTTP ${datesRes.status}` });
        return;
      }
      const datesData = await datesRes.json();
      const latest = (datesData.dates || [])[0];
      if (!latest) {
        addLog('✗ No latest date found in dates.json.', 'err');
        await logAction('check_latest_json', 'error', { error: 'empty dates.json' });
        return;
      }
      const url = `/data/issues/${latest}.json`;
      addLog(`Fetching: ${url}`, 'info');
      const issueRes = await fetch(url + '?t=' + Date.now(), { cache: 'no-store' });
      if (!issueRes.ok) {
        addLog(`✗ Latest JSON not available (HTTP ${issueRes.status}): ${url}`, 'err');
        await logAction('check_latest_json', 'error', { error: `HTTP ${issueRes.status}` });
        return;
      }
      const issue = await issueRes.json();
      const isDemo = issue._demo === true || /demo fallback/i.test(issue.title || issue.subject || '');
      addLog(`✓ Latest JSON live: ${latest} sections=${issue.total_sections} items=${issue.total_dashboard_items}${isDemo ? ' | demo fallback' : ''}`, isDemo ? 'warn' : 'ok');
      await logAction('check_latest_json', 'success', { response: { latest, sections: issue.total_sections, demo: isDemo } });
    } catch (e) {
      addLog('Latest JSON check error: ' + e.message, 'err');
      await logAction('check_latest_json', 'error', { error: e.message });
    }
  }
  window.checkLatestJson = checkLatestJson;

  // ─── REFRESH PUBLIC STATS ────────────────────────────────────
  async function refreshPublicStats() {
    addLog('Refreshing public stats…', 'info');
    await logAction('refresh_public_stats', 'started');
    try {
      const res = await fetch('/api/stats?t=' + Date.now(), { cache: 'no-store' });
      const data = await res.json();
      addLog(`Stats: page_views=${data.total_page_views ?? data.total_visits ?? '?'} subscribers=${data.total_subscribers ?? '?'} unique_today=${data.unique_visitors_today ?? '?'}`, 'ok');
      await logAction('refresh_public_stats', 'success', { response: data });
    } catch (e) {
      addLog('Stats error: ' + e.message, 'err');
      await logAction('refresh_public_stats', 'error', { error: e.message });
    }
  }
  window.refreshPublicStats = refreshPublicStats;

  // ─── TRIGGER ────────────────────────────────────────────────
  async function trigger(mode, force) {
    addLog(`Triggering: mode=${mode}${force ? ' (force)' : ''}…`, 'info');
    try {
      const res = await fetch('/api/admin?action=trigger', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ mode, force: !!force }),
      });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      if (data.ok) {
        addLog(`✓ ${data.message}`, 'ok');
        addLog(data.note || 'Workflow dispatched. Check GitHub Actions run result.', 'info');
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
      const res = await fetch('/api/admin?action=trigger', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ mode: 'test_email', test_email: email }),
      });
      const data = await res.json();
      addLog(data.ok ? `✓ ${data.message}` : `✗ ${data.message}`, data.ok ? 'ok' : 'err');
      if (data.note) addLog(data.note, 'info');
    } catch (e) {
      addLog('Test email error: ' + e.message, 'err');
    }
  }

  async function refreshIndex() {
    addLog('Refreshing archive index…', 'info');
    try {
      const res = await fetch('/api/admin?action=trigger', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ mode: 'refresh_index' }),
      });
      const data = await res.json().catch(() => ({}));
      addLog(data.ok ? `✓ ${data.message}` : `✗ ${data.message || 'Index refresh trigger failed'}`, data.ok ? 'ok' : 'err');
      if (data.note) addLog(data.note, 'info');
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
    title.textContent = "Send Today's Newsletter?";
    msgEl.textContent = 'This will send today\'s issue to ALL active subscribers. Duplicate sends are prevented. Today\'s issue must be complete and live on production.';
    okBtn.onclick = async () => {
      closeConfirm();
      addLog("Triggering today's live send (send_live_today)…", 'warn');
      try {
        const res = await fetch('/api/admin?action=trigger', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ mode: 'send_live_today', confirm_live_send: true }),
        });
        const data = await res.json();
        addLog(data.ok ? `✓ ${data.message}` : `✗ ${data.message}`, data.ok ? 'ok' : 'err');
        if (data.ok) setTimeout(loadStatus, 5000);
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

    let url = '/api/admin?action=subscribers';
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

  function refreshAdminPanel() {
    loadAdminStats();
    loadNotifications();
    loadStatus();
    const el = document.getElementById('adminLastRefreshed');
    if (el) el.textContent = 'Last refreshed at ' + new Date().toLocaleTimeString();
  }

  function startAdminAutoRefresh() {
    if (adminRefreshTimer) return;
    adminRefreshTimer = window.setInterval(refreshAdminPanel, ADMIN_REFRESH_INTERVAL_MS);
  }

  window.addEventListener('beforeunload', () => {
    if (adminRefreshTimer) window.clearInterval(adminRefreshTimer);
  });

  // ─── INIT ───────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    refreshAdminPanel();
    startAdminAutoRefresh();
    loadActionLogs();
  });
  window.loadActionLogs = loadActionLogs;
})();
