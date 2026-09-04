import { useState } from 'react'
import './App.css'
import IngredientMatchChecker from './components/match_checker'
import RecipeManager from "./components/RecipeManager"
import Login from './components/Login'
import Register from './components/Register'
import AdminPanel from './components/AdminPanel'
import { AuthProvider, useAuth } from './context/AuthContext'

function AppContent() {
  const { user, isAdmin, isLoading, logout } = useAuth();
  const [activeComponent, setActiveComponent] = useState<'match' | 'recipe' | null>(null);
  const [authView, setAuthView] = useState<'login' | 'register'>('login');

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#4A594D] flex items-center justify-center text-[#5E7161] text-xs uppercase tracking-widest">
        Loading...
      </div>
    );
  }

  if (!user) {
    return authView === 'login'
      ? <Login onShowRegister={() => setAuthView('register')} />
      : <Register onShowLogin={() => setAuthView('login')} />;
  }

  return (
    <div className="bg-[#4A594D] h-screen flex flex-col max-w-[900px] mx-auto overflow-hidden p-4 gap-4">
      <header className="flex-none flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-[0.2em] text-[#5E7161] font-bold">
          {user.username}
          <span className="ml-2 text-[#FFA500]">{user.role}</span>
        </span>
        <button
          onClick={logout}
          className="text-[10px] uppercase tracking-widest text-[#5E7161] hover:text-red-400 font-bold"
        >
          Sign out
        </button>
      </header>

      {isAdmin && <AdminPanel />}

      <section className="flex-none">
        <IngredientMatchChecker 
          isActive={activeComponent === 'match'} 
          onSearchTrigger={() => setActiveComponent('match')} 
        />
      </section>

      <section className="flex-1 min-h-0">
        <RecipeManager 
          isActive={activeComponent === 'recipe'} 
          onSearchTrigger={() => setActiveComponent('recipe')}
          isAdmin={isAdmin}
        />
      </section>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
