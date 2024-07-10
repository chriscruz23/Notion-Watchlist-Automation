class NoEntriesFoundException(Exception):
    """Exception raised when no entries are found in the database query."""

    def __init__(self, message="No entries found in the database query"):
        self.message = message
        super().__init__(self.message)
