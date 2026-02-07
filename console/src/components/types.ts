export interface DishSearch { id: number; name: string; }
export interface Instruction { step: number; text: string; }
export interface Ingredient { name: string; quantity: number; unit: string; }
export interface Component { name: string; instructions: Instruction[]; ingredients: Ingredient[]; }
export interface RecipeFull { id: number; name: string; dish_id: number; components: Component[]; }

export const API_BASE = 'http://192.168.2.106/api/recipes';