import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface LoginProps {
  onShowRegister: () => void;
}

const Login: React.FC<LoginProps> = ({ onShowRegister }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
    } catch {
      setError('Could not sign in. Check your credentials or try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#4A594D] flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="bg-[#374239] w-full max-w-sm p-8 rounded shadow-2xl border border-white/5 text-[#F7F5F2]"
      >
        <h1 className="text-2xl font-black uppercase italic mb-2">Cooking Console</h1>
        <p className="text-[10px] uppercase tracking-[0.2em] text-[#5E7161] font-bold mb-8">Sign in to continue</p>

        {error && (
          <p className="text-red-400 text-xs mb-4 uppercase tracking-wider">{error}</p>
        )}

        <input
          autoFocus
          className="w-full bg-[#4A594D] p-3 mb-4 outline-none border-b border-[#5E7161] focus:border-[#FFA500] text-sm"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          className="w-full bg-[#4A594D] p-3 mb-6 outline-none border-b border-[#5E7161] focus:border-[#FFA500] text-sm"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          type="submit"
          disabled={loading || !username || !password}
          className="w-full bg-[#FFA500] text-black py-3 font-black uppercase text-sm hover:bg-[#FFB732] disabled:opacity-40"
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </button>

        <button
          type="button"
          onClick={onShowRegister}
          className="w-full mt-4 text-[10px] uppercase tracking-widest text-[#5E7161] hover:text-[#FFA500] font-bold"
        >
          Register with invite code
        </button>
      </form>
    </div>
  );
};

export default Login;
