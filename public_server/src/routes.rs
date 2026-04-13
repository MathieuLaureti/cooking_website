use axum::{routing::get, Router};
use sqlx::PgPool;
use crate::handlers;
use redis;
use bb8_redis::{bb8, RedisConnectionManager};

#[derive(Clone)]
pub struct AppState {
    pub pool: sqlx::PgPool,
    pub redis_pool: bb8::Pool<RedisConnectionManager>,
}


pub fn create_router(pool: PgPool,redis_pool: bb8::Pool<RedisConnectionManager>) -> Router {
    let state = AppState {
        pool,
        redis_pool,
    };
    Router::new()
        .route("/health", get(|| async { "Hello World" }))
        .route("/recipes/dishes", get(handlers::get_dishes))
        .route("/recipes/recipes/:dish_id", get(handlers::get_recipes))
        .route("/recipes/recipe/:recipe_id", get(handlers::get_full_recipe))
        .route("/match_checker/ingredients", get(handlers::get_ingredients))
        .route("/match_checker/ingredient/:ingredient_id", get(handlers::get_ingredient))
        .with_state(state) 
}
