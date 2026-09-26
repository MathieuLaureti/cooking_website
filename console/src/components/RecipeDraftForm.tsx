import React, { useEffect, useRef, useState } from 'react';
import { apiClient } from '../api/client';
import { type RecipeFull, type Component, type RecipeExtract, type ChatTurn, API_BASE } from './types';

interface RecipeDraftFormProps {
  formRecipe: RecipeFull;
  setFormRecipe: React.Dispatch<React.SetStateAction<RecipeFull>>;
  aiLoading: boolean;
  onAiUpload: (type: 'url' | 'image', payload: string | File) => void;
  onSubmit: (dishName: string) => void;
  onClose: () => void;
}

const extractToForm = (e: RecipeExtract): RecipeFull => ({
  id: 0,
  name: e.name,
  dish_id: e.dish_id ?? 0,
  components: e.components.map(c => ({
    name: c.name,
    ingredients: c.ingredients.map(i => ({ ...i })),
    instructions: c.instructions.map(s => ({ ...s })),
  })),
});

const AutoGrowTextarea: React.FC<{
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  className?: string;
}> = ({ value, onChange, className = '' }) => {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  return (
    <textarea
      ref={ref}
      rows={1}
      value={value}
      onChange={onChange}
      className={`overflow-hidden resize-none ${className}`}
    />
  );
};

