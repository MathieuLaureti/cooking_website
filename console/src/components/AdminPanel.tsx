import React, { useCallback, useEffect, useState } from 'react';
import { apiClient } from '../api/client';

const AdminPanel: React.FC = () => {
  const [code, setCode] = useState('');
  const [expiresIn, setExpiresIn] = useState(0);
  const [expanded, setExpanded] = useState(false);

  const fetchCode = useCallback(async () => {
    try {
      const res = await apiClient.get('/api/auth/registration-code');
      setCode(res.data.code);
      setExpiresIn(res.data.expires_in_seconds);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (!expanded) return;
    fetchCode();
    const interval = setInterval(fetchCode, 30000);
    return () => clearInterval(interval);
  }, [expanded, fetchCode]);

  useEffect(() => {
    if (!expanded || expiresIn <= 0) return;
    const timer = setInterval(() => {
      setExpiresIn((prev) => {
        if (prev <= 1) {
          fetchCode();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [expanded, expiresIn, fetchCode]);

  return (
    <div className="bg-[#374239] rounded border border-white/5 mb-4">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-2 px-4 text-[10px] uppercase tracking-[0.2em] text-[#5E7161] font-bold hover:text-[#FFA500] transition-colors"
      >
        <span>Admin — Registration Code</span>
        <span>{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
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
