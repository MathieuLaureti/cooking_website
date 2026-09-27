import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { API_PREFIX, apiClient } from '../api/client';
import AdminPanel from './AdminPanel';

interface Candidate {
  food_id: number;
  name_en: string;
  name_fr: string;
  probability: number | null;
}

interface Review {
  id: number;
  query: string;
  confidence: number | null;
  candidates: Candidate[];
}

interface ImportIngredient {
  name: string;
  quantity: string;
  unit: string;
}

interface ImportComponent {
  name: string;
  ingredients: ImportIngredient[];
  instructions: { step: number; text: string }[];
}

interface ImportExtract {
  name: string;
  dish_name: string;
  components: ImportComponent[];
}

interface UrlImport {
  id: number;
  url: string;
  status: string;
  extract: ImportExtract | null;
  error: string | null;
  pipeline_step: number | null;
  pipeline_label: string | null;
  ai_next_attempt_at: string | null;
}

function stepLine(row: UrlImport): string | null {
  if (row.pipeline_step == null || row.pipeline_label == null) {
    return null;
  }
  return `${row.pipeline_step}/3 ${row.pipeline_label}`;
}

function formatRetryAt(iso: string | null): string | null {
  if (!iso) {
    return null;
  }
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) {
    return null;
  }
  return when.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

