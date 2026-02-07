use serde::Serialize;
use sqlx::FromRow;

#[derive(Debug, Serialize, FromRow)]
pub struct Dish {
    pub id: i32,
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
pub struct MatchChecker {
    pub id: i32,
    pub title: String,
    pub avoid: Vec<String>,
    pub affinities: Vec<String>,
    pub matches: serde_json::Value, //JSONB
}