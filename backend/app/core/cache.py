"""
Ascendra — Redis Cache & Token Blacklisting.
"""

import logging
from redis import asyncio as aioredis
from app.config import settings

logger = logging.getLogger("ascendra.cache")

# Global Redis client instance
redis_client = None

async def init_redis():
    """Initialize Redis connection pool."""
    global redis_client
    clean_url = settings.REDIS_URL.replace("ssl_cert_reqs=CERT_NONE", "ssl_cert_reqs=none")
    kwargs = {"encoding": "utf-8", "decode_responses": True}
    if "rediss://" in clean_url:
        kwargs["ssl_cert_reqs"] = "none"
    redis_client = aioredis.from_url(clean_url, **kwargs)
    logger.info("Redis connection established.")

async def close_redis():
    """Close Redis connection."""
    if redis_client:
        await redis_client.close()

async def blacklist_token(jti: str, expires_in_seconds: int) -> None:
    """
    Store a revoked JWT ID (JTI) in Redis until it naturally expires.
    """
    if not redis_client:
        return
    
    # Prefix the key to avoid collisions
    key = f"revoked_jti:{jti}"
    # Ensure expires_in_seconds is at least 1 to avoid Redis errors
    ttl = max(1, expires_in_seconds)
    
    await redis_client.setex(key, ttl, "revoked")
    logger.debug(f"Blacklisted token jti={jti} for {ttl}s")

async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a given JWT ID (JTI) has been revoked.
    """
    if not redis_client:
        return False
        
    key = f"revoked_jti:{jti}"
    exists = await redis_client.exists(key)
    return exists > 0
