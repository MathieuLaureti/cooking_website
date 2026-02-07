use axum::{extract::{State,Path}, Json, http::StatusCode};
use sqlx::PgPool;
use crate::models::{Dish,SearchRecipe, FullRecipe, Recipe, RecipeComponent, Ingredient, Instruction, FullComponent, MatchChecker, MatchList};
use std::collections::HashMap;

pub async fn get_dishes(
    State(pool): State<PgPool>
) -> Result<Json<Vec<Dish>>, StatusCode> {
    let dishes = sqlx::query_as::<_, Dish>("SELECT id, name FROM dish")
        .fetch_all(&pool)
        .await
        .map_err(|e| {
            eprintln!("Database error: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;
    Ok(Json(dishes))
}

pub async fn get_recipes(State(pool): State<PgPool>, Path(dish_id): Path<i32>) -> Result<Json<Vec<SearchRecipe>>, StatusCode> {
    let recipes = sqlx::query_as::<_, SearchRecipe>("SELECT id, name FROM recipe WHERE dish_id = $1")
        .bind(dish_id)
        .fetch_all(&pool)
        .await
        .map_err(|e| {
            eprintln!("Database error: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;
    Ok(Json(recipes))
}

pub async fn get_full_recipe(State(pool): State<PgPool>, Path(recipe_id): Path<i32>) -> Result<axum::Json<FullRecipe>, (axum::http::StatusCode, String)> {
    let recipe = sqlx::query_as::<_, Recipe>(
        "SELECT id, dish_id, name FROM recipe WHERE id = $1"
    )
    .bind(recipe_id)
    .fetch_one(&pool).await
    .map_err(|e| (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let components = sqlx::query_as::<_, RecipeComponent>(
        "SELECT id, recipe_id, name FROM recipe_component WHERE recipe_id = $1"
    )
    .bind(recipe_id)
    .fetch_all(&pool).await
    .map_err(|e| (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let component_ids: Vec<i32> = components.iter().map(|c| c.id).collect();

    let all_ingredients = sqlx::query_as::<_, Ingredient>(
        "SELECT id, component_id, name, quantity, unit FROM ingredient WHERE component_id = ANY($1)"
    )
    .bind(&component_ids)
    .fetch_all(&pool).await
    .map_err(|e| (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let all_instructions = sqlx::query_as::<_, Instruction>(
        "SELECT id, component_id, step, text FROM instruction WHERE component_id = ANY($1) ORDER BY step"
    )
    .bind(&component_ids)
    .fetch_all(&pool).await
    .map_err(|e| (axum::http::StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let mut ing_map: HashMap<i32, Vec<Ingredient>> = HashMap::new();
    for ing in all_ingredients {
        ing_map.entry(ing.component_id).or_default().push(ing);
    }

    let mut ins_map: HashMap<i32, Vec<Instruction>> = HashMap::new();
    for ins in all_instructions {
        ins_map.entry(ins.component_id).or_default().push(ins);
    }

    let full_components = components.into_iter().map(|c| {
        let cid = c.id;
        FullComponent {
            id: cid,
            name: c.name,
            ingredients: ing_map.remove(&cid).unwrap_or_default(),
            instructions: ins_map.remove(&cid).unwrap_or_default(),
        }
    }).collect();

    Ok(axum::Json(FullRecipe {
        id: recipe.id,
        name: recipe.name,
        components: full_components,
    }))
}

pub async fn get_ingredients(State(pool): State<PgPool>) -> Result<Json<Vec<MatchList>>, StatusCode> {
    let ingredients = sqlx::query_as::<_, MatchList>("SELECT id, title FROM match_checker")
        .fetch_all(&pool)
        .await
        .map_err(|e| {
            eprintln!("Database error: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;
    Ok(Json(ingredients))
}

pub async fn get_ingredient(State(pool): State<PgPool>, Path(ingredient_id): Path<i32>) -> Result<Json<MatchChecker>, StatusCode> {
    let ingredient = sqlx::query_as::<_, MatchChecker>("SELECT id, title, avoid, affinities, matches FROM match_checker WHERE id = $1")
        .bind(ingredient_id)
        .fetch_one(&pool)
        .await
        .map_err(|e| {
            eprintln!("Database error: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;
    Ok(Json(ingredient))
}