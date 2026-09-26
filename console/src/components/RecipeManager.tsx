import React, { useState, useEffect, useMemo } from 'react';
import { apiClient } from '../api/client';
import { API_BASE, type DishSearch, type RecipeFull } from './types';
import RecipeDraftForm from './RecipeDraftForm';
import RecipeViewer from './RecipeViewer';

const RecipeManager: React.FC<{ isActive: boolean, onSearchTrigger: () => void, isAdmin: boolean }> = ({ isActive, onSearchTrigger, isAdmin }) => {
  const [dishes, setDishes] = useState<DishSearch[]>([]);
  const [selectedDish, setSelectedDish] = useState<DishSearch | null>(null);
  const [recipes, setRecipes] = useState<DishSearch[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeFull | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreatingRecipe, setIsCreatingRecipe] = useState(false);
  const [isCreatingDish, setIsCreatingDish] = useState(false);
  const [newDishName, setNewDishName] = useState('');
  const [isRenamingDish, setIsRenamingDish] = useState(false);
  const [renameDishName, setRenameDishName] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  const emptyRecipe = (dishId: number): RecipeFull => ({
    id: 0,
    name: '',
    dish_id: dishId,
    components: []
  });

  const [formRecipe, setFormRecipe] = useState<RecipeFull>(emptyRecipe(0));

  useEffect(() => {
    if (!isActive) {
      setSearchTerm('');
    }
  }, [isActive]);

  const fetchDishes = () => apiClient.get(`${API_BASE}/dishes`).then(res => setDishes(res.data));
  useEffect(() => { fetchDishes(); }, []);

  const handleDishSelect = async (dish: DishSearch) => {
    setSelectedDish(dish); setSearchTerm('');
    const res = await apiClient.get(`${API_BASE}/recipes/${dish.id}`);
    setRecipes(Array.isArray(res.data) ? res.data : []);
  };

  const handleRecipeSelect = async (recipe: DishSearch) => {
    setSearchTerm('');
    try {
      const res = await apiClient.get(`${API_BASE}/recipe/${recipe.id}`);
      setSelectedRecipe(res.data);
    } catch (e) { console.error("Error fetching recipe:", e); }
  };

  const handleDeleteRecipe = async (recipeId: number) => {
    try {
      await apiClient.delete(`${API_BASE}/recipe/${recipeId}`);
      setRecipes(prev => prev.filter(r => r.id !== recipeId));
      setSelectedRecipe(null);
    } catch {
      alert("SERVER REJECTION: UNABLE TO PURGE RECIPE.");
    }
  };

  const showRecipe = async (recipe: RecipeFull) => {
    const dishRes = await apiClient.get(`${API_BASE}/dishes`);
    setDishes(dishRes.data);
    const dish = dishRes.data.find((d: DishSearch) => d.id === recipe.dish_id) ?? null;
    setSelectedDish(dish);
    if (dish) {
      const list = await apiClient.get(`${API_BASE}/recipes/${dish.id}`);
      setRecipes(Array.isArray(list.data) ? list.data : []);
    }
    setSearchTerm('');
    setIsCreatingRecipe(false);
    setSelectedRecipe(recipe);
  };

  const handleAiUpload = async (type: 'url' | 'image', payload: string | File) => {
    setAiLoading(true);
    try {
      const params = selectedDish ? { dish_id: selectedDish.id } : {};
      let res;
      if (type === 'url') {
        res = await apiClient.get(`${API_BASE}/recipe_url`, { params: { url: payload, ...params } });
      } else {
        const formData = new FormData();
        formData.append('file', payload);
        res = await apiClient.post(`${API_BASE}/recipe_image`, formData, { params });
      }
      await showRecipe(res.data);
    } catch {
      alert("AI EXTRACTION ERROR.");
    } finally { setAiLoading(false); }
  };

  const filteredItems = useMemo(() => {
    const list = !selectedDish ? dishes : recipes;
    if (!Array.isArray(list)) return [];
    return list
      .filter(d => d.name.toLowerCase().includes(searchTerm.toLowerCase()))
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));
  }, [dishes, recipes, selectedDish, searchTerm]);

  const handleDeleteDish = async () => {
    if (!selectedDish) return;
    if (recipes.length > 0) {
      window.alert('Cannot delete this dish while it still has recipes. Remove every recipe first.');
      return;
    }
    const ok = window.confirm(
      `Delete dish "${selectedDish.name}"?\n\nThis cannot be undone.`
    );
    if (!ok) return;
    try {
      await apiClient.delete(`${API_BASE}/dish/${selectedDish.id}`);
      await fetchDishes();
      setSelectedDish(null);
      setRecipes([]);
      setSearchTerm('');
      setIsRenamingDish(false);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      window.alert(typeof detail === 'string' ? detail : 'Could not delete dish.');
    }
  };

  const handleRenameDish = async () => {
    if (!selectedDish) return;
    const name = renameDishName.trim();
    if (!name) return;
    if (name === selectedDish.name) {
      setIsRenamingDish(false);
      return;
    }
    const ok = window.confirm(`Rename dish to "${name}"? Recipes on this dish will keep their link.`);
    if (!ok) return;
    try {
      const res = await apiClient.put(`${API_BASE}/dish_edit/${selectedDish.id}`, { name });
      await fetchDishes();
      setSelectedDish({ id: res.data.id, name: res.data.name });
      setIsRenamingDish(false);
      setRenameDishName('');
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      window.alert(typeof detail === 'string' ? detail : 'Could not rename dish.');
    }
  };

  const showPicker = isActive && !selectedRecipe && !isCreatingDish && !isRenamingDish;

  if (isCreatingRecipe) return (
    <div className="h-full min-h-0 overflow-y-auto custom-scrollbar pr-1">
      <RecipeDraftForm
      formRecipe={formRecipe} setFormRecipe={setFormRecipe}
      aiLoading={aiLoading} onAiUpload={handleAiUpload}
      onClose={() => {
        setIsCreatingRecipe(false);
        setFormRecipe(emptyRecipe(selectedDish?.id || 0));
      }}
      onSubmit={async (dishName) => {
        if (formRecipe.id && formRecipe.id !== 0) {
          await apiClient.put(`${API_BASE}/recipe_edit/${formRecipe.id}`, formRecipe);
          setIsCreatingRecipe(false);
          if (selectedDish) handleDishSelect(selectedDish);
          setSelectedRecipe(null);
          return;
        }
        const res = selectedDish
          ? await apiClient.post(`${API_BASE}/recipe/${selectedDish.id}`, formRecipe)
          : await apiClient.post(`${API_BASE}/recipe`, {
              name: formRecipe.name,
              dish_id: formRecipe.dish_id || null,
              dish_name: dishName,
              components: formRecipe.components,
            });
        await showRecipe(res.data);
      }}
      />
    </div>
  );

  return (
    <div className="w-full min-w-0 bg-[#4A594D] font-sans text-[#F7F5F2] h-full min-h-0 flex flex-col">
      <div
        className={`w-full min-w-0 mb-4 bg-[#374239] rounded flex flex-col min-h-0 overflow-hidden transition-[flex-grow] duration-300 ease-in-out ${
          showPicker ? 'flex-1' : 'flex-none shrink-0'
        }`}
      >
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
            {selectedDish && !selectedRecipe && isAdmin && !isRenamingDish && (
              <button
                type="button"
                onClick={() => {
                  setRenameDishName(selectedDish.name);
                  setIsRenamingDish(true);
                  setIsCreatingDish(false);
                }}
                className="text-[9px] uppercase font-bold text-[#5E7161] hover:text-[#FFA500] border border-[#5E7161]/50 px-1.5 py-0.5"
                title="Rename dish"
              >
                Rename
              </button>
            )}
          </div>
          <div className="flex gap-2 items-center">
            {!selectedDish && !selectedRecipe && isAdmin && (
              <>
                <button onClick={() => setIsCreatingDish(!isCreatingDish)} className="border border-[#5E7161] text-[#5E7161] px-2 py-0.5 font-bold uppercase text-[9px]">
                  {isCreatingDish ? 'Cancel' : '+ New Dish'}
                </button>
                <button onClick={() => {
                  setFormRecipe(emptyRecipe(0));
                  setIsCreatingRecipe(true);
                  onSearchTrigger();
                }} className="bg-[#FFA500] text-black px-2 py-0.5 font-bold uppercase text-[9px]">+ Create Recipe</button>
              </>
            )}
            {selectedDish && !selectedRecipe && isAdmin && (
              <>
                <button
                  type="button"
                  onClick={handleDeleteDish}
                  disabled={recipes.length > 0}
                  title={recipes.length > 0 ? 'Remove all recipes before deleting this dish' : 'Delete dish'}
                  className="border border-red-900/40 text-red-400/80 px-1.5 py-0.5 text-sm leading-none hover:bg-red-950/30 disabled:opacity-25 disabled:cursor-not-allowed"
                  aria-label="Delete dish"
                >
                  🗑
                </button>
                <button onClick={() => {
                  setFormRecipe(emptyRecipe(selectedDish.id));
                  setIsCreatingRecipe(true);
                  onSearchTrigger();
                }} className="bg-[#FFA500] text-black px-2 py-0.5 font-bold uppercase text-[9px]">+ Create Recipe</button>
              </>
            )}
          </div>
        </div>

        {isRenamingDish && selectedDish && isAdmin ? (
          <div className="p-4 flex gap-2 border-b border-white/5">
            <input
              autoFocus
              className="flex-1 bg-[#4A594D] p-3 outline-none text-sm border-b border-[#FFA500]"
              placeholder="Dish name..."
              value={renameDishName}
              onChange={e => setRenameDishName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleRenameDish(); if (e.key === 'Escape') setIsRenamingDish(false); }}
            />
            <button
              onClick={() => setIsRenamingDish(false)}
              className="border border-white/10 px-3 font-bold text-[10px] uppercase"
            >
              Cancel
            </button>
            <button
              onClick={handleRenameDish}
              disabled={!renameDishName.trim()}
              className="bg-[#FFA500] text-black px-4 font-bold text-xs uppercase disabled:opacity-30"
            >
              Save
            </button>
          </div>
        ) : isCreatingDish && isAdmin ? (
          <div className="p-4 flex gap-2">
            <input autoFocus className="flex-1 bg-[#4A594D] p-3 outline-none text-sm border-b border-[#FFA500]" placeholder="New dish name..." value={newDishName} onChange={e => setNewDishName(e.target.value)} />
            <button onClick={async () => {
              const res = await apiClient.post(`${API_BASE}/dish`, { name: newDishName });
              await fetchDishes();
              handleDishSelect({ id: res.data.id, name: res.data.name });
              setNewDishName(''); setIsCreatingDish(false);
            }} className="bg-[#FFA500] text-black px-4 font-bold text-xs uppercase">Add</button>
          </div>
        ) : (
          !selectedRecipe && !isRenamingDish && <input type="text" className="w-full p-4 text-lg bg-transparent outline-none flex-none" placeholder={selectedDish ? "Find recipe..." : "Search dish catalog..."} value={searchTerm} onChange={e => { setSearchTerm(e.target.value); onSearchTrigger(); }} onFocus={onSearchTrigger} />
        )}

        <div
          className={`expand-grid border-t border-white/5 ${
            showPicker ? 'expand-grid-open flex-1 min-h-0' : 'expand-grid-closed flex-none'
          }`}
        >
          <div className="min-h-0 overflow-hidden flex flex-col">
            <div className="custom-scrollbar overflow-y-auto bg-[#374239] flex-1 min-h-0">
              {filteredItems.map(item => (
                <div key={item.id} onClick={() => !selectedDish ? handleDishSelect(item) : handleRecipeSelect(item)} className="p-3 hover:bg-[#F7F5F2]/10 cursor-pointer border-b border-white/5 last:border-0">{item.name}</div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {selectedRecipe && (
        <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1">
        <RecipeViewer
          recipe={selectedRecipe}
          dishName={selectedDish?.name}
          isAdmin={isAdmin}
          onBack={() => setSelectedRecipe(null)}
          onDelete={handleDeleteRecipe}
          onEdit={(recipe) => {
            setFormRecipe(recipe);
            setIsCreatingRecipe(true);
          }}
        />
        </div>
      )}
    </div>
  );
};

export default RecipeManager;
