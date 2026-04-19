"""
TestRail API client wrapper.

Centralizes all HTTP communication with the TestRail REST API so that
individual tools never need to think about:
  - Authentication headers
  - Base URL construction
  - Pagination (auto-fetches all pages)
  - Transient error retries with exponential backoff
  - Error response normalization into readable messages
  - Suite mode detection per project (cached)
"""

import time
import requests

# Maximum number of retry attempts for transient errors (429, 500, 503).
_MAX_RETRIES = 4

# Initial wait in seconds before the first retry. Doubles each attempt.
_RETRY_BACKOFF_BASE = 1.0

# TestRail returns up to 250 results per page by default.
_PAGE_LIMIT = 250

# Errors that are permanent — retrying will not help.
# NOTE: TestRail returns 400 (not 404) for nonexistent or inaccessible resource IDs.
# For example, GET get_project/999999999 returns HTTP 400 with body:
#   {"error": "Field :project_id is not a valid or accessible project."}
# Both 400 and 404 are treated as permanent failures — no retry, fail immediately.
_NO_RETRY_CODES = {400, 401, 403, 404}

# Human-readable explanations for common HTTP error codes.
_ERROR_MESSAGES = {
    400: "Bad request — the ID may not exist, or a required field is missing or incorrectly formatted.",
    401: "Authentication failed — verify TESTRAIL_EMAIL and TESTRAIL_API_KEY in your .env file.",
    403: "Permission denied — your TestRail user does not have access to perform this action.",
    404: "Resource not found — the ID provided does not exist or you do not have access to it.",
    429: "Rate limit exceeded — too many requests sent in a short period.",
    500: "TestRail server error — the API returned an internal error.",
    503: "TestRail service unavailable — the server may be temporarily down.",
}


class TestRailError(Exception):
    """Raised when the TestRail API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TestRailClient:
    """
    Wraps the TestRail REST API.

    Instantiate once (at server startup) and share across all tool calls.
    Thread-safe for read operations. Suite mode results are cached in memory.
    """

    def __init__(self, url: str, email: str, api_key: str) -> None:
        self.base_url = f"{url}/index.php?/api/v2"
        self._auth = (email, api_key)
        self._headers = {"Content-Type": "application/json"}
        # Cache suite mode per project_id to avoid redundant API calls.
        self._suite_mode_cache: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Public API — used by all tools
    # ------------------------------------------------------------------

    def get(self, endpoint: str, params: dict | None = None) -> dict | list:
        """
        GET a single resource from the TestRail API.

        For list endpoints that support pagination, use get_all() instead.
        """
        return self._request("GET", endpoint, params=params)

    def get_all(self, endpoint: str, list_key: str, params: dict | None = None) -> list:
        """
        GET all pages of a paginated list endpoint and return a flat list.

        TestRail wraps paginated responses as:
          {"offset": 0, "limit": 250, "size": 250, "<list_key>": [...], "_links": {...}}

        list_key is the key that holds the array in each page response,
        e.g. "cases", "sections", "runs".
        """
        results = []
        offset = 0
        base_params = dict(params or {})

        while True:
            page_params = {**base_params, "limit": _PAGE_LIMIT, "offset": offset}
            response = self._request("GET", endpoint, params=page_params)

            # Some endpoints return a plain list rather than a paginated envelope.
            if isinstance(response, list):
                return response

            page_items = response.get(list_key, [])
            results.extend(page_items)

            # Stop when this page returned fewer items than the limit —
            # that means we've reached the last page.
            if len(page_items) < _PAGE_LIMIT:
                break

            offset += _PAGE_LIMIT

        return results

    def post(self, endpoint: str, body: dict | None = None) -> dict:
        """POST to the TestRail API (create or update a resource)."""
        return self._request("POST", endpoint, json=body)

    def get_suite_mode(self, project_id: int) -> int:
        """
        Return the suite mode for a project (cached after first call).

          1 = Single suite (no suite_id needed)
          2 = Single suite + baselines
          3 = Multiple suites (suite_id required)
        """
        if project_id not in self._suite_mode_cache:
            project = self.get(f"get_project/{project_id}")
            self._suite_mode_cache[project_id] = project["suite_mode"]
        return self._suite_mode_cache[project_id]

    # ------------------------------------------------------------------
    # Internal request engine
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict | list:
        """
        Execute an HTTP request against the TestRail API.

        Handles:
          - Auth headers
          - Transient error retries with exponential backoff
          - Response body error detection (TestRail 200s with error bodies)
          - Normalization into TestRailError with readable messages
        """
        url = f"{self.base_url}/{endpoint}"
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = requests.request(
                    method,
                    url,
                    auth=self._auth,
                    headers=self._headers,
                    params=params,
                    json=json,
                    timeout=30,
                )
            except requests.ConnectionError:
                raise TestRailError(
                    "Could not connect to TestRail. "
                    "Check that TESTRAIL_URL is correct and the instance is reachable."
                )
            except requests.Timeout:
                raise TestRailError(
                    "Request to TestRail timed out after 30 seconds. "
                    "The server may be under load — try again shortly."
                )

            # Permanent errors — fail immediately, no retry.
            if response.status_code in _NO_RETRY_CODES:
                raise TestRailError(
                    self._error_message(response),
                    status_code=response.status_code,
                )

            # Transient errors — retry with backoff.
            if response.status_code in (429, 500, 503):
                last_error = TestRailError(
                    self._error_message(response),
                    status_code=response.status_code,
                )
                if attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF_BASE * (2 ** attempt)
                    time.sleep(wait)
                continue

            # Unexpected non-2xx — fail immediately.
            if not response.ok:
                raise TestRailError(
                    self._error_message(response),
                    status_code=response.status_code,
                )

            # Parse JSON — guard against empty responses (e.g., 204 deletes).
            if not response.content:
                return {}

            data = response.json()

            # TestRail sometimes returns 200 OK with an error key in the body.
            if isinstance(data, dict) and "error" in data:
                raise TestRailError(
                    f"TestRail returned an error: {data['error']}",
                    status_code=response.status_code,
                )

            return data

        # All retries exhausted.
        raise last_error or TestRailError("Request failed after maximum retries.")

    def _error_message(self, response: requests.Response) -> str:
        """Build a readable error message from an HTTP error response."""
        base = _ERROR_MESSAGES.get(
            response.status_code,
            f"Unexpected error (HTTP {response.status_code}).",
        )
        # Append any detail TestRail included in the response body.
        try:
            body = response.json()
            if isinstance(body, dict) and "error" in body:
                return f"{base} TestRail said: {body['error']}"
        except Exception:
            pass
        return base
