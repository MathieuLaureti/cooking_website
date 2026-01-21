import React, { useState } from 'react';
import { type RecipeFull, type Component } from './types';

interface RecipeDraftFormProps {
  formRecipe: RecipeFull;
  setFormRecipe: React.Dispatch<React.SetStateAction<RecipeFull>>;
  aiLoading: boolean;
  onAiUpload: (type: 'url' | 'image', payload: string | File) => void;
  onSubmit: () => void;
  onClose: () => void;
}

const RecipeDraftForm: React.FC<RecipeDraftFormProps> = ({ 
  formRecipe, setFormRecipe, aiLoading, onAiUpload, onSubmit, onClose 
}) => {
  const [urlInput, setUrlInput] = useState('');

  const updateComponent = (index: number, updatedComp: Component) => {
    const newComponents = [...formRecipe.components];
    newComponents[index] = updatedComp;
    setFormRecipe({ ...formRecipe, components: newComponents });
  };

  return (
    <div className="bg-[#374239] w-full p-6 rounded shadow-2xl border border-white/5 text-[#F7F5F2] h-full">
      {/* AI Extraction Tools */}
      <div className="mb-8 p-4 bg-black/20 border border-dashed border-white/10 rounded-lg">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 flex gap-2">
            <input 
              className="flex-1 bg-[#4A594D] p-2 text-xs outline-none border-b border-[#5E7161] focus:border-[#FFA500] transition-colors"
              placeholder="IMPORT FROM URL"
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
            />
            <button 
              disabled={aiLoading || !urlInput}
              onClick={() => onAiUpload('url', urlInput)}
              className="bg-[#5E7161] px-3 py-2 text-[9px] font-bold uppercase hover:bg-[#FFA500] hover:text-black disabled:opacity-30"
            >
              {aiLoading ? 'Processing...' : 'Scrape'}
            </button>
          </div>

          <div className="flex-1 relative">
            <input 
              type="file" accept="image/*" id="ai-image-upload" className="hidden" 
              onChange={e => e.target.files?.[0] && onAiUpload('image', e.target.files[0])}
            />
            <label htmlFor="ai-image-upload" className="flex items-center justify-center w-full h-full bg-black/30 border border-[#5E7161] border-dashed py-2 cursor-pointer hover:bg-[#FFA500]/10 hover:border-[#FFA500] group">
              <span className="text-[9px] font-bold uppercase text-[#5E7161] group-hover:text-[#FFA500]">
                {aiLoading ? 'Reading Image...' : 'Drop Recipe Image (Llama 3.2)'}
              </span>
            </label>
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center mb-6">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-[0.2em] text-[#5E7161] font-bold">Drafting</span>
          <h2 className="text-2xl font-black italic uppercase">New Recipe</h2>
        </div>
        <div className="flex gap-4">
          <button onClick={() => setFormRecipe({ name: '',id: 0, dish_id: 0, components: [] })} className="text-[10px] text-red-400 border border-red-400/20 px-2 py-1 uppercase font-bold hover:bg-red-400 hover:text-black">Scrap Recipe</button>
          <button onClick={onClose} className="text-xs opacity-50 uppercase tracking-widest hover:text-white pt-1">Close</button>
        </div>
      </div>

      <input 
        className="w-full bg-[#4A594D] p-4 mb-8 outline-none border-b border-[#FFA500]" 
        placeholder="RECIPE TITLE" 
        value={formRecipe.name}
        onChange={e => setFormRecipe({...formRecipe, name: e.target.value})} 
      />

      {formRecipe.components.map((comp, cIdx) => (
        <div key={cIdx} className="mb-10 p-6 bg-black/10 border-l-2 border-[#FFA500] relative group">
          <button 
            onClick={() => setFormRecipe({...formRecipe, components: formRecipe.components.filter((_, i) => i !== cIdx)})}
            className="absolute top-4 right-4 text-[10px] text-red-400 uppercase font-bold opacity-0 group-hover:opacity-100"
          >
            Remove Component
          </button>

          <input 
            className="bg-transparent text-xl font-bold mb-6 outline-none w-full border-b border-white/5 pb-2" 
            placeholder="COMPONENT NAME" value={comp.name}
            onChange={e => updateComponent(cIdx, { ...comp, name: e.target.value })} 
          />

          <div className="grid md:grid-cols-2 gap-8">
            <div className="space-y-3">
              <span className="text-[9px] uppercase tracking-widest text-[#5E7161] font-bold block mb-2">Ingredients</span>
              {comp.ingredients.map((ing, iIdx) => (
                <div key={iIdx} className="flex gap-2 group/item">
                  <input className="flex-1 bg-[#4A594D] p-2 text-sm outline-none" placeholder="Item" value={ing.name}
                         onChange={e => {
                           const ings = [...comp.ingredients]; ings[iIdx].name = e.target.value;
                           updateComponent(cIdx, { ...comp, ingredients: ings });
                         }} />
                  <input className="w-20 bg-[#4A594D] p-2 text-sm outline-none font-mono text-center" placeholder="Qty" value={ing.quantity || ''}
                         onChange={e => {
                           const ings = [...comp.ingredients]; ings[iIdx].quantity = Number(e.target.value);
                           updateComponent(cIdx, { ...comp, ingredients: ings });
                         }} />
                </div>
              ))}
              <button onClick={() => updateComponent(cIdx, { ...comp, ingredients: [...comp.ingredients, {name: '', quantity: 0, unit: ''}] })} className="text-[10px] text-[#FFA500] uppercase font-bold hover:underline">+ Add Ingredient</button>
            </div>

            <div className="space-y-3">
              <span className="text-[9px] uppercase tracking-widest text-[#5E7161] font-bold block mb-2">Instructions</span>
              {comp.instructions.map((inst, sIdx) => (
                <div key={sIdx} className="flex gap-2 group/step">
                  <span className="text-xs font-mono text-[#5E7161] pt-2">{inst.step}</span>
                  <textarea className="flex-1 bg-[#4A594D] p-2 text-sm outline-none resize-none" rows={1} value={inst.text}
                            onChange={e => {
                              const insts = [...comp.instructions]; insts[sIdx].text = e.target.value;
                              updateComponent(cIdx, { ...comp, instructions: insts });
                            }} />
                </div>
              ))}
              <button onClick={() => updateComponent(cIdx, { ...comp, instructions: [...comp.instructions, {step: comp.instructions.length + 1, text: ''}] })} className="text-[10px] text-[#FFA500] uppercase font-bold hover:underline">+ Add Step</button>
            </div>
          </div>
        </div>
      ))}

      <div className="flex gap-4 mt-8 border-t border-white/5 pt-6">
        <button onClick={() => setFormRecipe({...formRecipe, components: [...formRecipe.components, { name: '', ingredients: [{name:'', quantity:0, unit:''}], instructions: [{step: 1, text:''}] }]})} 
                className="border border-white/10 px-6 py-3 text-[10px] font-bold uppercase hover:bg-white/5">Add Component</button>
        <button onClick={onSubmit} className="flex-1 bg-[#FFA500] text-black py-3 font-black uppercase text-sm hover:bg-[#FFB732]">Save Recipe</button>
      </div>
    </div>
  );
};

export default RecipeDraftForm;