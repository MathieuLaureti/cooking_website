const status = document.getElementById('status');

document.getElementById('add').addEventListener('click', async () => {
  const stored = await chrome.storage.local.get(['siteBase', 'token']);
  if (!stored.token || !stored.siteBase) {
    status.textContent = '';
    const link = document.createElement('a');
    link.href = '#';
    link.textContent = 'Sign in from the extension options';
    link.addEventListener('click', (event) => {
      event.preventDefault();
      chrome.runtime.openOptionsPage();
    });
    status.appendChild(link);
    return;
  }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url || !/^https?:\/\//.test(tab.url)) {
    status.textContent = 'This tab has no page URL';
    return;
  }
  status.textContent = 'Sending…';
  try {
    const response = await fetch(`${stored.siteBase}/api/recipe_imports`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${stored.token}`,
      },
      body: JSON.stringify({ url: tab.url }),
    });
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      status.textContent = 'Sign in again from the extension options';
      return;
    }
    if (!response.ok) {
      status.textContent = body.detail || 'Could not queue that page';
      return;
    }
    status.textContent = body.status === 'queued' ? 'Queued' : `Already ${body.status}`;
  } catch (err) {
    status.textContent = 'Could not reach the site';
  }
});
