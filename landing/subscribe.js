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
      const res = await fetch('/api/public/stats');
      if (!res.ok) return;
      const data = await res.json();
      if (data.ok && data.total_subscribers > 0) {
        setReaderCount(data.total_subscribers);
      }
    } catch (_) {}
  }

  function setReaderCount(n) {
    const el = document.getElementById('readerCountLine');
    if (el) el.textContent = `Join ${n.toLocaleString()} readers getting the executive cut every morning.`;
  }

  loadReaderCount();

  // ─── FORM STATE ──────────────────────────────────────────────
  function setLoading(on) {
    submitBtn.disabled  = on;
    emailInput.disabled = on;
    if (btnText)   btnText.hidden   = on;
    if (btnLoader) btnLoader.hidden = !on;
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
    clearMessage();

    const email = emailInput.value.trim();
    if (!email) {
      showMessage('Please enter your email address.', 'error');
      emailInput.focus();
      return;
    }

    setLoading(true);

    let succeeded = false;
    try {
      const res = await fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, source: 'dashboard' }),
      });

      let data;
      try { data = await res.json(); }
      catch (_) { data = null; }

      if (data && data.ok) {
        showMessage(data.message || "You're subscribed!", 'success');
        emailInput.value = '';
        submitBtn.textContent = 'Subscribed';
        submitBtn.disabled = true;
        succeeded = true;
        setTimeout(loadReaderCount, 800);
      } else if (data && (data.error || data.message)) {
        showMessage(data.error || data.message, 'error');
      } else if (!res.ok) {
        showMessage('Subscription failed (server error). Please try again.', 'error');
      } else {
        showMessage('Something went wrong. Please try again.', 'error');
      }
    } catch (err) {
      showMessage('Cannot reach server. Please check your connection.', 'error');
    } finally {
      if (!succeeded) setLoading(false);
    }
  });
})();
