import React, { useState } from 'react';
import type { RecipeFull } from './types';

interface RecipeViewerProps {
  recipe: RecipeFull;
  dishName?: string;
  onBack: () => void;
  onDelete: (id: number) => Promise<void>;
  onEdit: (recipe: RecipeFull) => void;
}

const RecipeViewer: React.FC<RecipeViewerProps> = ({ recipe, dishName, onBack, onDelete, onEdit }) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleAction = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (!isDeleting) {
      setIsDeleting(true);
    } else {
      if (recipe.id) {
        try {
          await onDelete(recipe.id);
        } catch (err) {
          setIsDeleting(false);
        }
      }
    }
  };

  return (
    <div className="bg-[#374239] p-6 rounded shadow-xl animate-in fade-in zoom-in-95">
      <div className="flex justify-between items-start mb-4">
        <button 
          onClick={onBack} 
          className="text-[9px] uppercase tracking-[0.2em] text-[#5E7161] font-bold hover:text-[#F7F5F2] transition-colors"
        >
          ← Back to {dishName}
        </button>
        
        <div className="flex gap-2">
          {!isDeleting && (
            <button 
              onClick={() => onEdit(recipe)}
              className="text-[10px] border border-[#FFA500]/40 text-[#FFA500] px-3 py-1 uppercase font-bold hover:bg-[#FFA500] hover:text-black transition-all"
            >
              Edit Recipe
            </button>
          )}

          {isDeleting && (
            <button 
              type="button"
              onClick={() => setIsDeleting(false)}
              className="text-[10px] text-[#5E7161] px-2 py-1 uppercase font-bold hover:text-white"
            >
              Cancel
            </button>
          )}
          <button 
            type="button"
            onClick={handleAction}
            className={`text-[10px] border px-3 py-1 uppercase font-bold transition-all duration-200 ${
              isDeleting 
                ? 'bg-red-600 text-white border-red-600 animate-pulse' 
                : 'text-red-400 border-red-400/20 hover:bg-red-400 hover:text-black'
            }`}
          >
            {isDeleting ? 'Confirm Delete?' : 'Delete Recipe'}
          </button>
        </div>
      </div>

      <h1 className="text-4xl font-black uppercase italic mb-8 border-b border-white/5 pb-4">
        {recipe.name}
      </h1>
      
      {recipe.components.map((comp, idx) => (
        <div key={idx} className="mb-12">
          <h2 className="font-bold text-xs tracking-widest bg-black/40 border border-white/5 px-3 py-1.5 inline-block uppercase mb-6">
            {comp.name}
          </h2>
          <div className="grid md:grid-cols-2 gap-10">
            <div>
              <span className="text-[9px] uppercase tracking-widest text-[#5E7161] font-bold block mb-4 border-b border-white/5">Mise en place</span>
              {comp.ingredients.map((ing, i) => (
                <div key={i} className="flex justify-between border-b border-white/5 py-2">
                  <span className="text-sm">{ing.name}</span>
                  <span className="font-mono text-xs text-[#FFA500]">{ing.quantity} {ing.unit}</span>
                </div>
              ))}
            </div>
            <div>
              <span className="text-[9px] uppercase tracking-widest text-[#5E7161] font-bold block mb-4 border-b border-white/5">Method</span>
              {comp.instructions.sort((a,b)=>a.step-b.step).map((inst, i) => (
                <div key={i} className="flex gap-4 mb-4">
                  <span className="font-mono text-xs text-[#5E7161] mt-1">{inst.step.toString().padStart(2,'0')}</span>
                  <p className="text-sm opacity-90 leading-relaxed">{inst.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default RecipeViewer;