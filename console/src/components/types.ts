export interface DishSearch { id: number; name: string; }
export interface Instruction { step: number; text: string; }
export interface Ingredient { name: string; quantity: number | string; unit: string; }
export interface Component { name: string; instructions: Instruction[]; ingredients: Ingredient[]; }
export interface RecipeFull { id: number; name: string; dish_id: number; components: Component[]; }

export interface RecipeExtract {
  name: string;
  dish_id?: number | null;
  dish_name?: string;
  components: Component[];
}
export interface ChatTurn { role: 'user' | 'model'; text: string; }
export interface RecipeChatResponse { reply: string; recipes: RecipeExtract[]; }

import { API_PREFIX } from '../api/client';

export const API_BASE = `${API_PREFIX}/recipes`;