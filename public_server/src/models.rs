use serde::Serialize;
use sqlx::FromRow;

#[derive(Debug, Serialize, FromRow)]
pub struct Dish {
    pub id: i32,
    pub name: Option<String>,
}

#[derive(Debug, Serialize, FromRow)]
pub struct Recipe {
    pub id: i32,
    pub dish_id: i32,
    pub name: Option<String>,
}

#[derive(Debug, Serialize, FromRow)]
pub struct SearchRecipe {
    pub id: i32,
    pub name: Option<String>,
}

#[derive(Debug, Serialize, FromRow)]
pub struct RecipeComponent {
    pub id: i32,
    pub recipe_id: i32,
    pub name: Option<String>,
}

#[derive(Debug, Serialize, FromRow)]
pub struct Ingredient {
    pub id: i32,
    pub component_id: i32,
    pub name: String,
    pub quantity: String,
    pub unit: String,
}

#[derive(Debug, Serialize, FromRow)]
pub struct Instruction {
    pub id: i32,
    pub component_id: i32,
    pub step: i32,
    pub text: String,
}

#[derive(Debug, Serialize, FromRow)]
pub struct MatchChecker {
    pub id: i32,
    pub title: String,
    pub avoid: Vec<String>,
    pub affinities: Vec<String>,
    pub matches: serde_json::Value, 
}
#[derive(Debug, Serialize, FromRow)]
pub struct MatchList {
    pub id: i32,
    pub title: String,
}

#[derive(Debug, Serialize)]
pub struct FullRecipe {
    pub id: i32,
    pub name: Option<String>,
    pub components: Vec<FullComponent>,
}

#[derive(Debug, Serialize)]
pub struct FullComponent {
    pub id: i32,
    pub name: Option<String>,
    pub ingredients: Vec<Ingredient>,
    pub instructions: Vec<Instruction>,
}