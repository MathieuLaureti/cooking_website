use sqlx::postgres::{PgPool, PgPoolOptions};
use std::env;
use std::time::Duration;
use redis::Client;
use bb8_redis::{bb8, RedisConnectionManager};

pub async fn create_redis_pool() -> bb8::Pool<RedisConnectionManager> {
    let redis_url = env::var("REDIS_URL").unwrap_or_else(|_| "redis://cw_redis_test:6379".to_string());
    
    let manager = RedisConnectionManager::new(redis_url.clone())
        .expect("Failed to create Redis connection manager");

    bb8::Pool::builder()
        .max_size(20)
        .build(manager)
        .await
        .expect("Redis pool failure")
}

pub async fn create_pool() -> PgPool {
    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL not set");
    let pool = PgPoolOptions::new()
        .max_connections(5)
        .acquire_timeout(Duration::from_secs(3))
        .connect(&database_url)
        .await;

    match pool {
        Ok(p) => {
            if let Err(e) = sqlx::query("SELECT 1").execute(&p).await {
                panic!("Connected to DB, but query failed: {}", e);
            }
            println!("Database connection verified.");
            p
        }
        Err(e) => {
            panic!("Could not connect to database at {}: {}", database_url, e);
        }
    }
}
