use sqlx::postgres::{PgPool, PgPoolOptions};
use std::env;
use std::time::Duration;

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