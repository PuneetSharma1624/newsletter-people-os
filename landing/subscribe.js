/* PeopleOS Brief — subscribe form handler */
(function () {
  'use strict';

  const form = document.getElementById('subscribeForm');
  const emailInput = document.getElementById('emailInput');
  const submitBtn = document.getElementById('submitBtn');
  const btnText = document.getElementById('btnText');
  const btnLoader = document.getElementById('btnLoader');
  const formMessage = document.getElementById('formMessage');

  if (!form) return;

  function setLoading(on) {
    submitBtn.disabled = on;
    emailInput.disabled = on;
    btnText.hidden = on;
    btnLoader.hidden = !on;
  }

  function showMessage(text, type) {
    formMessage.textContent = text;
    formMessage.className = 'form-message ' + type;
  }

  function clearMessage() {
    formMessage.textContent = '';
    formMessage.className = 'form-message';
  }

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
        emailInput.value = '';
        submitBtn.textContent = '✓ Subscribed';
        submitBtn.disabled = true;
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
