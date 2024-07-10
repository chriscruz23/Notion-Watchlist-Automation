Notion Watchlist Automation

Utilizing the Notion API and TMDB API to find movie and TV show data, this program queries a Notion Database looking for entries that end in a semicolon and then searches TMDB to populate the missing properties in the Notion Database.

The Notion API (notion-client package in Python) is used to first set up a connection to the watchlist Notion database, and then to query entries looking for titles that end in a semicolon. These entries are then queried in the TMDB website using their API (I'm using tmdbsimple as a wrapper in Python) to search for missing properties.

TODO
  ~ Implement search filtering by denoting markers that are read while searching through the Notion Database Example: Parasite[m2019; => Search for a Movie "Parasite" that was released in 2019
  ~ Implement simple GUI interface for ease-of-use
  ~ Implement a "refresh" method that searches through all entries in the Notion Database and updates any entries where updated or new information was added to the TMBD database
  ~ Debug TV show searches and populations
