import logging
from typing import Any, Dict, List

import TMDB_API
import tmdbsimple
from tmdbsimple import TV, Movies, Search

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Logs to console
        logging.FileHandler("logs/notion.log"),  # Logs to a file
    ],
)

# Initialize a logger for the module
logger = logging.getLogger(__name__)


class TMDBHandler:
    def __init__(self, api_key: str | None) -> None:
        tmdbsimple.API_KEY = api_key

        try:
            # Attempt a test search to verify the API key is valid
            test_search = Search()
            test_search.multi(query="test")
            logger.info("TMDBHandler initialized successfully with API key.")
        except Exception as e:
            logger.critical("Failed to set API key for TMDBHandler", exc_info=True)
            raise ValueError("Invalid API key for TMDBHandler.") from e

    def search_media(self, title: str):
        """
        Search TMDb for a given title, which could be a movie or TV show.
        Returns a list of search results.
        """
        try:
            search = Search()
            response = search.multi(query=title)
            results = response.get("results", [])
            if not results:
                logger.warning(f"No results found for title: '{title}'")
            else:
                logger.info(f"Found {len(results)} result(s) for title: '{title}'")
            return results
        except Exception as e:
            logger.error(f"Error searching for title '{title}': {e}", exc_info=True)
            raise

    # FIXME This only works with movies right now
    def fetch_media_details(self, tmdb_result):
        """
        Fetch detailed data for a specific media item, whether it's a movie or TV show.
        """
        try:
            media_type = tmdb_result.get("media_type")
            media_id = tmdb_result.get("id")

            if media_type == "movie":
                media = Movies(media_id)
            elif media_type == "tv":
                media = TV(media_id)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            raw_data = media.info(
                append_to_response=["watch/providers,credits,release_dates,videos"]
            )
            logger.info(f"Fetched details for {media_type} with ID {media_id}")
            return raw_data

        except ValueError as e:
            logger.error(f"Error with media type: {media_type}", exc_info=True)
        except AttributeError as e:
            logger.error(f"Error with tmdb result: {tmdb_result}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error fetching info for media ID {media_id}", exc_info=True)
            raise

    def clean_media_data(self, tmdb_data, media_type):
        # Extract and format desired TMDb fields

        cleaned_data = {}
        if media_type == "movie":

            # US title
            tmdb_data["title"] = tmdb_data.pop("title", None)

            # Media type
            tmdb_data["type"] = media_type.capitalize()

            # Tagline
            tmdb_data["tagline"] = tmdb_data.pop("tagline", None)

            # TMDB rating
            if tmdb_data.get("vote_average"):
                tmdb_data["tmdb_rating"] = round(tmdb_data.pop("vote_average"), 1)
            else:
                tmdb_data["tmdb_rating"] = None

            # Directors & producers
            for member in tmdb_data["credits"]["crew"]:
                if member["job"] == "Director":
                    tmdb_data.setdefault("directors", []).append(member["name"])
                elif member["job"] == "Producer":
                    tmdb_data.setdefault("producers", []).append(member["name"])

            tmdb_data["directors"] = ", ".join(tmdb_data.get("directors"))
            tmdb_data["producers"] = ", ".join(tmdb_data.get("producers"))

            # Genres
            tmdb_data["genres"] = [
                {"name": genre["name"]} for genre in tmdb_data.get("genres", [])
            ]

            # Runtime
            tmdb_data["runtime"] = tmdb_data.pop("runtime", None)

            # Streaming providers
            for provider in (
                tmdb_data.get("watch/providers", {})
                .get("results", {})
                .get("US", {})
                .get("flatrate", [])
            ):
                if provider:
                    tmdb_data["streaming"] = [
                        {"name": provider["provider_name"]}
                        for provider in tmdb_data.get("watch/providers", {})
                        .get("results", {})
                        .get("US", {})
                        .get("flatrate", [])
                    ]

            # Watch free
            for provider in (
                tmdb_data.get("watch/providers", {})
                .get("results", {})
                .get("US", {})
                .get("free", [])
            ):
                if provider:
                    tmdb_data["watch_free"] = [
                        {"name": provider["provider_name"]}
                        for provider in tmdb_data.get("watch/providers", {})
                        .get("results", {})
                        .get("US", {})
                        .get("free", [])
                    ]

            # Official trailer
            # TODO Prioritize official trailers

            trailers = []
            for trailer in tmdb_data["videos"]["results"]:
                if (
                    trailer["type"] == "Trailer"
                    and trailer["site"] == "YouTube"
                    and trailer["iso_3166_1"] == "US"
                ):
                    trailers.append(trailer)

            if trailers:
                tmdb_data["trailer_url"] = (
                    f"https://www.youtube.com/watch?v={max(trailers, key=lambda x: x['size'])['key']}"
                )
            else:
                tmdb_data["trailer_url"] = None

            # IMDB page
            tmdb_data["imdb_url"] = (
                f"https://www.imdb.com/title/{tmdb_data.get('imdb_id')}/"
                if tmdb_data.get("imdb_id")
                else None
            )

            # Synopsis
            tmdb_data["synopsis"] = tmdb_data.pop("overview", None)

            # Release Date
            tmdb_data["release_date"] = tmdb_data.pop("release_date", None)

            # Cast members
            for member in tmdb_data["credits"]["cast"]:
                if (
                    member["known_for_department"] == "Acting"
                    and "(uncredited)" not in member["character"]
                ):
                    tmdb_data.setdefault("cast_list", []).append(member["name"])

            tmdb_data["cast"] = ", ".join(tmdb_data.pop("cast_list", [])[:10])

            # Country of origin
            # FIXME using the wrong data, should use "origin_country"
            tmdb_data["country_of_origin"] = (
                tmdb_data.get("production_countries")[0]["name"]
                if tmdb_data.get("production_countries")
                else None
            )

            # Content rating
            for result in tmdb_data["release_dates"]["results"]:
                if result["iso_3166_1"] == "US":
                    for date in result["release_dates"]:
                        if date["certification"]:
                            tmdb_data["content_rating"] = date["certification"]
                        else:
                            tmdb_data["content_rating"] = None

            # Poster path
            tmdb_data["poster_path"] = (
                f'https://image.tmdb.org/t/p/original{tmdb_data["poster_path"]}'
                if tmdb_data.get("poster_path")
                else None
            )

            # # Episode count
            # tmdb_data['episodes'] = tmdb_data.pop('number_of_episodes', None)

            # # Season count
            # tmdb_data['seasons'] = tmdb_data.pop('number_of_seasons', None)

            # Writer
            # "Writer": {"rich_text": [{"text": {"content": data.get("writer")}}]},

            # Last episode
            # "Last Episode": {"rich_text": [{"text": {"content": data.get("last_episode")}}]},

            # Upcoming episode
            # "Upcoming Episode": {"rich_text": [{"text": {"content": data.get("upcoming_episode")}}]},

            # Last air date
            # "Last Air Date": {"date": {"start": data.get("last_air_date")}},

            # Next air date
            # "Next Air Date": {"date": {"start": data.get("next_air_date")}},

            # Production status
            tmdb_data["status"] = tmdb_data.pop("status", None)

            # Original language
            # FIXME use tmdb's internal languages instead
            # tmdb_data['original_language'] = iso_639_1_languages[tmdb_data.get('original_language', '')]

            # Original title
            tmdb_data["original_title"] = (
                tmdb_data.get("original_title")
                if tmdb_data.get("original_title", "") != tmdb_data.get("title")
                else None
            )

            # Backdrop path
            tmdb_data["backdrop_path"] = (
                f'https://image.tmdb.org/t/p/original{tmdb_data["backdrop_path"]}'
            )

        elif media_type == "tv":
            pass

        for key in list(tmdb_data.keys()):
            if tmdb_data[key] is None or key not in [
                "title",
                "type",
                "tagline",
                "tmdb_rating",
                "directors",
                "producers",
                "genres",
                "runtime",
                "streaming",
                "watch_free",
                "trailer_url",
                "imdb_url",
                "synopsis",
                "release_date",
                "cast",
                "country_of_origin",
                "content_rating",
                "poster_path",
                "status",
                "original_language",
                "original_title",
                "backdrop_path",
            ]:
                del tmdb_data[key]

        return tmdb_data

    def get_cleaned_media_data(self, title: str):
        """
        Searches for media by title and returns cleaned data of the first result.
        """
        search_results = self.search_media(title)

        if not search_results:
            raise ValueError("No TMDb results found for the title.")

        # Use the first result for now; a GUI could allow selection from search_results.
        tmdb_result = search_results[0]
        media_type = tmdb_result.get("media_type")

        # Fetch detailed data and clean it
        raw_data = self.fetch_media_details(tmdb_result)
        cleaned_data = self.clean_media_data(raw_data, media_type)

        print(search_results)

        # return cleaned_data
