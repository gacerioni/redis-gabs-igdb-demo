import os

from flask import Flask, request, render_template, jsonify

from cache.redis_utils import wait_for_redis_to_load
from config.index_manager import ensure_indexes_exist
from config.logger_config import setup_logger
from dotenv import load_dotenv
from prometheus_client import make_wsgi_app, Histogram
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from books_vector_redis_demo import search_books_by_tag, get_book_recommendations, get_book_embedding, \
    recommend_games_by_book_embedding
from twitch_igdb_games_to_json import search_games_by_name

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
    return render_template('books.html')


# Setup Prometheus metrics
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})


@app.route('/books')
def books():
    return render_template('books.html')


@app.route('/search_books', methods=['POST'])
def search_books():
    tag = request.form['tag_query']
    books = search_books_by_tag(tag)
    return jsonify(books)


@app.route('/search_games', methods=['POST'])
def search_games():
    game_name = request.form['game_query']
    games = search_games_by_name(game_name)
    return jsonify(games)


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
    #wait_for_redis_to_load()

    # Ensure all indexes exist before starting the APP!
    #ensure_indexes_exist()

    app.run(host='0.0.0.0', port=5000, debug=True)
