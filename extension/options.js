const baseInput = document.getElementById('base');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const status = document.getElementById('status');

function siteBase() {
  return baseInput.value.trim().replace(/\/$/, '');
}

chrome.storage.local.get(['siteBase', 'username'], (stored) => {
  if (stored.siteBase) baseInput.value = stored.siteBase;
  if (stored.username) usernameInput.value = stored.username;
});

document.getElementById('save').addEventListener('click', async () => {
  const base = siteBase();
  status.textContent = 'Signing in…';
  try {
    const response = await fetch(`${base}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      status.textContent = body.detail || 'Sign-in failed';
      return;
    }
    await chrome.storage.local.set({
      siteBase: base,
      username: body.username,
      token: body.access_token,
    });
    passwordInput.value = '';
    status.textContent = `Signed in as ${body.username}`;
  } catch (err) {
    status.textContent = 'Could not reach the site';
  }
});
