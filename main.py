import json
import os

import tmdbsimple as tmdb
from dotenv import load_dotenv
from notion_client import Client

from ResultsExceptions import NoEntriesFoundException

# load environment variables from .env file
load_dotenv()

# constants
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# language codes
with open("utils/iso_639_1_languages.json", "r") as json_file:
    iso_639_1_languages = json.load(json_file)

# Initialize Notion client and TMDB API
notion = Client(auth=NOTION_API_KEY)
tmdb.API_KEY = TMDB_API_KEY


def get_notion_entries(title=None):
    if title:
        query = {
            "database_id": DATABASE_ID,
            "filter": {"property": "Title", "title": {"equals": title}},
        }
    else:
        query = {
            "database_id": DATABASE_ID,
            "filter": {"property": "Title", "title": {"ends_with": ";"}},
        }
    response = notion.databases.query(**query)
    return response


def search_tmdb(title):
    search = tmdb.Search()
    response = search.multi(query=title)
    return response["results"][0] if response["results"] else None


def update_notion_page(page_id, tmdb_data):
    # prepare the data to update in Notion
    update_data = {
        "Title": {"title": [{"text": {"content": tmdb_data.get("title", None)}}]},
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
            {"url": f"https://www.imdb.com/title/{tmdb_data.get('imdb_id')}/"}
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
        "Country of Origin": (
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
        "Poster": {
            "files": [
                {
                    "type": "external",
                    "name": "Poster",
                    "external": {"url": tmdb_data.get("poster_path", None)},
                }
            ]
        },
        "Episodes": {"number": tmdb_data.get("number_of_episodes", None)},
        "Seasons": {"number": tmdb_data.get("number_of_seasons", None)},
        "Status": {"select": {"name": tmdb_data.get("status", "")}},
        "Original Language": {
            "select": {
                "name": iso_639_1_languages[tmdb_data.get("original_language", "")]
            }
        },
        "Original Title": (
            {"rich_text": [{"text": {"content": tmdb_data.get("original_title")}}]}
            if tmdb_data.get("original_title") != tmdb_data.get("title")
            else None
        ),
        # default values for specific properties
        "Watch Status": {"select": {"name": "Unwatched"}},
        "Rewatch": {"checkbox": False},
        "Rating": {"select": {"name": "🤷‍♂️"}},
        "Format": {"select": {"name": "Unowned"}},
    }

    # filter out None values
    update_data = {k: v for k, v in update_data.items() if v}

    # update the page in Notion
    notion.pages.update(page_id, properties=update_data)
    # set the icon and cover
    notion.pages.update(
        page_id=page_id,
        icon={"type": "external", "external": {"url": tmdb_data.get("poster_path")}},
    )
    notion.pages.update(
        page_id=page_id,
        cover={"type": "external", "external": {"url": tmdb_data.get("backdrop_path")}},
    )


def get_movie_data(tmdb_result):
    movie = tmdb.Movies(tmdb_result["id"])
    movie_data = movie.info(
        append_to_response=["watch/providers,credits,release_dates,videos"]
    )

    # media type
    movie_data["type"] = tmdb_result["media_type"].capitalize()

    # directors & producers
    for member in movie_data["credits"]["crew"]:
        if member["job"] == "Director":
            movie_data.setdefault("directors", []).append(member["name"])
        elif member["job"] == "Producer":
            movie_data.setdefault("producers", []).append(member["name"])

    # cast members
    for member in movie_data["credits"]["cast"]:
        if (
            member["known_for_department"] == "Acting"
            and "(uncredited)" not in member["character"]
        ):
            movie_data.setdefault("cast", []).append(member["name"])

    # content rating
    for result in movie_data["release_dates"]["results"]:
        if result["iso_3166_1"] == "US":
            for date in result["release_dates"]:
                if date["certification"]:
                    movie_data["content_rating"] = date["certification"]
                    break
            if movie_data["content_rating"]:
                break

    # images
    movie_data["backdrop_path"] = (
        f'https://image.tmdb.org/t/p/original{movie_data["backdrop_path"]}'
    )
    movie_data["poster_path"] = (
        f'https://image.tmdb.org/t/p/original{movie_data["poster_path"]}'
    )

    # official trailer
    for trailer in movie_data["videos"]["results"]:
        if trailer["official"] == True:
            movie_data["trailer_url"] = (
                f"https://www.youtube.com/watch?v={trailer['key']}"
            )

    # vod providers
    movie_data["providers"] = [
        provider["provider_name"]
        for provider in movie_data.get("watch/providers", {})
        .get("results", {})
        .get("US", {})
        .get("rent", [])
    ]

    return movie_data


def main():
    try:
        response = get_notion_entries()
        notion_entries = response.get("results", [])
    except Exception as e:
        print(f"Error fetching Notion database: {e}")

    if not notion_entries:
        raise NoEntriesFoundException("No entries found in Notion.")

    for entry in notion_entries:
        title = entry["properties"]["Title"]["title"][0]["text"]["content"].rstrip(";")
        page_id = entry["id"]

        # Search TMDB
        tmdb_result = search_tmdb(title)

        if tmdb_result:
            tmdb_type = tmdb_result["media_type"]
            if tmdb_type == "movie":
                tmdb_data = get_movie_data(tmdb_result)
            elif tmdb_type == "tv":
                # tv = tmdb.TV(tmdb_id)
                # tmdb_data = tv.info()
                pass
            else:
                continue

        update_notion_page(page_id, tmdb_data)


if __name__ == "__main__":
    main()
