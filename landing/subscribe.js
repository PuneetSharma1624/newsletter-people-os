/* PeopleOS Brief - subscribe form handler + live reader count */
(function () {
  'use strict';

  const form        = document.getElementById('subscribeForm');
  const emailInput  = document.getElementById('emailInput');
  const submitBtn   = document.getElementById('submitBtn');
  const btnText     = document.getElementById('btnText');
  const btnLoader   = document.getElementById('btnLoader');
  const formMessage = document.getElementById('formMessage');

  if (!form) return;

  function setReaderCount(n) {
    const el = document.getElementById('readerCountLine');
    if (el) el.textContent = `Join ${n.toLocaleString()} readers getting the executive cut every morning.`;
  }

  function updateLiveCounters(data) {
    const pv = data.total_page_views ?? data.total_visits ?? 0;
    const uv = data.unique_visitors_today ?? 0;
    const sb = data.total_subscribers ?? 0;
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setEl('kpiVisitorsVal', pv.toLocaleString());
    setEl('kpiPageViewsVal', `${pv.toLocaleString()} total · ${uv.toLocaleString()} today`);
    setEl('kpiSubscribersVal', sb.toLocaleString());
    setEl('kpiUniqueVisitorsVal', `${sb.toLocaleString()} morning brief readers`);
    setReaderCount(sb);
  }

  async function loadReaderCount() {
    try {
      const res = await fetch('/api/stats?t=' + Date.now(), { cache: 'no-store' });
      const data = res.ok ? await res.json().catch(() => null) : null;
      if (data && data.ok) updateLiveCounters(data);
    } catch (err) {
      console.warn('PeopleOS stats refresh failed:', err);
    }
  }

  let submitting = false;

  function setLoading(on) {
    submitting = on;
    submitBtn.disabled = on;
    emailInput.disabled = on;
    if (btnText) btnText.style.display = on ? 'none' : '';
    if (btnLoader) {
      btnLoader.removeAttribute('hidden');
      btnLoader.style.display = on ? 'inline-block' : 'none';
    }
  }

  function showMessage(text, type) {
    if (!formMessage) return;
    formMessage.textContent = text;
    formMessage.className = 'form-message ' + type;
  }

  function clearMessage() {
    if (!formMessage) return;
    formMessage.textContent = '';
    formMessage.className = 'form-message';
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (submitting) return;

    clearMessage();

    const email = (emailInput.value || '').trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
      showMessage('Please enter a valid email address.', 'error');
      emailInput.focus();
      return;
    }

    setLoading(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);

    try {
      const res = await fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: 'dashboard' }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      const data = await res.json().catch(() => null);
      if (data && data.ok) {
        const status = data.status === 'already_subscribed' ? 'You are already subscribed.' : "You're subscribed!";
        showMessage(data.message || status, 'success');
        emailInput.value = '';
        if (btnText) btnText.textContent = 'Subscribed';
        await loadReaderCount();
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
      setLoading(false);
    }
  });

  loadReaderCount();
})();
