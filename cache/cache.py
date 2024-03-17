import redis
import os
from datetime import timedelta

r = redis.Redis.from_url(os.getenv("GABS_REDIS_URL"))


def get_redis_object():
    return r


def cache_data(key, data, ttl=20):
    r.setex(key, timedelta(seconds=ttl), value=data)


def get_cached_data(key):
    return r.get(key)


def search_in_cache(index, query):
    # Assuming RedisSearch is configured and an index is created
    return r.ft(index).search(query)
