mod routes;
mod database;
mod handlers;
mod models;

use axum::{
    routing::get,
    Router,
};

#[tokio::main]
async fn main() {
    let pool = database::create_pool().await;
    let app = routes::create_router(pool);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:6668").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}