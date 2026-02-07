use axum::{extract::State, Json, http::StatusCode};
use sqlx::PgPool;
use crate::models::Dish;

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