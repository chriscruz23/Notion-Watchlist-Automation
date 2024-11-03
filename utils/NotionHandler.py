from typing import Any, Dict, List

from notion_client import Client


class NotionHandler:
    # TODO catch database_id and client not found exceptions
    def __init__(self, api_key: str | None, database_id: str | None) -> None:
        self.client = Client(auth=api_key)
        self.database_id = database_id

    def get_entries_to_update(self, title: str | None = None) -> List[Dict[str, Any]]:
        """Fetch entries with titles ending in semicolon, or for the given title."""

        query = {"database_id": self.database_id, "filter": {"property": "Title"}}

        if title:
            query["filter"]["title"] = {"equals": title}
        else:
            query["filter"]["title"] = {"ends_with": ";"}

        # Any is to silence pylance(reportAttributeAccessIssue) error
        response: Any = self.client.databases.query(**query)
        return response.get("results", [])

    def update_page(self, page_id, data):
        """Update page properties with cleaned data."""

        self.client.pages.update(page_id=page_id, properties=data)

        # Set the icon and cover images
        self.client.pages.update(
            page_id=page_id,
            icon={"type": "external", "external": {"url": data.get("poster_path")}},
        )
        self.client.pages.update(
            page_id=page_id,
            cover={"type": "external", "external": {"url": data.get("backdrop_path")}},
        )
