import { useState } from 'react'
import './App.css'
import IngredientMatchChecker from './components/match_checker'
import RecipeManager from "./components/RecipeManager"

function App() {
  const [activeComponent, setActiveComponent] = useState<'match' | 'recipe' | null>(null);

  return (
    <div className="bg-[#4A594D] h-screen flex flex-col max-w-[900px] mx-auto overflow-hidden p-4 gap-4">
      {/* Top Section: Matches */}
      <section className="flex-none">
        <IngredientMatchChecker 
          isActive={activeComponent === 'match'} 
          onSearchTrigger={() => setActiveComponent('match')} 
        />
      </section>

      {/* Bottom Section: Recipes (Takes all remaining space) */}
      <section className="flex-1 min-h-0">
        <RecipeManager 
          isActive={activeComponent === 'recipe'} 
          onSearchTrigger={() => setActiveComponent('recipe')} 
        />
      </section>
    </div>
  )
}

export default App;