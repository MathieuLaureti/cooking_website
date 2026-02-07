use axum::{routing::get, Router};
use sqlx::PgPool;
use crate::handlers;

pub fn create_router(pool: PgPool) -> Router {
    Router::new()
        .route("/", get(|| async { "Hello, World!" }))
        .route("/dishes", get(handlers::get_dishes))
        .with_state(pool) 
}