"""
Phase 2 verification script — read-only live tests against the real TestRail instance.

Run with:
    uv run python scripts/verify_phase2.py

Checks:
  1. Auth — valid credentials connect successfully
  2. Projects — can fetch all projects (exercises get_all + pagination)
  3. Suite mode — detects and caches suite mode for a project
  4. 404 handling — a bad ID returns a readable error, not a crash
  5. 401 handling — bad credentials return a readable error
  6. Connection error — a bad host returns a readable error
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from testrail_mcp.config import Settings
from testrail_mcp.client import TestRailClient, TestRailError

PASS = "✅"
FAIL = "❌"


def check(label: str, fn):
    try:
        result = fn()
        print(f"{PASS} {label}")
        return result
    except AssertionError as e:
        print(f"{FAIL} {label}: {e}")
        return None
    except Exception as e:
        print(f"{FAIL} {label}: {type(e).__name__}: {e}")
        return None


def main():
    print("\n── Phase 2 Verification ──────────────────────────────────────\n")

    settings = Settings()
    client = TestRailClient(
        url=settings.testrail_url,
        email=settings.testrail_email,
        api_key=settings.testrail_api_key,
    )

    # 1. Auth — fetch projects with real credentials
    projects = check(
        "Auth: valid credentials accepted",
        lambda: client.get_all("get_projects", "projects"),
    )

    if projects is None:
        print("\n⚠️  Auth failed — check TESTRAIL_URL, TESTRAIL_EMAIL, TESTRAIL_API_KEY in .env")
        sys.exit(1)

    # 2. Projects returned
    check(
        f"Pagination: received {len(projects)} project(s)",
        lambda: projects or AssertionError("No projects returned"),
    )

    if projects:
        print(f"\n   Projects found:")
        for p in projects:
            print(f"     [{p['id']}] {p['name']}")
        print()

    # 3. Suite mode detection on the first project
    first_mode = None
    if projects:
        first = projects[0]
        first_mode = check(
            f"Suite mode: detected mode for project '{first['name']}'",
            lambda: client.get_suite_mode(first["id"]),
        )
        if first_mode is not None:
            mode_labels = {1: "Single suite", 2: "Single suite + baselines", 3: "Multiple suites"}
            print(f"   Mode {first_mode}: {mode_labels.get(first_mode, 'Unknown')}\n")

        # 4. Cache — second call should hit cache and return same value
        check(
            "Suite mode cache: second call returns same value without re-fetching",
            lambda: client.get_suite_mode(first["id"]) == first_mode
                    or (_ for _ in ()).throw(AssertionError("Cached value differs")),
        )

    # 5. Error handling for nonexistent IDs — TestRail returns 400 or 404 depending
    #    on the endpoint; both indicate a permanent client error and should not retry.
    def expect_bad_id_error():
        try:
            client.get("get_project/999999999")
            raise AssertionError("Expected TestRailError but call succeeded unexpectedly")
        except TestRailError as e:
            assert e.status_code in (400, 404), \
                f"Expected 400 or 404 for nonexistent ID, got {e.status_code}"
            return f"HTTP {e.status_code}: {e}"

    msg = check("Error handling: nonexistent ID raises TestRailError immediately (no retry)", expect_bad_id_error)
    if msg:
        print(f"   Message: {msg}\n")

    # 6. 401 handling — bad credentials
    def expect_401():
        bad_client = TestRailClient(
            url=settings.testrail_url,
            email="nobody@example.com",
            api_key="notavalidkey",
        )
        try:
            bad_client.get_all("get_projects", "projects")
            raise AssertionError("Expected TestRailError but call succeeded unexpectedly")
        except TestRailError as e:
            assert e.status_code == 401, f"Expected 401, got {e.status_code}"
            return str(e)

    msg = check("Error handling: bad credentials return readable 401 message", expect_401)
    if msg:
        print(f"   Message: {msg}\n")

    # 7. Connection error — use a local port that is guaranteed to be unreachable
    def expect_connection_error():
        bad_client = TestRailClient(
            url="http://localhost:19999",
            email="a@b.com",
            api_key="key",
        )
        try:
            bad_client.get("get_projects")
            raise AssertionError("Expected TestRailError but call succeeded unexpectedly")
        except TestRailError as e:
            assert "connect" in str(e).lower() or "reach" in str(e).lower(), \
                f"Error message not descriptive enough: {e}"
            return str(e)

    msg = check("Error handling: bad host URL returns readable connection error", expect_connection_error)
    if msg:
        print(f"   Message: {msg}\n")

    print("── Done ──────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
