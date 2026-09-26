import { useState } from 'react'
import './App.css'
import IngredientMatchChecker from './components/MatchChecker'
import RecipeManager from "./components/RecipeManager"
import Login from './components/Login'
import Register from './components/Register'
import AdminHome from './components/AdminHome'
import MobileInstallButton from './components/MobileInstallButton'
import { AuthProvider } from './context/AuthProvider'
import { useAuth } from './context/auth-context'

function AppContent() {
  const { user, isAdmin, isLoading, logout } = useAuth();
  const [activeComponent, setActiveComponent] = useState<'match' | 'recipe' | null>(null);
  const [authView, setAuthView] = useState<'login' | 'register'>('login');
  const [surface, setSurface] = useState<'user' | 'admin'>('user');
  const [focusFoodId, setFocusFoodId] = useState<number | null>(null);

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
          {isAdmin ? (
            <button
              type="button"
              onClick={() => setSurface(current => current === 'admin' ? 'user' : 'admin')}
              className="ml-2 px-2 py-1 text-[#FFA500]"
            >
              {surface === 'admin' ? 'user' : 'admin'}
            </button>
          ) : (
            <span className="ml-2 text-[#FFA500]">{user.role}</span>
          )}
        </span>
        <div className="flex items-center gap-3">
          <MobileInstallButton />
          <button
            onClick={logout}
            className="text-[10px] uppercase tracking-widest text-[#5E7161] hover:text-red-400 font-bold"
          >
            Sign out
          </button>
        </div>
      </header>

      {surface === 'admin' && isAdmin ? (
        <AdminHome onOpenFood={(foodId) => {
          setFocusFoodId(foodId);
          setActiveComponent('match');
          setSurface('user');
        }} />
      ) : (
      <div className="flex-1 min-h-0 flex flex-col gap-2 w-full min-w-0">
        <div
          className={`panel-slot ${
            activeComponent === 'match' ? 'panel-slot-expanded' : 'panel-slot-collapsed'
          }`}
        >
          <IngredientMatchChecker
            isActive={activeComponent === 'match'}
            onSearchTrigger={() => setActiveComponent('match')}
            focusFoodId={focusFoodId}
            onFoodOpened={() => setFocusFoodId(null)}
          />
        </div>

        <div
          className={`panel-slot ${
            activeComponent !== 'match' ? 'panel-slot-expanded' : 'panel-slot-collapsed'
          }`}
        >
          <RecipeManager
            isActive={activeComponent === 'recipe'}
            onSearchTrigger={() => setActiveComponent('recipe')}
            isAdmin={isAdmin}
          />
        </div>
      </div>
      )}
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
