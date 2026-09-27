/** Shared helpers for popup + background (importScripts). */

function normalizeImportUrl(raw) {
  try {
    const parsed = new URL(raw.trim());
    if (!/^https?:$/i.test(parsed.protocol)) {
      return raw.trim();
    }
    let path = parsed.pathname.replace(/\/$/, '') || '/';
    return `${parsed.protocol}//${parsed.host.toLowerCase()}${path}${parsed.search}`;
  } catch {
    return raw.trim();
  }
}

function activeImportCount(rows) {
  return rows.filter(
    (row) => row.status === 'queued' || row.status === 'running' || row.status === 'ai_wait'
  ).length;
}

function findImportForUrl(rows, pageUrl) {
  const key = normalizeImportUrl(pageUrl);
  return rows.find((row) => normalizeImportUrl(row.url) === key) || null;
}

function importStatusMessage(row) {
  if (!row) {
    return '';
  }
  switch (row.status) {
    case 'queued':
      return 'Waiting in queue…';
    case 'running':
      return 'Extracting recipe…';
    case 'ai_wait':
      return 'Waiting for AI (model busy)…';
    case 'ready':
      return 'Ready — review in admin';
    case 'failed':
      return row.error ? `Failed: ${row.error}` : 'Extraction failed';
    default:
      return `Status: ${row.status}`;
  }
}

async function fetchRecipeImports(siteBase, token) {
  const response = await fetch(`${siteBase}/api/recipe_imports`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (response.status === 401) {
    return { error: 'auth' };
  }
  if (!response.ok) {
    return { error: 'http' };
  }
  const rows = await response.json();
  return { rows: Array.isArray(rows) ? rows : [] };
}
