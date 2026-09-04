import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface RegisterProps {
  onShowLogin: () => void;
}

const Register: React.FC<RegisterProps> = ({ onShowLogin }) => {
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(username, password, code);
      onShowLogin();
    } catch {
      setError('Registration failed — check code and try again');
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
        <h1 className="text-2xl font-black uppercase italic mb-2">Register</h1>
        <p className="text-[10px] uppercase tracking-[0.2em] text-[#5E7161] font-bold mb-8">
          Enter the 7-digit code from your admin
        </p>

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
          className="w-full bg-[#4A594D] p-3 mb-4 outline-none border-b border-[#5E7161] focus:border-[#FFA500] text-sm"
          placeholder="Password (min 6 chars)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <input
          className="w-full bg-[#4A594D] p-3 mb-6 outline-none border-b border-[#FFA500] text-sm font-mono tracking-[0.3em] text-center"
          placeholder="0000000"
          maxLength={7}
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 7))}
        />

        <button
          type="submit"
          disabled={loading || !username || password.length < 6 || code.length !== 7}
          className="w-full bg-[#FFA500] text-black py-3 font-black uppercase text-sm hover:bg-[#FFB732] disabled:opacity-40"
        >
          {loading ? 'Creating account...' : 'Create Account'}
        </button>

        <button
          type="button"
          onClick={onShowLogin}
          className="w-full mt-4 text-[10px] uppercase tracking-widest text-[#5E7161] hover:text-[#FFA500] font-bold"
        >
          Back to sign in
        </button>
      </form>
    </div>
  );
};

export default Register;
