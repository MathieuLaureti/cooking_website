importScripts('import-status.js');

const BADGE_COLOR = '#FFA500';

async function refreshBadge() {
  const stored = await chrome.storage.local.get(['siteBase', 'token']);
  if (!stored.token || !stored.siteBase) {
    await chrome.action.setBadgeText({ text: '' });
    return;
  }
  try {
    const result = await fetchRecipeImports(stored.siteBase, stored.token);
    if (result.error) {
      await chrome.action.setBadgeText({ text: '' });
      return;
    }
    const count = activeImportCount(result.rows);
    await chrome.action.setBadgeBackgroundColor({ color: BADGE_COLOR });
    await chrome.action.setBadgeText({ text: count > 0 ? String(count) : '' });
  } catch {
    await chrome.action.setBadgeText({ text: '' });
  }
}

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === 'refreshImportStatus') {
    refreshBadge();
  }
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'importPoll') {
    refreshBadge();
  }
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create('importPoll', { periodInMinutes: 1 });
  refreshBadge();
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && (changes.token || changes.siteBase)) {
    refreshBadge();
  }
});

refreshBadge();