const RecipeDraftForm: React.FC<RecipeDraftFormProps> = ({
  formRecipe, setFormRecipe, aiLoading, onAiUpload, onSubmit, onClose
}) => {
  const [urlInput, setUrlInput] = useState('');
  const [dishName, setDishName] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatTurn[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatRecipes, setChatRecipes] = useState<RecipeExtract[]>([]);
  const [versionIndex, setVersionIndex] = useState(0);
  const messagesRef = useRef<HTMLDivElement>(null);

  const needsDish = formRecipe.dish_id === 0 && !formRecipe.id;

  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [chatMessages, chatLoading]);

  const draftSnapshot = () => {
    const hasDraft =
      formRecipe.name.trim() ||
      formRecipe.components.length > 0 ||
      Boolean(dishName.trim());
    if (!hasDraft) return null;
    return {
      name: formRecipe.name,
      dish_id: formRecipe.dish_id || null,
      ...(dishName.trim() ? { dish_name: dishName.trim() } : {}),
      components: formRecipe.components.map(c => ({
        ...c,
        ingredients: c.ingredients.map(i => ({
          ...i,
          quantity: i.quantity === '' || i.quantity === undefined ? '' : String(i.quantity),
        })),
      })),
    };
  };

  const sendChat = async () => {
    const msg = chatInput.trim();
    if (!msg || chatLoading) return;
    setChatLoading(true);
    const history = [...chatMessages];
    setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
    setChatInput('');
    try {
      const res = await apiClient.post(`${API_BASE}/recipe_chat`, {
        message: msg,
        dish_id: formRecipe.dish_id || null,
        history,
        current_recipe: draftSnapshot(),
      });
      const data = res.data;
      setChatMessages(prev => [...prev, { role: 'model', text: data.reply || '(recipe ready)' }]);
      if (data.recipes && data.recipes.length) {
        setChatRecipes(data.recipes);
        setVersionIndex(0);
        const first = data.recipes[0];
        setFormRecipe(extractToForm(first));
        if (first.dish_name) setDishName(first.dish_name);
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      let message = 'AI error. Try again.';
      if (typeof detail === 'string') {
        message = detail.length > 280 ? `${detail.slice(0, 280)}…` : detail;
      } else if (Array.isArray(detail) && detail[0]?.msg) {
        message = detail[0].msg;
      }
      setChatMessages(prev => [...prev, { role: 'model', text: message }]);
    } finally {
      setChatLoading(false);
    }
  };

  const goVersion = (dir: number) => {
    const newIdx = versionIndex + dir;
    if (newIdx < 0 || newIdx >= chatRecipes.length) return;
    setChatRecipes(prev => {
      const next = [...prev];
      next[versionIndex] = {
        name: formRecipe.name,
        dish_id: formRecipe.dish_id || null,
        dish_name: dishName || undefined,
        components: formRecipe.components,
      };
      return next;
    });
    setVersionIndex(newIdx);
    const v = chatRecipes[newIdx];
    setFormRecipe(extractToForm(v));
    if (v.dish_name) setDishName(v.dish_name);
  };

  const updateComponent = (index: number, updatedComp: Component) => {
    const newComponents = [...formRecipe.components];
    newComponents[index] = updatedComp;
    setFormRecipe({ ...formRecipe, components: newComponents });
  };

  return (
    <div className="bg-[#374239] w-full p-6 rounded shadow-2xl border border-white/5 text-[#F7F5F2]">
      <div className="mb-4 p-4 bg-black/20 border border-dashed border-white/10 rounded-lg">
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
                {aiLoading ? 'Reading Image...' : 'Drop Recipe Image'}
              </span>
            </label>
          </div>
        </div>
      </div>

      <div className="mb-4 p-4 bg-black/20 border border-dashed border-white/10 rounded-lg">
        {chatMessages.length > 0 && (
          <div ref={messagesRef} className="custom-scrollbar overflow-y-auto max-h-64 mb-3 space-y-2 pr-1">
            {chatMessages.map((m, i) => (
              <div key={i} className={`text-xs leading-relaxed ${m.role === 'user' ? 'text-[#FFA500]' : 'text-[#F7F5F2]'}`}>
                <span className="text-[9px] uppercase tracking-widest text-[#5E7161] font-bold mr-2">{m.role === 'user' ? 'You' : 'AI'}</span>
                {m.text}
              </div>
            ))}
            {chatLoading && <div className="text-[9px] uppercase tracking-widest text-[#5E7161] animate-pulse">AI thinking...</div>}
          </div>
        )}
        <div className="flex gap-2">
          <input
            className="flex-1 bg-[#4A594D] p-2 text-xs outline-none border-b border-[#5E7161] focus:border-[#FFA500] transition-colors"
            placeholder="ask ai"
            title="ask ai"
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } }}
          />
          <button
            disabled={chatLoading || !chatInput.trim()}
            onClick={sendChat}
            className="bg-[#5E7161] px-3 py-2 text-[9px] font-bold uppercase hover:bg-[#FFA500] hover:text-black disabled:opacity-30"
          >
            {chatLoading ? '...' : 'Ask'}
          </button>
        </div>
      </div>

      <div className="flex justify-between items-center mb-6">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-[0.2em] text-[#5E7161] font-bold">
            {formRecipe.id ? 'Editing' : 'Drafting'}
          </span>
          <h2 className="text-2xl font-black italic uppercase">
            {formRecipe.id ? formRecipe.name : 'New Recipe'}
          </h2>
        </div>
        <div className="flex gap-4">
          <button onClick={onClose} className="text-xs opacity-50 uppercase tracking-widest hover:text-white pt-1">Close</button>
        </div>
      </div>

      {needsDish && (
        <input
          className="w-full bg-[#4A594D] p-4 mb-4 outline-none border-b border-[#5E7161] focus:border-[#FFA500]"
          placeholder="DISH NAME"
          value={dishName}
          onChange={e => setDishName(e.target.value)}
        />
      )}

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
                <div key={iIdx} className="flex gap-2">
                  <input className="flex-1 bg-[#4A594D] p-2 text-sm outline-none" placeholder="Item" value={ing.name}
                         onChange={e => {
                           const ings = [...comp.ingredients]; ings[iIdx].name = e.target.value;
                           updateComponent(cIdx, { ...comp, ingredients: ings });
                         }} />
                  <input className="w-16 bg-[#4A594D] p-2 text-sm outline-none font-mono text-center" placeholder="Qty" value={ing.quantity || ''}
                         onChange={e => {
                           const ings = [...comp.ingredients]; ings[iIdx].quantity = e.target.value;
                           updateComponent(cIdx, { ...comp, ingredients: ings });
                         }} />
                  <input className="w-16 bg-[#4A594D] p-2 text-sm outline-none font-mono text-[#FFA500]" placeholder="Unit" value={ing.unit || ''}
                         onChange={e => {
                           const ings = [...comp.ingredients]; ings[iIdx].unit = e.target.value;
                           updateComponent(cIdx, { ...comp, ingredients: ings });
                         }} />
                </div>
              ))}
              <button onClick={() => updateComponent(cIdx, { ...comp, ingredients: [...comp.ingredients, {name: '', quantity: 0, unit: ''}] })} className="text-[10px] text-[#FFA500] uppercase font-bold hover:underline">+ Add Ingredient</button>
            </div>

            <div className="space-y-3">
              <span className="text-[9px] uppercase tracking-widest text-[#5E7161] font-bold block mb-2">Instructions</span>
              {comp.instructions.map((inst, sIdx) => (
                <div key={sIdx} className="flex gap-2">
                  <span className="text-xs font-mono text-[#5E7161] pt-2">{inst.step}</span>
                  <AutoGrowTextarea
                    className="flex-1 bg-[#4A594D] p-2 text-sm outline-none min-h-[2.25rem]"
                    value={inst.text}
                    onChange={e => {
                      const insts = [...comp.instructions];
                      insts[sIdx].text = e.target.value;
                      updateComponent(cIdx, { ...comp, instructions: insts });
                    }}
                  />
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
        <button
          onClick={() => onSubmit(dishName.trim())}
          disabled={needsDish && !dishName.trim()}
          className="flex-1 bg-[#FFA500] text-black py-3 font-black uppercase text-sm hover:bg-[#FFB732] disabled:opacity-30"
        >
          {formRecipe.id ? 'Update Recipe' : 'Save Recipe'}
        </button>
      </div>

      {chatRecipes.length > 1 && (
        <div className="flex items-center justify-between gap-3 mt-6 mb-2 p-3 bg-black/20 rounded-lg border border-white/5">
          <button
            onClick={() => goVersion(-1)}
            disabled={versionIndex === 0}
            className="px-3 py-1 text-xs font-bold text-[#5E7161] hover:text-[#FFA500] disabled:opacity-20"
          >
            ◀
          </button>
          <div className="flex-1 text-center">
            <div className="text-[10px] uppercase tracking-widest text-[#5E7161] font-bold truncate">
              {chatRecipes[versionIndex]?.name || 'version'}
            </div>
            <div className="text-[9px] text-[#F7F5F2]/50 font-mono">
              {versionIndex + 1}/{chatRecipes.length}
            </div>
          </div>
          <button
            onClick={() => goVersion(1)}
            disabled={versionIndex === chatRecipes.length - 1}
            className="px-3 py-1 text-xs font-bold text-[#5E7161] hover:text-[#FFA500] disabled:opacity-20"
          >
            ▶
          </button>
        </div>
      )}
    </div>
  );
};

export default RecipeDraftForm;