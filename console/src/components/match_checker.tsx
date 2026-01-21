import React, { useState, useEffect, type ChangeEvent } from 'react';
import axios from 'axios';

const API_BASE = 'http://192.168.2.106:81/api/match_checker';

interface MatchCheckerShort { id: number; title: string; }
interface MatchCheckerFull extends MatchCheckerShort { 
    avoid: string[]; 
    affinities: string[]; 
    matches: [string, number][]; 
}

const IngredientMatchChecker: React.FC<{isActive: boolean, onSearchTrigger: () => void}> = ({ isActive, onSearchTrigger }) => {
    const [ingredients, setIngredients] = useState<MatchCheckerShort[]>([]);
    const [searchTerm, setSearchTerm] = useState<string>('');
    const [selectedIngredient, setSelectedIngredient] = useState<MatchCheckerFull | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => { if (!isActive) { setSelectedIngredient(null); setSearchTerm(''); } }, [isActive]);
    useEffect(() => { axios.get(`${API_BASE}/ingredient_list`).then(res => setIngredients(res.data)); }, []);

    const handleSelect = async (ing: MatchCheckerShort) => {
        setLoading(true); 
        setSearchTerm(ing.title);
        try {
            const res = await axios.get<MatchCheckerFull>(`${API_BASE}/get_ingredient/${ing.id}`);
            setSelectedIngredient(res.data);
        } finally { setLoading(false); }
    };

    const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
        setSearchTerm(e.target.value);
        if (e.target.value.length > 0) onSearchTrigger();
        if (selectedIngredient) setSelectedIngredient(null);
    };

    const filtered = ingredients.filter(ing => ing.title.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const getScoreColor = (score: number) => {
        switch (score) {
            case 4: return "text-[#FFA500] font-black"; 
            case 3: return "text-[#FFD700] font-bold";
            case 2: return "text-[#F1F5F9] font-medium";
            default: return "text-slate-400 font-light opacity-60";
        }
    };

    return (
        <div className="flex flex-col max-h-[400px]">
            <div className="bg-[#374239] rounded overflow-hidden shadow-xl flex-none">
                <div className="flex items-center justify-between p-2 px-4 border-b border-white/5 bg-black/20">
                    <span className="uppercase tracking-[0.2em] text-[#5E7161] font-bold text-[13px] sm:text-[10px]">
                        {selectedIngredient ? `Analysis / ${selectedIngredient.title}` : 'Ingredient Matcher'}
                    </span>
                    {selectedIngredient && (
                        <button onClick={() => { setSelectedIngredient(null); setSearchTerm(''); }} className="text-[10px] uppercase underline opacity-60 hover:opacity-100">Clear</button>
                    )}
                </div>

                <input 
                    type="text" 
                    className="w-full p-4 text-lg outline-none bg-transparent" 
                    placeholder="Search ingredient pairings..." 
                    value={searchTerm} 
                    onChange={handleInputChange} 
                />

                {!selectedIngredient && searchTerm && (
                    <div className="custom-scrollbar overflow-y-auto bg-[#374239] border-t border-white/5 max-h-48">
                        {filtered.map(ing => (
                            <div key={ing.id} onClick={() => handleSelect(ing)} className="p-3 hover:bg-white/5 cursor-pointer border-b border-white/5 last:border-0">{ing.title}</div>
                        ))}
                    </div>
                )}
            </div>

            {selectedIngredient && !loading && (
                <div className="bg-[#374239] mt-2 p-3 rounded shadow-xl flex-1 min-h-0 overflow-hidden flex flex-col animate-in fade-in zoom-in-95">
                    <div className="flex flex-row gap-8 overflow-y-auto custom-scrollbar pr-2">
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