import os
import time
import json
from dotenv import load_dotenv
from igdb.wrapper import IGDBWrapper
from config.logger_config import setup_logger

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
CLIENT_ACCESS_TOKEN = os.getenv("TWITCH_CLIENT_ACCESS_TOKEN")

# Setup logger
logger = setup_logger()


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
