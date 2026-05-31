/* PeopleOS Brief — Admin JS
   Handles both the login page and the post-login dashboard.
   Detects which page it's on by checking for #loginForm vs #logBox.
*/
(function () {
  'use strict';

  // ─── LOGIN PAGE ─────────────────────────────────────────────────────────────
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    // Already logged in — skip to dashboard
    if (sessionStorage.getItem('admin_token') || localStorage.getItem('admin_token')) {
      window.location.href = '/admin/dashboard/';
      return;
    }

    loginForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const btn  = document.getElementById('loginBtn');
      const msg  = document.getElementById('msg');
      const tokenVal = (document.getElementById('tokenInput').value || '').trim();

      if (!tokenVal) {
        msg.textContent = 'Token is required.';
        msg.className = 'msg error';
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Checking…';
      msg.textContent = '';
      msg.className = 'msg';

      let data;
      try {
        const res = await fetch('/api/admin/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: tokenVal }),
        });

        // Parse JSON safely — Vercel can return HTML on hard 500s
        try {
          data = await res.json();
        } catch (_) {
          data = { ok: false, success: false, message: `Server error (HTTP ${res.status}). Check Vercel function logs.` };
        }
      } catch (networkErr) {
        // True network failure (offline, DNS, CORS block)
        msg.textContent = 'Cannot reach server: ' + (networkErr.message || 'network error');
        msg.className = 'msg error';
        btn.disabled = false;
        btn.textContent = 'Login';
        return;
      }

      if (data.ok || data.success) {
        // Store session — use both localStorage and sessionStorage for resilience
        sessionStorage.setItem('admin_token', data.session || tokenVal);
        localStorage.setItem('admin_token', data.session || tokenVal);
        window.location.href = '/admin/dashboard/';
      } else {
        msg.textContent = data.message || 'Invalid token.';
        msg.className = 'msg error';
        btn.disabled = false;
        btn.textContent = 'Login';
      }
    });

    return; // Login page done — don't run dashboard code
  }

  // ─── DASHBOARD PAGE ──────────────────────────────────────────────────────────
  const token = sessionStorage.getItem('admin_token') || localStorage.getItem('admin_token');
  if (!token) {
    window.location.href = '/admin/';
    return;
  }

  function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
  }

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
    el.className = 'stat-value' + (cls ? ' ' + cls : '');
  }

  async function loadStatus() {
    try {
      const res = await fetch('/api/admin/status', { headers: authHeaders() });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      if (!data.ok) { addLog('Status load failed: ' + data.message, 'err'); return; }

      setStatEl('statToday', data.today || '—');
      setStatEl('statTodayExists', data.today_exists ? 'Published ✓' : 'Not yet', data.today_exists ? 'ok' : 'warn');
      setStatEl('statLatest', data.latest_date || 'None', data.latest_date ? 'ok' : 'warn');

      const gs = data.generation_status || {};
      const status = gs.status || 'not_started';
      const statusCls = { complete: 'ok', running: 'warn', failed: 'fail', not_started: '' }[status] || '';
      setStatEl('statGenStatus', status, statusCls);
      setStatEl('statCount', data.total_archived || '0');
      setStatEl('statGithub', data.github_configured ? 'Configured ✓' : 'Not configured', data.github_configured ? 'ok' : 'warn');

      const note = document.getElementById('githubNote');
      if (note) note.style.display = data.github_configured ? 'none' : 'block';

      addLog(`Status: today=${data.today_exists ? 'exists' : 'missing'}, generation=${status}`, 'info');
    } catch (e) {
      addLog('Status load error: ' + e.message, 'err');
    }
  }

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
        if (data.fallback) addLog(`Manual steps: ${data.fallback}`, 'warn');
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
      addLog('Index refresh triggered via workflow.', 'info');
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

  // Expose globals for onclick handlers in HTML
  window.trigger        = trigger;
  window.triggerTest    = triggerTest;
  window.refreshIndex   = refreshIndex;
  window.confirmLiveSend = confirmLiveSend;
  window.closeConfirm   = closeConfirm;
  window.logout         = logout;
  window.loadStatus     = loadStatus;

  document.addEventListener('DOMContentLoaded', loadStatus);
})();
