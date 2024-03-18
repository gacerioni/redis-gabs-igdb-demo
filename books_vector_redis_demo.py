import os
import json
import numpy as np
import redis
from dotenv import load_dotenv
from redis.commands.search.query import Query
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import TextField, TagField, NumericField, VectorField
from sentence_transformers import SentenceTransformer

from config.index_names import BOOKS_INDEX, UNIFIED_INDEX
from config.logger_config import setup_logger

# Setup logger
logger = setup_logger()

# Load environment variables
load_dotenv()

# Initialize global variables
REDIS_URL = os.getenv('GABS_REDIS_URL', "redis://default:secret42@localhost:6379")
DATA_FOLDER = "./data/books/"
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Initialize Redis connection
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
logger.info("Redis connection established: %s", r.ping())

# Define the model
model = SentenceTransformer(MODEL_NAME)


def load_books_into_redis(datasource_dir):
    """Load books into Redis from a specified directory."""
    for filename in os.listdir(datasource_dir):
        filepath = os.path.join(datasource_dir, filename)
        if os.path.isfile(filepath):
            with open(filepath, 'r', encoding="utf-8") as book_file:
                book_json = json.load(book_file)

                # Append the title and author to the description before encoding
                full_text = f"{book_json['title']} {book_json['author']} {book_json['description']}"

                book_json['embedding'] = model.encode(full_text).astype(np.float32).tolist()
                r.json().set(f"book:{book_json['id']}", "$", book_json)
                logger.info(f"{book_json['title']} processed and loaded into Redis. ID: book:{book_json['id']}",
                            book_json)


def create_books_index():
    """Create a books index in Redis if it doesn't exist."""
    if BOOKS_INDEX not in r.execute_command("FT._LIST"):
        index_def = IndexDefinition(prefix=["book:"], index_type=IndexType.JSON)
        schema = [
            TagField("$.title", as_name="title"),
            TagField("$.status", as_name="status"),
            TagField("$.author", as_name="author"),
            NumericField("$.year_published", as_name="year_published"),
            TextField("$.description", as_name="description"),
            VectorField("$.embedding", "HNSW", {
                "TYPE": "FLOAT32", "DIM": 384, "DISTANCE_METRIC": "COSINE", "INITIAL_CAP": 1500
            }, as_name="embedding")
        ]
        r.ft('books_idx').create_index(fields=schema, definition=index_def)
        logger.info("Books index created.")
    else:
        logger.info("Books index already exists.")


def get_recommendation(key):
    """Retrieve book recommendations based on vector similarity."""
    embedding = r.json().get(key, "$.embedding")
    embedding_as_blob = np.array(embedding, dtype=np.float32).tobytes()
    query = Query("*=>[KNN 5 @embedding $vec AS score]").return_field("$.title").sort_by("score", asc=True).dialect(
        2).paging(1, 5)
    results = r.ft("books_idx").search(query, query_params={"vec": embedding_as_blob})
    return results


def get_recommendation_by_range(key):
    embedding = r.json().get(key)
    embedding_as_blob = np.array(embedding['embedding'], dtype=np.float32).tobytes()
    q = Query("@embedding:[VECTOR_RANGE $radius $vec]=>{$YIELD_DISTANCE_AS: score}") \
        .return_fields("title") \
        .sort_by("score", asc=True) \
        .paging(1, 5) \
        .dialect(2)

    # Find all vectors within a radius from the query vector
    query_params = {
        "radius": 3,
        "vec": embedding_as_blob
    }

    res = r.ft("books_idx").search(q, query_params)
    return res


def get_books_by_author(author_name):
    """Retrieve books by a specific author."""
    query = f"@author:{{{author_name}}}"
    results = r.ft("books_idx").search(query)
    logger.info("Books by author %s: %s", author_name, results)
    return results


def get_books_by_title(title):
    """Retrieve books by title."""
    query = f"@title:({title})"
    results = r.ft("books_idx").search(query)
    logger.info("Books with title %s: %s", title, results)
    return results


def search_books_by_tag(tag):
    """
    Search books by any matching tag or text in Redis Search.
    Allows direct query syntax for broad matching.
    """
    logger.info("TAG BEING USED: %s", tag)
    try:
        # Correctly specify fields to return in the query itself
        query = Query(tag).return_fields("title", "author", "year_published", "description", "id").paging(0, 10)
        results = r.ft("books_idx").search(query)

        books = []
        for doc in results.docs:
            book_data = {
                "title": doc.title if "title" in doc.__dict__ else "Title not available",
                "author": doc.author if "author" in doc.__dict__ else "Author not available",
                "year_published": doc.year_published if "year_published" in doc.__dict__ else "Year not available",
                "description": doc.description if "description" in doc.__dict__ else "Description not available",
                "id": doc.id if "id" in doc.__dict__ else "ID not available"
            }
            books.append(book_data)

        logger.info(f"Books matching tag '{tag}': {books}")
        return books
    except Exception as e:
        logger.error(f"Error searching books by tag '{tag}': {e}")
        return []


