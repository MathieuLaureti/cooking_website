import React, { useEffect, useState } from 'react';
import { API_PREFIX, apiClient } from '../api/client';

async function fetchRegistrationCode(): Promise<{ code: string; expiresIn: number } | null> {
  try {
    const res = await apiClient.get(`${API_PREFIX}/auth/registration-code`);
    return { code: res.data.code, expiresIn: res.data.expires_in_seconds };
  } catch {
    return null;
  }
}

const AdminPanel: React.FC<{ embedded?: boolean }> = ({ embedded = false }) => {
  const [code, setCode] = useState('');
  const [expiresIn, setExpiresIn] = useState(0);
  const [expanded, setExpanded] = useState(embedded);

  useEffect(() => {
    if (!expanded && !embedded) return;
    let alive = true;
    const load = async () => {
      const data = await fetchRegistrationCode();
      if (!alive || !data) return;
      setCode(data.code);
      setExpiresIn(data.expiresIn);
    };
    void load();
    const interval = setInterval(() => void load(), 30000);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [expanded, embedded]);

  useEffect(() => {
    if (!expanded || expiresIn <= 0) return;
    const timer = setInterval(() => {
      setExpiresIn((prev) => {
        if (prev <= 1) {
          void fetchRegistrationCode().then((data) => {
            if (!data) return;
            setCode(data.code);
            setExpiresIn(data.expiresIn);
          });
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [expanded, expiresIn]);

  return (
    <div className="bg-[#374239] rounded border border-white/5 mb-4">
      {!embedded && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center justify-between p-2 px-4 text-[10px] uppercase tracking-[0.2em] text-[#5E7161] font-bold hover:text-[#FFA500] transition-colors"
        >
          <span>Admin — Registration Code</span>
          <span>{expanded ? '▲' : '▼'}</span>
        </button>
      )}

      {(expanded || embedded) && (
        <div className="px-4 pb-4 border-t border-white/5 pt-4">
          <p className="text-[9px] uppercase tracking-widest text-[#5E7161] font-bold mb-2">
            Share this code to register new users
          </p>
          <p className="text-4xl font-mono font-black tracking-[0.2em] text-[#FFA500] text-center py-2">
            {code || '·······'}
          </p>
          <p className="text-[9px] uppercase tracking-widest text-[#5E7161] text-center">
            Refreshes in {expiresIn}s
          </p>
        </div>
      )}
    </div>
  );
};

export default AdminPanel;
