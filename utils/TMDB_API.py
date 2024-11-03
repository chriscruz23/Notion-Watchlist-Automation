import logging

import requests

# Configure the logger for TMDBAPI
logger = logging.getLogger(__name__)


class TMDB_API:
    BASE_URL = "https://api.themoviedb.org/3/"

    def __init__(self, api_key):
        self.api_key = api_key
        # Authenticate API key
        if not self._authenticate():
            raise ValueError("Invalid TMDb API key. Authentication failed.")

    def _authenticate(self):
        """
        Check if the provided API key is valid by requesting a new token.
        """
        try:
            url = self.BASE_URL + "authentication"
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            response = requests.get(url=url, headers=headers)
            response.raise_for_status()  # Will raise an HTTPError if the request failed
            if response.json().get("success"):
                logger.info("API key authentication successful.")
                return True
            else:
                logger.error("API key authentication failed. Check API key.")
                return False
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error during authentication: {http_err}", exc_info=True)
            return False
        except Exception as err:
            logger.error(f"Error during API key authentication: {err}", exc_info=True)
            return False

    def _get(self, endpoint, headers=None):
        """Helper method for making GET requests to the TMDb API."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if headers is None:
            headers = {}
        headers["accept"] = "application/json"
        headers["Authorization"] = (
            f"Bearer {self.api_key}"  # Append the API key to each request
        )

    def search_multi(self, title):
        """
        Search for a movie or TV show by title.
        :param title: The title of the movie or TV show.
        :return: List of search results.
        """
        params = {"query": title}
        return self._get("search/multi", params=params).get("results", [])

    def get_movie_details(self, movie_id):
        """
        Get detailed information for a specific movie.
        :param movie_id: The TMDb ID of the movie.
        :return: Dictionary of movie details.
        """
        return self._get(f"movie/{movie_id}")

    def get_tv_details(self, tv_id):
        """
        Get detailed information for a specific TV show.
        :param tv_id: The TMDb ID of the TV show.
        :return: Dictionary of TV show details.
        """
        return self._get(f"tv/{tv_id}")
