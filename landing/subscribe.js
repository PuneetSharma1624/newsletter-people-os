/* PeopleOS Brief — subscribe form handler + reader count */
(function () {
  'use strict';

  const form       = document.getElementById('subscribeForm');
  const emailInput = document.getElementById('emailInput');
  const submitBtn  = document.getElementById('submitBtn');
  const btnText    = document.getElementById('btnText');
  const btnLoader  = document.getElementById('btnLoader');
  const formMessage= document.getElementById('formMessage');

  if (!form) return;

  // ─── READER COUNT ────────────────────────────────────────────
  async function loadReaderCount() {
    try {
      const res = await fetch('/api/public/stats?t=' + Date.now(), { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      if (data.ok) {
        const n = data.total_subscribers || 0;
        if (n > 0) setReaderCount(n);
        const sEl = document.getElementById('kpiSubscribersVal');
        if (sEl) sEl.textContent = n.toLocaleString();
      }
    } catch (_) {}
  }

  function setReaderCount(n) {
    const el = document.getElementById('readerCountLine');
    if (el) el.textContent = `Join ${n.toLocaleString()} readers getting the executive cut every morning.`;
  }

  loadReaderCount();

  // ─── FORM STATE ──────────────────────────────────────────────
  let _submitting = false;

  function setLoading(on) {
    _submitting = on;
    submitBtn.disabled  = on;
    emailInput.disabled = on;
    if (btnText) {
      btnText.style.display = on ? 'none' : '';
    }
    if (btnLoader) {
      // Remove hidden attr if present — use only style.display for control
      if (on) {
        btnLoader.removeAttribute('hidden');
        btnLoader.style.display = 'inline-block';
      } else {
        btnLoader.style.display = 'none';
      }
    }
  }

  function showMessage(text, type) {
    if (!formMessage) return;
    formMessage.textContent = text;
    formMessage.className   = 'form-message ' + type;
  }

  function clearMessage() {
    if (!formMessage) return;
    formMessage.textContent = '';
    formMessage.className   = 'form-message';
  }

  // ─── SUBMIT ──────────────────────────────────────────────────
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (_submitting) return; // prevent double submit

    clearMessage();

    const email = (emailInput.value || '').trim();
    if (!email) {
      showMessage('Please enter your email address.', 'error');
      emailInput.focus();
      return;
    }
    // Basic email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
      showMessage('Please enter a valid email address.', 'error');
      emailInput.focus();
      return;
    }

    setLoading(true);

    let succeeded = false;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

    try {
      const res = await fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: 'dashboard' }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      let data;
      try { data = await res.json(); }
      catch (_) { data = null; }

      if (data && data.ok) {
        showMessage(data.message || "You're subscribed!", 'success');
        emailInput.value = '';
        succeeded = true;
        if (btnText) { btnText.style.display = ''; btnText.textContent = 'Subscribed ✓'; }
        if (btnLoader) btnLoader.style.display = 'none';
        submitBtn.disabled = true;
        setTimeout(loadReaderCount, 800);
      } else if (data && (data.error || data.message)) {
        showMessage(data.error || data.message, 'error');
      } else if (!res.ok) {
        showMessage('Subscription failed (server error). Please try again.', 'error');
      } else {
        showMessage('Something went wrong. Please try again.', 'error');
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        showMessage('Request timed out. Please check your connection and try again.', 'error');
      } else {
        showMessage('Cannot reach server. Please check your connection.', 'error');
      }
    } finally {
      if (!succeeded) setLoading(false);
    }
  });
})();
