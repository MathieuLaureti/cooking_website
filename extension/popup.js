const status = document.getElementById('status');
const queueHint = document.getElementById('queue-hint');
let pollTimer = null;
let currentTabUrl = null;

function setStatusText(text, { busy = false } = {}) {
  status.textContent = text;
  status.classList.toggle('busy', busy);
}

function setQueueHint(rows) {
  const n = activeImportCount(rows);
  if (n === 0) {
    queueHint.textContent = '';
    return;
  }
  queueHint.textContent = n === 1 ? '1 import in progress' : `${n} imports in progress`;
}

async function refreshStatus() {
  const stored = await chrome.storage.local.get(['siteBase', 'token']);
  if (!stored.token || !stored.siteBase) {
    setQueueHint([]);
    return;
  }
  const result = await fetchRecipeImports(stored.siteBase, stored.token);
  if (result.error === 'auth') {
    setQueueHint([]);
    return;
  }
  if (result.error) {
    return;
  }
  setQueueHint(result.rows);
  if (!currentTabUrl) {
    return;
  }
  const row = findImportForUrl(result.rows, currentTabUrl);
  if (!row) {
    return;
  }
  const busy = row.status === 'queued' || row.status === 'running';
  setStatusText(importStatusMessage(row), { busy });
}

function startPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  pollTimer = setInterval(refreshStatus, 3000);
}

function notifyBackground() {
  chrome.runtime.sendMessage({ type: 'refreshImportStatus' }).catch(() => {});
}

document.getElementById('add').addEventListener('click', async () => {
  const stored = await chrome.storage.local.get(['siteBase', 'token']);
  if (!stored.token || !stored.siteBase) {
    status.textContent = '';
    status.classList.remove('busy');
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
    setStatusText('This tab has no page URL');
    return;
  }
  currentTabUrl = tab.url;
  setStatusText('Sending…', { busy: true });
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
      setStatusText('Sign in again from the extension options');
      return;
    }
    if (!response.ok) {
      setStatusText(body.detail || 'Could not queue that page');
      return;
    }
    if (body.status === 'queued' || body.status === 'running') {
      setStatusText(importStatusMessage(body), { busy: true });
    } else if (body.status === 'ready') {
      setStatusText('Ready — review in admin');
    } else {
      setStatusText(`Already ${body.status}`);
    }
    notifyBackground();
    await refreshStatus();
  } catch {
    setStatusText('Could not reach the site');
  }
});

chrome.tabs.query({ active: true, currentWindow: true }).then(([tab]) => {
  if (tab?.url && /^https?:\/\//.test(tab.url)) {
    currentTabUrl = tab.url;
  }
  refreshStatus();
  startPolling();
});

window.addEventListener('unload', () => {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
});
