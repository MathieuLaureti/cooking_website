use axum::{extract::{State, Path}, Json, http::StatusCode};
use bb8_redis::redis::AsyncCommands;
use serde_json;
use std::collections::HashMap;
use crate::routes::AppState;
use crate::models::{Dish, SearchRecipe, FullRecipe, Recipe, RecipeComponent, Ingredient, Instruction, FullComponent, MatchChecker, MatchList};

pub async fn get_dishes(
    State(state): State<AppState>
) -> Result<Json<Vec<Dish>>, StatusCode> {
    let mut conn = state.redis_pool.get().await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let cache_key = "dishes:all";

    // Specify String return type via turbofish
    if let Ok(cached) = conn.get::<&str, String>(cache_key).await {
        if let Ok(dishes) = serde_json::from_str(&cached) {
            return Ok(Json(dishes));
        }
    }

    let dishes = sqlx::query_as::<_, Dish>("SELECT id, name FROM dish")
        .fetch_all(&state.pool).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    // Specify types for set_ex: <Key, Value, ReturnType>
    let _ : () = conn.set_ex::<&str, String, ()>(
        cache_key, 
        serde_json::to_string(&dishes).unwrap(), 
        3600
    ).await.unwrap_or(());

    Ok(Json(dishes))
}

pub async fn get_recipes(
    State(state): State<AppState>, 
    Path(dish_id): Path<i32>
) -> Result<Json<Vec<SearchRecipe>>, StatusCode> {
    let mut conn = state.redis_pool.get().await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let cache_key = format!("dish_recipes:{}", dish_id);

    if let Ok(cached) = conn.get::<String, String>(cache_key.clone()).await {
        if let Ok(data) = serde_json::from_str(&cached) {
            return Ok(Json(data));
        }
    }

    let recipes = sqlx::query_as::<_, SearchRecipe>("SELECT id, name FROM recipe WHERE dish_id = $1")
        .bind(dish_id)
        .fetch_all(&state.pool).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let _ : () = conn.set_ex::<String, String, ()>(
        cache_key, 
        serde_json::to_string(&recipes).unwrap(), 
        3600
    ).await.unwrap_or(());

    Ok(Json(recipes))
}

pub async fn get_full_recipe(
    State(state): State<AppState>, 
    Path(recipe_id): Path<i32>
) -> Result<Json<FullRecipe>, (StatusCode, String)> {
    let mut conn = state.redis_pool.get().await.map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    let cache_key = format!("full_recipe:{}", recipe_id);

    if let Ok(cached) = conn.get::<String, String>(cache_key.clone()).await {
        if let Ok(data) = serde_json::from_str(&cached) {
            return Ok(Json(data));
        }
    }

    let recipe = sqlx::query_as::<_, Recipe>("SELECT id, dish_id, name FROM recipe WHERE id = $1")
        .bind(recipe_id)
        .fetch_one(&state.pool).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let components = sqlx::query_as::<_, RecipeComponent>("SELECT id, recipe_id, name FROM recipe_component WHERE recipe_id = $1")
        .bind(recipe_id)
        .fetch_all(&state.pool).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let component_ids: Vec<i32> = components.iter().map(|c| c.id).collect();

    let all_ingredients = sqlx::query_as::<_, Ingredient>("SELECT id, component_id, name, quantity, unit FROM ingredient WHERE component_id = ANY($1)")
        .bind(&component_ids)
        .fetch_all(&state.pool).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let all_instructions = sqlx::query_as::<_, Instruction>("SELECT id, component_id, step, text FROM instruction WHERE component_id = ANY($1) ORDER BY step")
        .bind(&component_ids)
        .fetch_all(&state.pool).await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

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

    let full_recipe = FullRecipe {
        id: recipe.id,
        dish_id: recipe.dish_id,
        name: recipe.name,
        components: full_components,
    };

    let _ : () = conn.set_ex::<String, String, ()>(
        cache_key, 
        serde_json::to_string(&full_recipe).unwrap(), 
        3600
    ).await.unwrap_or(());

    Ok(Json(full_recipe))
}

pub async fn get_ingredients(
    State(state): State<AppState>
) -> Result<Json<Vec<MatchList>>, StatusCode> {
    let mut conn = state.redis_pool.get().await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let cache_key = "match_checker:list";

    if let Ok(cached) = conn.get::<&str, String>(cache_key).await {
        if let Ok(data) = serde_json::from_str(&cached) {
            return Ok(Json(data));
        }
    }

    let ingredients = sqlx::query_as::<_, MatchList>("SELECT id, title FROM match_checker")
        .fetch_all(&state.pool).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let _ : () = conn.set_ex::<&str, String, ()>(
        cache_key, 
        serde_json::to_string(&ingredients).unwrap(), 
        3600
    ).await.unwrap_or(());

    Ok(Json(ingredients))
}

pub async fn get_ingredient(
    State(state): State<AppState>, 
    Path(ingredient_id): Path<i32>
) -> Result<Json<MatchChecker>, StatusCode> {
    let mut conn = state.redis_pool.get().await.map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    let cache_key = format!("ingredient_detail:{}", ingredient_id);

    if let Ok(cached) = conn.get::<String, String>(cache_key.clone()).await {
        if let Ok(data) = serde_json::from_str(&cached) {
            return Ok(Json(data));
        }
    }

    let ingredient = sqlx::query_as::<_, MatchChecker>("SELECT id, title, avoid, affinities, matches FROM match_checker WHERE id = $1")
        .bind(ingredient_id)
        .fetch_one(&state.pool).await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let _ : () = conn.set_ex::<String, String, ()>(
        cache_key, 
        serde_json::to_string(&ingredient).unwrap(), 
        3600
    ).await.unwrap_or(());

    Ok(Json(ingredient))
}
