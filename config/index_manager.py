import os

from dotenv import load_dotenv
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
import redis

from books_vector_redis_demo import create_books_index, auto_create_special_gabs_cross_model_game_book_index
from config.logger_config import setup_logger
from vectorize_igdb_in_redis_as_json import create_games_index

# Setup logger
logger = setup_logger()

# Load environment variables
load_dotenv()

# Initialize global variables
REDIS_URL = os.getenv('GABS_REDIS_URL', "redis://default:secret42@localhost:6379")

# Initialize Redis connection
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
logger.info("Redis connection established: %s", r.ping())


def ensure_indexes_exist():
    create_books_index()
    create_games_index()
    auto_create_special_gabs_cross_model_game_book_index()
