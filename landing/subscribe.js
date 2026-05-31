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

    try {
      const res = await fetch('/api/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const data = await res.json();

      if (data.ok) {
        showMessage(data.message || "You're subscribed!", 'success');
        emailInput.value   = '';
        submitBtn.textContent = '✓ Subscribed';
        submitBtn.disabled = true;
        // Refresh count after successful subscribe
        setTimeout(loadReaderCount, 800);
      } else {
        showMessage(data.message || 'Something went wrong. Please try again.', 'error');
        setLoading(false);
      }
    } catch (err) {
      showMessage('Network error. Please check your connection and try again.', 'error');
      setLoading(false);
    }
  });
})();