const UrlImportQueue: React.FC = () => {
  const [rows, setRows] = useState<UrlImport[]>([]);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    apiClient.get<UrlImport[]>(`${API_PREFIX}/recipe_imports`)
      .then(res => {
        setRows(res.data);
        setError('');
      })
      .catch(() => setError('Could not load URL imports'));
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [load]);

  const drop = (id: number) => setRows(prev => prev.filter(row => row.id !== id));

  const act = (id: number, action: 'keep' | 'discard') => {
    apiClient.post(`${API_PREFIX}/recipe_imports/${id}/${action}`)
      .then(() => drop(id))
      .catch(() => setError(action === 'keep' ? 'Could not keep that recipe' : 'Could not discard that import'));
  };

  const retry = (id: number) => {
    apiClient.post(`${API_PREFIX}/recipe_imports/${id}/retry`)
      .then(() => load())
      .catch(() => setError('Could not retry that import'));
  };

  const activeRows = rows.filter(row =>
    row.status === 'queued' || row.status === 'running' || row.status === 'ai_wait'
  );
  const running = activeRows.find(row => row.status === 'running');
  const waitingAi = activeRows.filter(row => row.status === 'ai_wait');
  const queuedRows = activeRows.filter(row => row.status === 'queued');
  const card = rows.find(row => row.status === 'ready') ?? rows.find(row => row.status === 'failed');
  const recipe = card?.extract;

  return (
    <div className="bg-[#374239] rounded shadow-xl flex flex-col p-4">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="text-[10px] uppercase tracking-[0.2em] text-[#FFA500] font-bold">URL imports</h2>
        <span
          className={`text-[10px] uppercase tracking-widest ${
            activeRows.length > 0 ? 'text-[#FFA500] font-bold' : 'text-[#5E7161]'
          }`}
        >
          {activeRows.length > 0 ? `${activeRows.length} in progress` : 'idle'}
        </span>
      </div>
      {error && <p className="text-sm text-red-300 mb-2">{error}</p>}
      {activeRows.length > 0 && (
        <div className="mb-3 rounded bg-black/25 p-3 border border-[#FFA500]/25">
          {running && (
            <div className="mb-2">
              <p className="text-[10px] uppercase tracking-widest text-[#FFA500] font-bold flex items-center gap-2 mb-1">
                <span className="inline-block w-2 h-2 rounded-full bg-[#FFA500] animate-pulse shrink-0" aria-hidden />
                {stepLine(running) ?? 'Extracting recipe'}
              </p>
              <a href={running.url} className="text-xs text-slate-300 break-all" target="_blank" rel="noreferrer">
                {running.url}
              </a>
            </div>
          )}
          {waitingAi.map(row => (
            <div key={row.id} className={(running ? 'mt-2 pt-2 border-t border-white/5' : 'mb-2')}>
              <p className="text-[10px] uppercase tracking-widest text-[#FFA500] font-bold mb-1">
                {stepLine(row) ?? '3/3 Extraction via AI'}
              </p>
              {row.error && (
                <p className="text-xs text-slate-400 mb-1">Model busy — {row.error.slice(0, 120)}</p>
              )}
              {formatRetryAt(row.ai_next_attempt_at) && (
                <p className="text-xs text-slate-500 mb-1">
                  Retry around {formatRetryAt(row.ai_next_attempt_at)}
                </p>
              )}
              <a href={row.url} className="text-xs text-slate-400 break-all" target="_blank" rel="noreferrer">
                {row.url}
              </a>
            </div>
          ))}
          {queuedRows.map(row => (
            <div key={row.id} className={running || waitingAi.length ? 'mt-2 pt-2 border-t border-white/5' : ''}>
              <p className="text-[10px] uppercase tracking-widest text-[#5E7161] mb-1">
                {stepLine(row) ?? 'Waiting in queue'}
              </p>
              <a href={row.url} className="text-xs text-slate-400 break-all" target="_blank" rel="noreferrer">
                {row.url}
              </a>
            </div>
          ))}
        </div>
      )}
      {!card && activeRows.length === 0 && !error && (
        <p className="text-sm text-slate-400">No recipes waiting. The browser button adds a URL.</p>
      )}
      {card && (
        <div>
          <a href={card.url} className="text-xs text-slate-400 break-all" target="_blank" rel="noreferrer">{card.url}</a>
          {card.status === 'failed' && (
            <p className="text-sm text-red-300 mt-2">{card.error || 'Extraction failed'}</p>
          )}
          {recipe && (
            <div className="mt-3">
              {recipe.dish_name && (
                <p className="text-[10px] uppercase tracking-widest text-[#5E7161]">{recipe.dish_name}</p>
              )}
              <p className="text-lg font-bold mb-3">{recipe.name}</p>
              {recipe.components.map((component, index) => (
                <div key={`${component.name}-${index}`} className="mb-3">
                  {component.name && <p className="text-sm font-bold">{component.name}</p>}
                  <ul className="text-sm text-slate-300">
                    {component.ingredients.map((item, itemIndex) => (
                      <li key={itemIndex}>{item.quantity} {item.unit} {item.name}</li>
                    ))}
                  </ul>
                  <ol className="text-sm list-decimal pl-4">
                    {component.instructions.map(step => (
                      <li key={step.step}>{step.text}</li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2 mt-3">
            {card.status === 'ready' && (
              <button type="button" onClick={() => act(card.id, 'keep')} className="px-3 py-2 rounded bg-[#FFA500] text-black text-xs font-bold uppercase tracking-widest">
                Keep
              </button>
            )}
            {card.status === 'failed' && !recipe && (
              <button type="button" onClick={() => retry(card.id)} className="px-3 py-2 rounded bg-[#FFA500] text-black text-xs font-bold uppercase tracking-widest">
                Retry
              </button>
            )}
            <button type="button" onClick={() => act(card.id, 'discard')} className="px-3 py-2 rounded bg-black/30 text-slate-300 text-xs font-bold uppercase tracking-widest">
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

interface MatchFood {
  id: number;
  name_en: string;
  name_fr: string;
  group_en: string;
}

interface MatchResponse {
  status: 'match' | 'queued' | 'none';
  confidence: number | null;
  match: MatchFood | null;
}

const AdminHome: React.FC<{ onOpenFood: (foodId: number) => void }> = ({ onOpenFood }) => {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [hit, setHit] = useState<MatchFood | null>(null);
  const [focusId, setFocusId] = useState<number | null>(null);

  const load = useCallback(() => {
    return apiClient.get<Review[]>(`${API_PREFIX}/alias_reviews`)
      .then(res => {
        setReviews(res.data);
        setError('');
        return res.data;
      })
      .catch(() => {
        setError('Could not load the waiting list');
        return [] as Review[];
      });
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [load]);

  const checkName = (event: FormEvent) => {
    event.preventDefault();
    const typed = name.trim();
    if (!typed || busy) return;
    setBusy(true);
    setNote('');
    setHit(null);
    apiClient.post<MatchResponse>(`${API_PREFIX}/alias_reviews/match`, { query: typed })
      .then(async res => {
        const data = res.data;
        if (data.status === 'match' && data.match) {
          setHit(data.match);
          setNote(`${typed} → ${data.match.name_en}`);
          setFocusId(null);
        } else if (data.status === 'queued') {
          setNote(`${typed} is in the queue`);
        } else {
          setNote('No catalog food');
          setFocusId(null);
        }
        setName('');
        const rows = await load();
        if (data.status === 'queued') {
          const queued = rows.find(row => row.query.toLowerCase() === typed.toLowerCase());
          setFocusId(queued ? queued.id : null);
        }
      })
      .catch(() => setNote('Could not check that name'))
      .finally(() => setBusy(false));
  };

  const accept = (review: Review, foodId: number) => {
    apiClient.post(`${API_PREFIX}/alias_reviews/${review.id}/accept`, { food_id: foodId })
      .then(() => setReviews(prev => prev.filter(item => item.id !== review.id)))
      .catch(() => setError('Could not save that alias'));
  };

  const current = reviews.find(row => row.id === focusId) ?? reviews[0];

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-3 overflow-y-auto custom-scrollbar">
      <AdminPanel embedded />
      <div className="bg-[#374239] rounded shadow-xl flex flex-col p-4">
        <form onSubmit={checkName} className="flex gap-2 mb-3">
          <input
            value={name}
            onChange={event => setName(event.target.value)}
            placeholder="Ingredient name"
            disabled={busy}
            className="flex-1 min-w-0 bg-black/30 rounded px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={busy || !name.trim()}
            className="px-3 py-2 rounded bg-[#FFA500] text-black text-xs font-bold uppercase tracking-widest disabled:opacity-40"
          >
            {busy ? '…' : 'Check'}
          </button>
        </form>
        {hit ? (
          <button type="button" onClick={() => onOpenFood(hit.id)} className="text-left text-sm text-[#FFA500] mb-3">
            {note}
          </button>
        ) : note ? (
          <p className="text-sm text-slate-300 mb-3">{note}</p>
        ) : null}
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h2 className="text-[10px] uppercase tracking-[0.2em] text-[#FFA500] font-bold">Alias queue</h2>
          <span className="text-[10px] uppercase tracking-widest text-[#5E7161]">{reviews.length} waiting</span>
        </div>
        {error && <p className="text-sm text-red-300 mb-2">{error}</p>}
        {!current && !error && (
          <p className="text-sm text-slate-400">No names waiting.</p>
        )}
        {current && (
          <div>
            <p className="text-lg font-bold">{current.query}</p>
            <p className="text-[10px] uppercase tracking-widest text-[#5E7161] mb-3">
              {current.confidence == null ? 'No score' : `Confidence ${Math.round(current.confidence * 100)}%`}
            </p>
            <div className="space-y-2">
              {current.candidates.map((candidate, index) => (
                <div key={candidate.food_id} className="flex items-start gap-3 border-b border-white/5 pb-2">
                  <button
                    type="button"
                    onClick={() => accept(current, candidate.food_id)}
                    className="w-8 h-8 shrink-0 rounded bg-black/30 text-[#FFA500] font-bold"
                  >
                    {index + 1}
                  </button>
                  <button
                    type="button"
                    onClick={() => onOpenFood(candidate.food_id)}
                    className="text-left min-w-0"
                  >
                    <div>
                      {candidate.name_en}
                      {candidate.probability != null && (
                        <span className="ml-2 text-[10px] uppercase tracking-widest text-[#5E7161]">
                          {Math.round(candidate.probability * 100)}%
                        </span>
                      )}
                    </div>
                    {candidate.name_fr !== candidate.name_en && (
                      <div className="text-xs text-slate-400">{candidate.name_fr}</div>
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <UrlImportQueue />
    </div>
  );
};

export default AdminHome;
