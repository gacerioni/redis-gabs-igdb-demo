import os
import time
import json

import redis
from dotenv import load_dotenv
from igdb.wrapper import IGDBWrapper

from config.index_names import GAMES_INDEX
from config.logger_config import setup_logger

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_ACCESS_TOKEN = os.getenv("TWITCH_CLIENT_ACCESS_TOKEN")

# Setup logger
logger = setup_logger()

r = redis.Redis.from_url(os.getenv("GABS_REDIS_URL"))


def fetch_all_games(wrapper):
    games = []
    offset = 0
    limit = 500
    has_more = True

    while has_more:
        logger.info("We have more games to fetch! Offset: {0}".format(offset))
        query = (f'fields name, category, cover, first_release_date, slug, storyline, summary, url; limit {limit}; '
                 f'offset {offset};')
        response = wrapper.api_request('games', query)
        current_batch = json.loads(response)

        if not current_batch:
            has_more = False
        else:
            games.extend(current_batch)
            offset += limit

        # Respect the rate limit: 4 requests per second
        time.sleep(1)  # Adjust based on actual performance and safety margin

    return games


def search_games_by_name(game_name):
    """
    Search for games by name.

    :param game_name: The name or partial name of the game to search for.
    :return: A list of games that match the search query.
    """
    index_name = GAMES_INDEX  # Assuming GAMES_INDEX is the name of your Redisearch index for games

    try:
        query_str = f"@name:({game_name}*)"  # Adjust based on your index's schema

        # Execute the search query against the index
        search_results = r.ft(index_name).search(query_str)

        # Extract the JSON data from the Document object and parse it
        games = []
        for document in search_results.docs:
            game_data = json.loads(document.json)
            dict_for_game = {"name": game_data["name"], "summary": game_data["summary"], "url": game_data["url"]}
            games.append(dict_for_game)

        logger.info(f"Found {len(games)} games for query '{game_name}'")
        return games

    except Exception as e:
        logger.error(f"Error searching games by name '{game_name}': {e}")
        return []



def main():
    wrapper = IGDBWrapper(CLIENT_ID, CLIENT_ACCESS_TOKEN)
    all_games = fetch_all_games(wrapper)
    print(f"Total games fetched: {len(all_games)}")
    # Here you can add your logic to persist the `all_games` list to a PostgreSQL table

    # Writing the list of games to a file
    with open('data/games_list.json', 'w', encoding='utf-8') as f:
        json.dump(all_games, f, ensure_ascii=False, indent=4)
    logger.info("The games list has been written to 'games_list.json'.")


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
