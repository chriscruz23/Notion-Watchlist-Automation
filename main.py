import os

import tmdbsimple as tmdb
from dotenv import load_dotenv
from notion_client import Client

from ResultsExceptions import NoEntriesFoundException

# Load environment variables from .env file
load_dotenv()

# Constants
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Initialize Notion client and TMDB API
notion = Client(auth=NOTION_API_KEY)
tmdb.API_KEY = TMDB_API_KEY


def get_notion_entries():
    query = {
        "database_id": DATABASE_ID,
        "filter": {"property": "Name", "title": {"ends_with": ";"}},
    }
    response = notion.databases.query(**query)
    return response


def search_tmdb(title):
    search = tmdb.Search()
    response = search.multi(query=title)
    return response["results"][0] if response["results"] else None


def update_notion_page(page_id, tmdb_data):
    # Prepare the data to update in Notion
    update_data = {
        "Name": {"title": [{"text": {"content": tmdb_data.get("title", "")}}]},
        "Type": {"select": {"name": tmdb_data.get("type")}},
        "TMDB Rating": (
            {"number": round(tmdb_data.get("vote_average"), 1)}
            if tmdb_data.get("vote_average")
            else None
        ),
        "Director": {
            "rich_text": [
                {"text": {"content": ", ".join(tmdb_data.get("directors", []))}}
            ]
        },
        "Genre": {
            "multi_select": [{"name": item["name"]} for item in tmdb_data.get("genres")]
        },
        "Runtime": {"number": tmdb_data.get("runtime", None)},
        "VOD": {
            "multi_select": [
                {"name": provider} for provider in tmdb_data.get("providers", [])
            ]
        },
        "Trailer": {"url": tmdb_data.get("trailer_url", None)},
        "IMDb Page": (
            {"url": "https://www.imdb.com/title/{}/".format(tmdb_data.get("imdb_id"))}
            if tmdb_data.get("imdb_id")
            else None
        ),
        "Synopsis": {
            "rich_text": [{"text": {"content": tmdb_data.get("overview", "")}}]
        },
        "Release Date": (
            {"date": {"start": tmdb_data.get("release_date")}}
            if tmdb_data.get("release_date")
            else None
        ),
        "Cast": {
            "rich_text": [{"text": {"content": ", ".join(tmdb_data.get("cast", []))}}]
        },
        "Producer": {
            "rich_text": [
                {"text": {"content": ", ".join(tmdb_data.get("producers", []))}}
            ]
        },
        "Country of origin": (
            {
                "rich_text": [
                    {
                        "text": {
                            "content": tmdb_data.get("production_countries")[0]["name"]
                        }
                    }
                ]
            }
            if tmdb_data.get("production_countries")
            else None
        ),
        "Content Rating": {"select": {"name": tmdb_data.get("content_rating", None)}},
        "IMDb ID": {"rich_text": [{"text": {"content": tmdb_data.get("imdb_id", "")}}]},
        "IMG": {
            "files": [
                {
                    "type": "external",
                    "name": "Poster",
                    "external": {"url": tmdb_data.get("poster_path", "")},
                }
            ]
        },
        "Episodes": {"number": tmdb_data.get("number_of_episodes", None)},
        "Seasons": {"number": tmdb_data.get("number_of_seasons", None)},
        "Status": {"select": {"name": tmdb_data.get("status", "")}},
        "Language": {"select": {"name": tmdb_data.get("original_language", "")}},
        "Original Name": (
            {"rich_text": [{"text": {"content": tmdb_data.get("original_title")}}]}
            if tmdb_data.get("original_title") != tmdb_data.get("title")
            else None
        ),
        # Default values for specific properties
        "Watch Status": {"select": {"name": "Unwatched"}},
        "Rewatch?": {"checkbox": False},
        "Rating": {"select": {"name": "🤷‍♂️"}},
        "Format": {"select": {"name": "Unowned"}},
    }

    # Filter out None values
    update_data = {k: v for k, v in update_data.items() if v}

    # Update the page in Notion
    notion.pages.update(page_id, properties=update_data)
    notion.pages.update(
        page_id=page_id,
        icon={"type": "external", "external": {"url": tmdb_data["poster_path"]}},
    )
    notion.pages.update(
        page_id=page_id,
        cover={"type": "external", "external": {"url": tmdb_data["cover_url"]}},
    )


def additional_movie_info(movie):
    movie_details = {}
    movie_details["type"] = "Movie"
    movie_details["directors"] = []
    movie_details["producers"] = []
    movie_details["cast"] = []
    movie_details["content_rating"] = None
    movie_details["poster_path"] = None
    movie_details["cover_url"] = None

    credits = movie.credits()
    releases = movie.releases()

    # director/producer
    for member in credits["crew"]:
        if member["job"] == "Director":
            movie_details["directors"].append(member["name"])
        elif member["job"] == "Producer":
            movie_details["producers"].append(member["name"])

    # cast members
    for member in credits["cast"]:
        if (
            member["known_for_department"] == "Acting"
            and "(uncredited)" not in member["character"]
        ):
            movie_details["cast"].append(member["name"])

    # content rating
    for country in releases["countries"]:
        if country["iso_3166_1"] == "US":
            movie_details["content_rating"] = country["certification"]

    # IMG
    for image in movie.images()["posters"]:
        if image["iso_639_1"] == "en":
            movie_details["poster_path"] = (
                f"https://image.tmdb.org/t/p/w1280{image['file_path']}"
            )
            break

    # backdrop
    movie_details["cover_url"] = (
        f'https://image.tmdb.org/t/p/w3840_and_h2160_bestv2{movie.images()["backdrops"][0]["file_path"]}'
    )

    return movie_details


def main():
    try:
        response = get_notion_entries()
        notion_entries = response.get("results", [])
    except Exception as e:
        print(f"Error fetching Notion database: {e}")

    if not notion_entries:
        raise NoEntriesFoundException()

    for entry in notion_entries:
        title = entry["properties"]["Name"]["title"][0]["text"]["content"]
        page_id = entry["id"]

        # Search TMDB
        tmdb_result = search_tmdb(title.rstrip(";"))

        if not tmdb_result:
            raise NoEntriesFoundException()

        tmdb_id = tmdb_result["id"]
        tmdb_type = tmdb_result["media_type"]
        if tmdb_type == "movie":
            movie = tmdb.Movies(tmdb_id)
            tmdb_data = movie.info()

            for k, v in additional_movie_info(movie).items():
                tmdb_data[k] = v

        elif tmdb_type == "tv":
            tv = tmdb.TV(tmdb_id)
            tmdb_data = tv.info()
        else:
            continue

        update_notion_page(page_id, tmdb_data)


if __name__ == "__main__":
    main()
