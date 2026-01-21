import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { API_BASE, type DishSearch, type RecipeFull } from './types';
import RecipeDraftForm from './RecipeDraftForm';
import RecipeViewer from './RecipeViewer';

const RecipeManager: React.FC<{isActive: boolean, onSearchTrigger: () => void}> = ({ isActive, onSearchTrigger }) => {
  const [dishes, setDishes] = useState<DishSearch[]>([]);
  const [selectedDish, setSelectedDish] = useState<DishSearch | null>(null);
  const [recipes, setRecipes] = useState<DishSearch[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeFull | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreatingRecipe, setIsCreatingRecipe] = useState(false);
  const [isCreatingDish, setIsCreatingDish] = useState(false);
  const [newDishName, setNewDishName] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [formRecipe, setFormRecipe] = useState<RecipeFull>({ name: '', id: 0, dish_id: 0, components: [] });

  useEffect(() => { 
    if (!isActive) { 
      setSelectedRecipe(null); setSelectedDish(null); 
      setIsCreatingRecipe(false); setIsCreatingDish(false); 
      setSearchTerm(''); 
    } 
  }, [isActive]);
  
  const fetchDishes = () => axios.get(`${API_BASE}/searchList`).then(res => setDishes(res.data));
  useEffect(() => { fetchDishes(); }, []);

  const handleDishSelect = async (dish: DishSearch) => {
    setSelectedDish(dish); setSearchTerm('');
    const res = await axios.get(`${API_BASE}/recipe_list/${dish.id}`);
    setRecipes(Array.isArray(res.data) ? res.data : []);
  };

  const handleRecipeSelect = async (recipe: DishSearch) => {
    setSearchTerm('');
    const res = await axios.get(`${API_BASE}/recipe/${selectedDish?.id}/${recipe.id}`);
    setSelectedRecipe(res.data);
  };

  const handleDeleteRecipe = async (recipeId: number) => {
    try {
      await axios.delete(`${API_BASE}/recipe/${recipeId}`);
      setRecipes(prev => prev.filter(r => r.id !== recipeId));
      setSelectedRecipe(null);
    } catch (e) {
      console.error("Deletion failed:", e);
      alert("SERVER REJECTION: UNABLE TO PURGE RECIPE.");
    }
  };

  const handleAiUpload = async (type: 'url' | 'image', payload: string | File) => {
    if (!selectedDish) return;
    setAiLoading(true);
    try {
      let res;
      if (type === 'url') {
        res = await axios.get(`${API_BASE}/recipe_url/${selectedDish.id}`, { params: { url: payload } });
      } else {
        const formData = new FormData();
        formData.append('file', payload);
        res = await axios.post(`${API_BASE}/recipe_image/${selectedDish.id}`, formData);
      }
      const listRes = await axios.get(`${API_BASE}/recipe_list/${selectedDish.id}`);
      setRecipes(Array.isArray(listRes.data) ? listRes.data : []);
      setIsCreatingRecipe(false);
      setSelectedRecipe(res.data);
    } catch (e) { 
      console.error(e); 
      alert("AI EXTRACTION ERROR.");
    } finally { 
      setAiLoading(false); 
    }
  };

  const filteredItems = useMemo(() => {
    const list = !selectedDish ? dishes : recipes;
    return Array.isArray(list) ? list.filter(d => d.name.toLowerCase().includes(searchTerm.toLowerCase())) : [];
  }, [dishes, recipes, selectedDish, searchTerm]);

  if (isCreatingRecipe) return (
    <RecipeDraftForm 
      formRecipe={formRecipe} setFormRecipe={setFormRecipe} 
      aiLoading={aiLoading} onAiUpload={handleAiUpload}
      onClose={() => setIsCreatingRecipe(false)}
      onSubmit={async () => {
        await axios.post(`${API_BASE}/recipe/${selectedDish!.id}`, formRecipe);
        setIsCreatingRecipe(false);
        handleDishSelect(selectedDish!);
      }}
    />
  );

  return (
    <div className="bg-[#4A594D] mx-auto font-sans text-[#F7F5F2]">
      <div className="mb-4 bg-[#374239] rounded overflow-hidden">
        <div className="flex items-center justify-between p-2 px-4 border-b border-white/5 bg-black/20">
          <div className="flex items-center gap-3">
            {selectedDish && !selectedRecipe && (
              <button 
                onClick={() => { setSelectedDish(null); setRecipes([]); setSearchTerm(''); }}
                className="text-[#5E7161] hover:text-white transition-colors flex items-center group"
              >
                <span className="text-lg leading-none group-hover:-translate-x-1 transition-transform">←</span>
              </button>
            )}
            <span className="uppercase tracking-[0.2em] text-[#5E7161] font-bold text-[10px]">
              {selectedRecipe ? 'Datasheet' : selectedDish ? `Recipes / ${selectedDish.name}` : 'Dish Selection'}
            </span>
          </div>
          <div className="flex gap-2">
            {!selectedDish && !selectedRecipe && (
              <button onClick={() => setIsCreatingDish(!isCreatingDish)} className="border border-[#5E7161] text-[#5E7161] px-2 py-0.5 font-bold uppercase text-[9px]">
                {isCreatingDish ? 'Cancel' : '+ New Dish'}
              </button>
            )}
            {selectedDish && !selectedRecipe && (
              <button onClick={() => { setIsCreatingRecipe(true); onSearchTrigger(); }} className="bg-[#FFA500] text-black px-2 py-0.5 font-bold uppercase text-[9px]">+ Create Recipe</button>
            )}
          </div>
        </div>

        {isCreatingDish ? (
          <div className="p-4 flex gap-2">
            <input autoFocus className="flex-1 bg-[#4A594D] p-3 outline-none text-sm" placeholder="New dish name..." value={newDishName} onChange={e => setNewDishName(e.target.value)} />
            <button onClick={async () => {
               const res = await axios.post(`${API_BASE}/dish`, { name: newDishName });
               await fetchDishes();
               handleDishSelect({ id: res.data.id, name: res.data.name });
               setNewDishName(''); setIsCreatingDish(false);
            }} className="bg-[#FFA500] text-black px-4 font-bold text-xs uppercase">Add</button>
          </div>
        ) : (
          !selectedRecipe && <input type="text" className="w-full p-4 text-lg bg-transparent outline-none" placeholder={selectedDish ? "Find recipe..." : "Search dish catalog..."} value={searchTerm} onChange={e => { setSearchTerm(e.target.value); onSearchTrigger(); }} />
        )}

        {!selectedRecipe && searchTerm && (
          <div className="custom-scrollbar overflow-y-auto bg-[#374239] border-t border-white/5 max-h-64">
            {filteredItems.map(item => (
              <div key={item.id} onClick={() => !selectedDish ? handleDishSelect(item) : handleRecipeSelect(item)} className="p-3 hover:bg-[#F7F5F2]/10 cursor-pointer border-b border-white/5 last:border-0">{item.name}</div>
            ))}
          </div>
        )}
      </div>

      {selectedRecipe && (
        <RecipeViewer 
          recipe={selectedRecipe} 
          dishName={selectedDish?.name} 
          onBack={() => setSelectedRecipe(null)} 
          onDelete={handleDeleteRecipe}
        />
      )}
    </div>
  );
};

export default RecipeManager;