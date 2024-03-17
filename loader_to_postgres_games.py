import csv
import json

from dotenv import load_dotenv
from models.models import init_db, load_initial_data, Session

# Load environment variables
load_dotenv()


def load_csv_data(csv_file):
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        data = [row for row in reader]
    return data


def load_json_data(json_file):
    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def main():
    init_db()
    session = Session()
    data = load_json_data('data/games_list.json')
    load_initial_data(session, data)
    session.close()


if __name__ == "__main__":
    main()