def get_book_embedding(book_id):
    embedding = r.json().get(f"book:{book_id}", "$.embedding")
    return embedding


def auto_create_special_gabs_cross_model_game_book_index():
    """Automatically create a special unified index for games and books in Redis, if it doesn't exist."""
    if UNIFIED_INDEX not in r.execute_command("FT._LIST"):
        # Define the index with the correct name and prefix for both games and books
        index_def = IndexDefinition(prefix=["game:", "book:"], index_type=IndexType.JSON)

        # Simplify the schema to focus on the embedding field, and include fields for game name and potentially other relevant information
        schema = [
            TextField("$.name", as_name="name"),  # Assuming games and books have a 'name' field; adjust as needed
            TextField("$.summary", as_name="summary"),  # Keep description for full-text search
            # Remove fields that are no longer necessary due to the use of a single embedding field
            VectorField("$.embedding", "HNSW", {
                "TYPE": "FLOAT32", "DIM": 384, "DISTANCE_METRIC": "COSINE", "INITIAL_CAP": 1500
            }, as_name="embedding")  # Generic embedding field for both books and games
        ]

        # Create the index with the defined schema
        r.ft(UNIFIED_INDEX).create_index(fields=schema, definition=index_def)
        logger.info(f"{UNIFIED_INDEX} for games and books created.")
    else:
        logger.info(f"{UNIFIED_INDEX} for games and books already exists.")


def recommend_games_by_book_embedding(book_id):
    """
    Recommend games based on the book's embedding vector.
    This function uses the unified index for querying game recommendations.
    """
    try:
        # Ensure the special unified index exists
        auto_create_special_gabs_cross_model_game_book_index()

        # Retrieve the embedding for the given book ID
        embedding = r.json().get(f"book:{book_id}", "$.embedding")
        if not embedding:
            logger.info(f"No embedding found for book ID {book_id}")
            return []

        # Convert embedding to the appropriate format for Redis search
        embedding_as_blob = np.array(embedding, dtype=np.float32).tobytes()

        # Formulate the KNN query for the unified index
        query = Query("*=>[KNN 20 @embedding $vec AS score]").sort_by("score").paging(0, 20).dialect(2).return_fields(
            "name", "summary", "id", "score").sort_by("score", asc=True)

        # Execute the query on the unified index, passing the book's embedding
        results = r.ft(UNIFIED_INDEX).search(query, query_params={"vec": embedding_as_blob})

        # Pre-filter game entries based on their ID prefix before parsing the results
        game_results = [doc for doc in results.docs if doc.id.startswith("game:")]

        logger.info("GABS QUICK DEBUGGING: %s", game_results)

        # Parse the filtered game entries to extract relevant information
        recommended_games = [{
            "name": doc.__dict__.get('name', 'No name available'),  # Use 'name' instead of 'title'
            "summary": doc.__dict__.get('summary', 'No summary available'),
            "score": doc.__dict__.get('score', 0)
        } for doc in game_results]

        logger.info(f"Recommended games for book ID {book_id}: {recommended_games}")
        return recommended_games
    except Exception as e:
        logger.error(f"Error getting game recommendations for book ID {book_id}: {e}")
        return []


def get_book_recommendations(book_id):
    """
    Get book recommendations based on the book's embedding vector with improved error handling.
    """
    try:
        key = f"book:{book_id}"
        embedding = r.json().get(key, "$.embedding")
        if not embedding:
            logger.info(f"No embedding found for book ID {book_id}")
            return []

        embedding_as_blob = np.array(embedding, dtype=np.float32).tobytes()
        query = Query("*=>[KNN 5 @embedding $vec AS score]").sort_by("score").paging(0, 5).dialect(2).return_fields(
            "title", "author", "id", "score").sort_by("score", asc=True)
        results = r.ft("books_idx").search(query, query_params={"vec": embedding_as_blob})

        recommendations = [{
            "title": doc.title,
            "author": doc.author,
            "id": doc.id,
            "score": doc.__dict__.get('score', 0)  # Adjusting score access
        } for doc in results.docs]

        logger.info(f"Recommendations for book ID {book_id}: {recommendations}")
        return recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations for book ID {book_id}: {e}")
        return []


def main(reindex=False):
    """Main function to control the flow of the script."""
    if reindex:
        logger.info("Reindexing...")
        load_books_into_redis(DATA_FOLDER)
        create_books_index()
    else:
        logger.info("Skipping reindexing.")

    # Demonstrate vector search usage - Lets use Harry Potter as an example (Gabs hehe)
    for book_id in ['89111', '89117']:
        recommendations = get_recommendation(f'book:{book_id}')
        recommendations_by_range = get_recommendation_by_range(f'book:{book_id}')
        logger.info("Recommendations for book ID %s: %s", book_id, recommendations)
        logger.info("Recommendations by range for book ID %s: %s", book_id, recommendations_by_range)


if __name__ == "__main__":
    reindex = input("Do you want to reindex everything? (yes/no): ").strip().lower() == "yes"
    main(reindex)
