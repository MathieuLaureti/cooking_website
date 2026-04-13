import redis.asyncio as redis

# Create a constrained connection pool
pool = redis.BlockingConnectionPool.from_url(
    "redis://cache:6379/0",
    max_connections=1500,
    timeout=5.0,
    decode_responses=True,
)

cache = redis.Redis(connection_pool=pool)
