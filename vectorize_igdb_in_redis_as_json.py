import os
import json
import numpy as np
import redis
from dotenv import load_dotenv
from redis.commands.search.field import TextField, TagField, NumericField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from sentence_transformers import SentenceTransformer
from config.index_names import GAMES_INDEX

from config.logger_config import setup_logger

# Setup logger
logger = setup_logger()

# Load environment variables
load_dotenv()

# Initialize global variables
REDIS_URL = os.getenv('GABS_REDIS_URL', "redis://default:secret42@localhost:6379")
DATA_FILE = "./data/games_list.json"
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Initialize Redis connection
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
logger.info("Redis connection established: %s", r.ping())

# Define the model
model = SentenceTransformer(MODEL_NAME)


def load_games_into_redis(data_file):
    """Load games into Redis from a single JSON file, using a single embedding for name, summary, and storyline."""
    with open(data_file, 'r', encoding="utf-8") as file:
        games_data = json.load(file)

    for game in games_data:
        # Concatenate name, summary, and storyline
        text_to_embed = game['name']
        if 'summary' in game:
            text_to_embed += ' ' + game['summary']
        if 'storyline' in game and game['storyline'].strip():
            text_to_embed += ' ' + game['storyline']

        # Generate a single embedding for the concatenated text
        unified_embedding = model.encode(text_to_embed).astype(np.float32).tolist()

        logger.info(f"Unified embedding for game {game['name']} generated.")

        # Prepare and load the game data into Redis with the unified embedding
        game_json = {
            'id': game['id'],
            'category': str(game.get('category', '')),
            'cover': game.get('cover', 0),
            'first_release_date': game.get('first_release_date', 0),
            'name': game['name'],
            'slug': game['slug'],
            'summary': game.get('summary', ''),
            'url': game['url'],
            'embedding': unified_embedding,  # Use the unified embedding
        }

        r.json().set(f"game:{game_json['id']}", "$", game_json)
        logger.info(f"Game {game_json['name']} loaded into Redis. ID: game:{game_json['id']}")


def create_games_index():
    """Create a games index in Redis if it doesn't exist, using a unified embedding field."""
    if GAMES_INDEX not in r.execute_command("FT._LIST"):
        index_def = IndexDefinition(prefix=["game:"], index_type=IndexType.JSON)
        schema = [
            TextField("$.name", as_name="name"),
            TagField("$.category", as_name="category"),
            NumericField("$.first_release_date", as_name="first_release_date"),
            TextField("$.description", as_name="description"),
            VectorField("$.embedding", "HNSW", {
                "TYPE": "FLOAT32", "DIM": 384, "DISTANCE_METRIC": "COSINE", "INITIAL_CAP": 1500
            }, as_name="embedding")  # Updated to use a single embedding field
        ]
        r.ft('games_idx').create_index(fields=schema, definition=index_def)
        logger.info("Games index updated with unified embedding field.")
    else:
        logger.info("Games index with unified embedding field already exists.")


def main(reindex=False):
    """Main function to control the flow of the script."""
    if reindex:
        logger.info("Reindexing...")
        create_games_index()
        load_games_into_redis(DATA_FILE)
    else:
        logger.info("Skipping reindexing.")


if __name__ == "__main__":
    reindex = input("Do you want to reindex everything? (yes/no): ").strip().lower() == "yes"
    main(reindex)
