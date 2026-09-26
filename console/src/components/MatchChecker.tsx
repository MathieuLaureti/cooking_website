import React, { useState, useEffect, useMemo, useRef, type ChangeEvent, type UIEvent } from 'react';
import { API_PREFIX, apiClient } from '../api/client';

const PAIRING_API = `${API_PREFIX}/match_checker`;
const NUTRITION_API = `${API_PREFIX}/nutrition`;

type PanelMode = 'pairings' | 'nutrition';

interface MatchCheckerShort { id: number; title: string; }
interface MatchCheckerFull extends MatchCheckerShort { 
    avoid: string[]; 
    affinities: string[]; 
    matches: [string, number][]; 
}

interface NutritionFoodShort {
    id: number;
    name_en: string;
    name_fr: string;
    group_en: string | null;
}

interface NutritionAmount {
    code: string;
    symbol: string | null;
    name_en: string;
    name_fr: string;
    unit: string;
    decimals: number | null;
    amount_per_100g: number;
}

interface NutritionFoodPage {
    items: NutritionFoodShort[];
    offset: number;
    has_more: boolean;
}

interface NutritionFoodFull extends NutritionFoodShort {
    group_fr: string | null;
    nutrients: NutritionAmount[];
}

const FOOD_PAGE = 50;
const SCROLL_EDGE = 48;

const CORE_NUTRIENT_CODES = ['208', '203', '204', '606', '205', '269', '291', '307'];

function formatAmount(amount: number, decimals: number | null) {
    const places = decimals ?? 2;
    return amount.toLocaleString(undefined, {
        maximumFractionDigits: places,
        minimumFractionDigits: 0,
    });
}

