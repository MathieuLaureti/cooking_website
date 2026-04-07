use axum::{routing::get, Router};
use sqlx::PgPool;
use crate::handlers;

pub fn create_router(pool: PgPool) -> Router {
    Router::new()
        .route("/health", get(|| async { "Hello World" }))
        .route("/recipes/dishes", get(handlers::get_dishes))
        .route("/recipes/recipes/:dish_id", get(handlers::get_recipes))
        .route("/recipes/recipe/:recipe_id", get(handlers::get_full_recipe))
        .route("/match_checker/ingredients", get(handlers::get_ingredients))
        .route("/match_checker/ingredient/:ingredient_id", get(handlers::get_ingredient))
        .with_state(pool) 
}
