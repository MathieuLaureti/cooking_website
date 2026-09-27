import { useCallback, useEffect, useState } from 'react';
import { API_PREFIX, apiClient } from '../api/client';

interface SanityRun {
  id: number;
  status: string;
  use_laya: boolean;
  total_foods: number | null;
  pipeline_layer: string | null;
  layer_current: number | null;
  layer_total: number | null;
  drops_count: number;
  error: string | null;
  progress_label: string | null;
  finished_at: string | null;
}

const ACTIVE = new Set(['queued', 'running']);

const CatalogSanityPanel: React.FC = () => {
  const [runs, setRuns] = useState<SanityRun[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    return apiClient.get<SanityRun[]>(`${API_PREFIX}/catalog_sanity/runs`)
      .then(res => {
        setRuns(res.data);
        setError('');
      })
      .catch(() => setError('Could not load catalog sanity runs'));
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [load]);

  const active = runs.find(row => ACTIVE.has(row.status));
  const latestDone = runs.find(row => row.status === 'completed' || row.status === 'failed');

  const start = (useLaya: boolean) => {
    if (busy || active) return;
    setBusy(true);
    apiClient.post(`${API_PREFIX}/catalog_sanity/runs`, { use_laya: useLaya })
      .then(() => load())
      .catch((err: { response?: { status?: number } }) => {
        if (err.response?.status === 409) {
          setError('A run is already queued or running');
        } else {
          setError('Could not start catalog sanity run');
        }
      })
      .finally(() => setBusy(false));
  };

  const display = active ?? latestDone;

  return (
    <div className="bg-[#374239] rounded shadow-xl flex flex-col p-4">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="text-[10px] uppercase tracking-[0.2em] text-[#FFA500] font-bold">CNF catalog sanity</h2>
        <span
          className={`text-[10px] uppercase tracking-widest ${
            active ? 'text-[#FFA500] font-bold' : 'text-[#5E7161]'
          }`}
        >
          {active ? (active.status === 'queued' ? 'queued' : 'running') : 'idle'}
        </span>
      </div>
      {error && <p className="text-sm text-red-300 mb-2">{error}</p>}
      <div className="flex flex-wrap gap-2 mb-3">
        <button
          type="button"
          disabled={busy || !!active}
          onClick={() => start(false)}
          className="px-3 py-2 rounded bg-black/30 text-[#FFA500] text-xs font-bold uppercase tracking-widest disabled:opacity-40"
        >
          Rules only
        </button>
        <button
          type="button"
          disabled={busy || !!active}
          onClick={() => start(true)}
          className="px-3 py-2 rounded bg-[#FFA500] text-black text-xs font-bold uppercase tracking-widest disabled:opacity-40"
        >
          With Laya (overnight)
        </button>
      </div>
      {!display && !error && (
        <p className="text-sm text-slate-400">No runs yet. Start a preview to list CNF rows that would be hidden.</p>
      )}
      {display && (
        <div className="text-sm space-y-1">
          <p className="text-slate-300">
            Run #{display.id}
            {display.use_laya ? ' · Laya on' : ' · rules only'}
          </p>
          {display.progress_label && (
            <p className="text-lg font-bold text-[#FFA500]">{display.progress_label}</p>
          )}
          {display.total_foods != null && (
            <p className="text-[10px] uppercase tracking-widest text-[#5E7161]">
              {display.drops_count} drops
              {display.status === 'completed' || display.status === 'failed'
                ? ` · ${display.total_foods} CNF foods scanned`
                : ''}
            </p>
          )}
          {display.status === 'failed' && display.error && (
            <p className="text-sm text-red-300">{display.error}</p>
          )}
          {display.status === 'completed' && (
            <p className="text-xs text-slate-400">
              Finished. Full drop list is stored on the run (API GET /catalog_sanity/runs/{display.id}).
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default CatalogSanityPanel;
