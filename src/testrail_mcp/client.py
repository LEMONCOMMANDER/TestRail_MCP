"""
TestRail API client — stub for Phase 2.

Full implementation (auth, pagination, retry logic, error normalization,
and suite mode detection) will be added in Phase 2.
"""


class TestRailClient:
    """
    Wraps the TestRail REST API.

    All tools interact with TestRail exclusively through this class.
    It is responsible for:
      - Authentication headers
      - Base URL construction
      - Pagination (fetching all pages automatically)
      - Rate limit retry with exponential backoff
      - Error normalization into readable messages
      - Suite mode detection per project
    """

    def __init__(self, url: str, email: str, api_key: str) -> None:
        self.base_url = f"{url}/index.php?/api/v2"
        self.auth = (email, api_key)

    def get(self, endpoint: str, params: dict | None = None) -> dict | list:
        """GET a resource from the TestRail API. Full implementation in Phase 2."""
        raise NotImplementedError("TestRailClient will be implemented in Phase 2")

    def post(self, endpoint: str, body: dict | None = None) -> dict:
        """POST to the TestRail API. Full implementation in Phase 2."""
        raise NotImplementedError("TestRailClient will be implemented in Phase 2")
