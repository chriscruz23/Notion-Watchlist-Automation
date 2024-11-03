import json
import os
from pprint import pp

from dotenv import load_dotenv

from results_exceptions import NoEntriesFoundException
from utils import NotionHandler, TMDBHandler

# Load environment variables from .env file
load_dotenv()

# Constants
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")

# Language codes
with open("utils/iso_639_1_languages.json", "r") as json_file:
    iso_639_1_languages = json.load(json_file)

# Initialize Notion client and TMDB API
notion = NotionHandler(NOTION_API_KEY, DATABASE_ID)
tmdb = TMDBHandler(TMDB_API_KEY)


def update_notion_entries(notion_handler, tmdb_handler):
    notion_entries = notion_handler.get_entries_to_update()

    if not notion_entries:
        raise NoEntriesFoundException("No entries found in Notion.")

    for entry in notion_entries:
        title = entry["properties"]["Title"]["title"][0]["plain_text"].rstrip(";")
        page_id = entry["id"]

        # Search TMDb and handle multiple results if needed
        try:
            cleaned_data = tmdb_handler.get_cleaned_media_data(title=title)
            pp(cleaned_data)
        except ValueError as e:
            print(f"Error: {e}")


# update_notion_entries(notion, tmdb)

results = tmdb.search_media("The Dark Knight")
result = results[0]
tmdb_data = tmdb.fetch_media_details(result)
print(json.dumps(tmdb.clean_media_data(tmdb_data, "movie"), indent=4))


# raw_data = tmdb.fetch_media_details()
