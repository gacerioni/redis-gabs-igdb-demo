import os
import time
from redis.exceptions import BusyLoadingError

import numpy as np
from flask import Flask, request, render_template, jsonify

from cache.redis_utils import wait_for_redis_to_load
from config.index_manager import ensure_indexes_exist
from config.logger_config import setup_logger
from config.metrics_config import CACHE_HITS, CACHE_MISSES, REQUEST_DURATION, HITS
from models.models import Session, Game, engine
from cache.cache import cache_data, get_cached_data, get_redis_object
import json
from dotenv import load_dotenv
from prometheus_client import make_wsgi_app, Histogram
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from books_vector_redis_demo import search_books_by_tag, get_book_recommendations, get_book_embedding, \
    recommend_games_by_book_embedding

# Load environment variables
load_dotenv()

# Setup logger
logger = setup_logger()

# Define a Histogram for tracking latencies with labels for cache and db
LATENCY = Histogram('service_latency_seconds', 'Service latency in seconds', ['type'])

app = Flask(__name__)


# ff_client = FeatureFlagClient()

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    start_time = time.time()
    query = request.form['query']
    cached_result = get_cached_data(query)

    # demo_json = ff_client.get_demo_variation()
    # logger.info("Type of demo_json: {0}".format(type(demo_json)))

    if cached_result:
        latency = time.time() - start_time
        CACHE_HITS.inc()
        HITS.labels(type='cache').inc()
        LATENCY.labels(type='cache').observe(latency)
        logger.info(f"Cache hit for query '{query}'. Latency: {latency:.3f} seconds.")
        return jsonify(data=json.loads(cached_result.decode('utf-8')), source='cache')
    else:
        session = Session()
        result = session.query(Game).filter(Game.name.contains(query)).all()

        latency = time.time() - start_time
        HITS.labels(type='db').inc()
        CACHE_MISSES.inc()
        LATENCY.labels(type='db').observe(latency)
        logger.info(f"Cache miss for query '{query}'. DB query latency: {latency:.3f} seconds.")
        result_json = [{'name': game.name,
                        'cover': game.cover,
                        'first_release_date': game.first_release_date.isoformat() if game.first_release_date else None,
                        'slug': game.slug,
                        'summary': game.summary,
                        'url': game.url}
                       for game in result]

        # Now it's safe to use json.dumps without a custom encoder
        json_data = json.dumps(result_json)
        cache_data(query, json_data)
        session.close()
        REQUEST_DURATION.observe(latency)
        return jsonify(data=result_json, source='db')


# Setup Prometheus metrics
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})


@app.route('/wipe_redis', methods=['GET'])
def wipe_redis():
    try:
        r = get_redis_object()
        r.flushdb()  # Assuming 'r' is your Redis connection object
        return jsonify({"success": True, "message": "Redis cache wiped successfully."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/wipe_postgres', methods=['GET'])
def wipe_postgres():
    try:
        # Assuming SoccerTeam is your SQLAlchemy model for the soccer_teams table
        Game.__table__.drop(engine)
        Game.__table__.create(engine)
        return jsonify({"success": True, "message": "Postgres Game table wiped successfully."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/books')
def books():
    return render_template('books.html')


@app.route('/search_books', methods=['POST'])
def search_books():
    tag = request.form['tag_query']
    books = search_books_by_tag(tag)
    return jsonify(books)


@app.route('/recommend_books', methods=['POST'])
def recommend_books():
    book_id = request.form['book_id']
    recommendations = get_book_recommendations(book_id)
    return jsonify(recommendations)


@app.route('/recommend_games', methods=['POST'])
def recommend_games():
    book_id = request.form['book_id']
    recommendations = recommend_games_by_book_embedding(book_id)
    return render_template('books.html', recommendations=recommendations)


if __name__ == "__main__":
    REDIS_URL = os.getenv("GABS_REDIS_URL")
    print("REDIS URL MAIN: {0}".format(REDIS_URL))
    wait_for_redis_to_load()

    # Ensure all indexes exist before starting the APP!
    ensure_indexes_exist()

    app.run(host='0.0.0.0', port=5000, debug=True)