const IngredientMatchChecker: React.FC<{
    isActive: boolean,
    onSearchTrigger: () => void,
    focusFoodId?: number | null,
    onFoodOpened?: () => void,
}> = ({ isActive, onSearchTrigger, focusFoodId, onFoodOpened }) => {
    const [mode, setMode] = useState<PanelMode>('pairings');
    const [ingredients, setIngredients] = useState<MatchCheckerShort[]>([]);
    const [foods, setFoods] = useState<NutritionFoodShort[]>([]);
    const [searchTerm, setSearchTerm] = useState<string>('');
    const [selectedIngredient, setSelectedIngredient] = useState<MatchCheckerFull | null>(null);
    const [selectedFood, setSelectedFood] = useState<NutritionFoodFull | null>(null);
    const [loading, setLoading] = useState(false);
    const [searching, setSearching] = useState(false);
    const [foodOffset, setFoodOffset] = useState(0);
    const [hasMoreFoods, setHasMoreFoods] = useState(false);
    const listRef = useRef<HTMLDivElement>(null);
    const paging = useRef(false);
    const placeAfterLoad = useRef<'top' | 'bottom' | 'reset' | null>(null);
    const requestId = useRef(0);
    const onFoodOpenedRef = useRef(onFoodOpened);
    onFoodOpenedRef.current = onFoodOpened;

    useEffect(() => {
        if (!isActive) setSearchTerm('');
    }, [isActive]);

    useEffect(() => {
        if (!focusFoodId) return;
        let cancelled = false;
        setMode('nutrition');
        apiClient.get<NutritionFoodFull>(`${NUTRITION_API}/foods/${focusFoodId}`).then(res => {
            if (cancelled) return;
            setSelectedFood(res.data);
            setSearchTerm(res.data.name_en);
            onFoodOpenedRef.current?.();
        });
        return () => { cancelled = true; };
    }, [focusFoodId]);

    useEffect(() => { apiClient.get(`${PAIRING_API}/ingredients`).then(res => setIngredients(res.data)); }, []);

    useEffect(() => {
        const place = placeAfterLoad.current;
        if (!place) return;
        placeAfterLoad.current = null;
        const el = listRef.current;
        if (el) {
            if (place === 'top') el.scrollTop = SCROLL_EDGE;
            else if (place === 'bottom') el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight - SCROLL_EDGE);
            else el.scrollTop = 0;
        }
        paging.current = false;
    }, [foods, foodOffset]);

    useEffect(() => {
        if (mode !== 'nutrition' || selectedFood) return;
        const query = searchTerm.trim();
        const id = ++requestId.current;
        setSearching(true);
        const handle = window.setTimeout(() => {
            paging.current = true;
            apiClient
                .get<NutritionFoodPage>(`${NUTRITION_API}/foods`, { params: { q: query, offset: 0 } })
                .then(res => {
                    if (id !== requestId.current) return;
                    placeAfterLoad.current = 'reset';
                    setFoods(res.data.items);
                    setFoodOffset(res.data.offset);
                    setHasMoreFoods(res.data.has_more);
                })
                .catch(() => {
                    if (id !== requestId.current) return;
                    setFoods([]);
                    setFoodOffset(0);
                    setHasMoreFoods(false);
                    paging.current = false;
                })
                .finally(() => {
                    if (id === requestId.current) setSearching(false);
                });
        }, query ? 200 : 0);
        return () => {
            window.clearTimeout(handle);
            requestId.current += 1;
        };
    }, [mode, searchTerm, selectedFood]);

    const loadFoodWindow = (offset: number, place: 'top' | 'bottom') => {
        const query = searchTerm.trim();
        const id = ++requestId.current;
        paging.current = true;
        setSearching(true);
        apiClient
            .get<NutritionFoodPage>(`${NUTRITION_API}/foods`, { params: { q: query, offset } })
            .then(res => {
                if (id !== requestId.current) return;
                placeAfterLoad.current = place;
                setFoods(res.data.items);
                setFoodOffset(res.data.offset);
                setHasMoreFoods(res.data.has_more);
            })
            .catch(() => {
                if (id !== requestId.current) return;
                paging.current = false;
            })
            .finally(() => {
                if (id === requestId.current) setSearching(false);
            });
    };

    const handleFoodScroll = (event: UIEvent<HTMLDivElement>) => {
        if (mode !== 'nutrition' || paging.current || searching) return;
        const el = event.currentTarget;
        const overflow = el.scrollHeight - el.clientHeight;
        if (overflow <= SCROLL_EDGE) return;
        if (el.scrollTop < SCROLL_EDGE && foodOffset > 0) {
            loadFoodWindow(Math.max(0, foodOffset - FOOD_PAGE), 'bottom');
        } else if (hasMoreFoods && overflow - el.scrollTop < SCROLL_EDGE) {
            loadFoodWindow(foodOffset + FOOD_PAGE, 'top');
        }
    };

    const switchMode = (next: PanelMode) => {
        setMode(next);
        setSearchTerm('');
        setSelectedIngredient(null);
        setSelectedFood(null);
        onSearchTrigger();
    };

    const handleSelect = async (ing: MatchCheckerShort) => {
        setLoading(true); 
        setSearchTerm(ing.title);
        try {
            const res = await apiClient.get<MatchCheckerFull>(`${PAIRING_API}/ingredient/${ing.id}`);
            setSelectedIngredient(res.data);
        } finally { setLoading(false); }
    };

    const handleSelectFood = async (food: NutritionFoodShort) => {
        setLoading(true);
        setSearchTerm(food.name_en);
        try {
            const res = await apiClient.get<NutritionFoodFull>(`${NUTRITION_API}/foods/${food.id}`);
            setSelectedFood(res.data);
        } finally { setLoading(false); }
    };

    const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(e.target.value);
        onSearchTrigger();
        if (selectedIngredient) setSelectedIngredient(null);
        if (selectedFood) setSelectedFood(null);
    };

    const filtered = useMemo(
        () =>
            ingredients
                .filter(ing => ing.title.toLowerCase().includes(searchTerm.toLowerCase()))
                .sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' })),
        [ingredients, searchTerm],
    );

    const coreNutrients = selectedFood
        ? CORE_NUTRIENT_CODES
            .map(code => selectedFood.nutrients.find(nutrient => nutrient.code === code))
            .filter((nutrient): nutrient is NutritionAmount => Boolean(nutrient))
        : [];
    const otherNutrients = selectedFood
        ? selectedFood.nutrients.filter(nutrient => !CORE_NUTRIENT_CODES.includes(nutrient.code))
        : [];
    
    const getScoreColor = (score: number) => {
        switch (score) {
            case 4: return "text-[#FFA500] font-black"; 
            case 3: return "text-[#FFD700] font-bold";
            case 2: return "text-[#F1F5F9] font-medium";
            default: return "text-slate-400 font-light opacity-60";
        }
    };

    const selected = mode === 'pairings' ? selectedIngredient : selectedFood;
    const showPicker = isActive && !selected;
    const clearSelection = () => {
        setSelectedIngredient(null);
        setSelectedFood(null);
        setSearchTerm('');
    };

    return (
        <div className="h-full min-h-0 w-full min-w-0 flex flex-col gap-2">
            <div
                className={`bg-[#374239] rounded overflow-hidden shadow-xl flex flex-col w-full min-w-0 transition-[flex-grow] duration-300 ease-in-out ${
                    isActive ? 'flex-1 min-h-0' : 'flex-none shrink-0'
                }`}
            >
                <div className="flex items-center justify-between gap-2 p-2 px-4 border-b border-white/5 bg-black/20 flex-none">
                    <div className="flex items-center gap-2 min-w-0">
                        <button
                            type="button"
                            onClick={() => switchMode('pairings')}
                            className={`uppercase tracking-[0.15em] font-bold text-[11px] sm:text-[10px] ${
                                mode === 'pairings' ? 'text-[#FFA500]' : 'text-[#5E7161]'
                            }`}
                        >
                            Pairings
                        </button>
                        <span className="text-[#5E7161]">/</span>
                        <button
                            type="button"
                            onClick={() => switchMode('nutrition')}
                            className={`uppercase tracking-[0.15em] font-bold text-[11px] sm:text-[10px] ${
                                mode === 'nutrition' ? 'text-[#FFA500]' : 'text-[#5E7161]'
                            }`}
                        >
                            Nutrition
                        </button>
                    </div>
                    {selected && (
                        <button onClick={clearSelection} className="text-[10px] uppercase underline opacity-60 hover:opacity-100 shrink-0">Clear</button>
                    )}
                </div>

                <input 
                    type="text" 
                    className="w-full p-4 text-lg outline-none bg-transparent flex-none" 
                    placeholder={mode === 'pairings' ? 'Search ingredient pairings...' : 'Search foods (English or French)...'} 
                    value={searchTerm} 
                    onChange={handleInputChange}
                    onFocus={onSearchTrigger}
                />

                <div
                    className={`expand-grid border-t border-white/5 ${
                        showPicker ? 'expand-grid-open flex-1 min-h-0' : 'expand-grid-closed flex-none'
                    }`}
                >
                    <div className="min-h-0 overflow-hidden flex flex-col">
                        <div
                            ref={listRef}
                            onScroll={handleFoodScroll}
                            className="custom-scrollbar overflow-y-auto bg-[#374239] flex-1 min-h-0"
                        >
                            {mode === 'pairings' && filtered.map(ing => (
                                <div key={ing.id} onClick={() => handleSelect(ing)} className="p-3 hover:bg-white/5 cursor-pointer border-b border-white/5 last:border-0">{ing.title}</div>
                            ))}
                            {mode === 'nutrition' && searching && foods.length === 0 && (
                                <div className="p-3 text-sm text-slate-400">Searching...</div>
                            )}
                            {mode === 'nutrition' && !searching && foods.length === 0 && (
                                <div className="p-3 text-sm text-slate-400">No foods match</div>
                            )}
                            {mode === 'nutrition' && foodOffset > 0 && foods.length > 0 && (
                                <div className="p-2 text-[10px] uppercase tracking-widest text-[#5E7161]">Scroll up for the previous 50</div>
                            )}
                            {mode === 'nutrition' && foods.map(food => (
                                <div key={food.id} onClick={() => handleSelectFood(food)} className="p-3 hover:bg-white/5 cursor-pointer border-b border-white/5 last:border-0">
                                    <div>{food.name_en}</div>
                                    {food.name_fr && food.name_fr !== food.name_en && (
                                        <div className="text-xs text-slate-400">{food.name_fr}</div>
                                    )}
                                </div>
                            ))}
                            {mode === 'nutrition' && hasMoreFoods && foods.length > 0 && (
                                <div className="p-2 text-[10px] uppercase tracking-widest text-[#5E7161]">Scroll down for the next 50</div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {mode === 'nutrition' && selectedFood && !loading && (
                <div className="bg-[#374239] p-3 rounded shadow-xl flex-1 min-h-0 overflow-hidden flex flex-col">
                    <div className="flex-none mb-3">
                        <h2 className="text-sm font-bold">{selectedFood.name_en}</h2>
                        {selectedFood.name_fr !== selectedFood.name_en && (
                            <p className="text-xs text-slate-400">{selectedFood.name_fr}</p>
                        )}
                        <p className="text-[10px] uppercase tracking-widest text-[#5E7161] mt-1">
                            Per 100 g{selectedFood.group_en ? ` · ${selectedFood.group_en}` : ''}
                        </p>
                    </div>
                    <div className="overflow-y-auto custom-scrollbar pr-2 flex-1 min-h-0 space-y-4">
                        <div className="space-y-1">
                            {coreNutrients.map(nutrient => (
                                <div key={nutrient.code} className="flex justify-between border-b border-white/5 py-1 gap-3">
                                    <span className="text-sm">{nutrient.name_en}</span>
                                    <span className="text-sm font-bold shrink-0">{formatAmount(nutrient.amount_per_100g, nutrient.decimals)} {nutrient.unit}</span>
                                </div>
                            ))}
                        </div>
                        {otherNutrients.length > 0 && (
                            <div>
                                <h3 className="font-bold text-[10px] tracking-widest bg-slate-800 px-2 py-1 inline-block uppercase mb-2">All nutrients</h3>
                                <div className="space-y-1">
                                    {otherNutrients.map(nutrient => (
                                        <div key={nutrient.code} className="flex justify-between border-b border-white/5 py-1 gap-3">
                                            <span className="text-xs text-slate-300">{nutrient.name_en}</span>
                                            <span className="text-xs shrink-0">{formatAmount(nutrient.amount_per_100g, nutrient.decimals)} {nutrient.unit}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {mode === 'pairings' && selectedIngredient && !loading && (
                <div className="bg-[#374239] p-3 rounded shadow-xl flex-1 min-h-0 overflow-hidden flex flex-col">
                    <div className="flex flex-row gap-8 overflow-y-auto custom-scrollbar pr-2 flex-1 min-h-0">
                        <div className="flex-1 space-y-6">
                            {selectedIngredient.affinities?.length > 0 && (
                                <div>
                                    <h2 className="font-bold text-[10px] tracking-widest bg-slate-800 px-2 py-1 inline-block uppercase mb-2">Affinities</h2>
                                    <ul className="text-sm space-y-1">
                                        {selectedIngredient.affinities.map((a, i) => <li key={i} className="capitalize">{a}</li>)}
                                    </ul>
                                </div>
                            )}
                            {selectedIngredient.avoid?.length > 0 && (
                                <div>
                                    <h2 className="font-bold text-[10px] tracking-widest bg-[#452727] px-2 py-1 inline-block uppercase mb-2">Avoid</h2>
                                    <ul className="text-sm space-y-1">
                                        {selectedIngredient.avoid.map((a, i) => <li key={i} className="text-slate-500 line-through">{a}</li>)}
                                    </ul>
                                </div>
                            )}
                        </div>
                        <div className="flex-1">
                             <h2 className="font-bold text-[10px] tracking-widest bg-black px-2 py-1 inline-block uppercase mb-2">Scores</h2>
                             <div className="space-y-1">
                                {selectedIngredient.matches.map(([name, score], i) => (
                                    <div key={i} className="flex justify-between border-b border-white/5 py-1">
                                        <span className="text-xs lowercase">{name}</span>
                                        <span className={getScoreColor(score)}>{score}</span>
                                    </div>
                                ))}
                             </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default IngredientMatchChecker;
