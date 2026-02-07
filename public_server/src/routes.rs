use axum::{routing::get, Router};
use sqlx::PgPool;
use crate::handlers;

pub fn create_router(pool: PgPool) -> Router {
    Router::new()
        .route("/", get(|| async { "Hello, World!" }))
        .route("/dishes", get(handlers::get_dishes))
        .route("/recipes/:dish_id", get(handlers::get_recipes))
        .route("/recipe/:recipe_id", get(handlers::get_full_recipe))
        .route("/ingredients", get(handlers::get_ingredients))
        .route("/ingredient/:ingredient_id", get(handlers::get_ingredient))
        .with_state(pool) 
}