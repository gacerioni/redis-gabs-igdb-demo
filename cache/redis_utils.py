import os
import time

import redis
from dotenv import load_dotenv
from redis import BusyLoadingError

from config.logger_config import setup_logger

# Setup logger
logger = setup_logger()

# Load environment variables
load_dotenv()

r = redis.Redis.from_url(os.getenv("GABS_REDIS_URL"))


def wait_for_redis_to_load(redis_client=r):
    while True:
        try:
            # Attempt to ping Redis
            redis_client.ping()
            print("Redis is ready to accept connections.")
            break  # Exit loop if ping is successful
        except BusyLoadingError:
            print("Redis is loading the dataset in memory, waiting...")
            time.sleep(5)  # Wait for 5 seconds before retrying
