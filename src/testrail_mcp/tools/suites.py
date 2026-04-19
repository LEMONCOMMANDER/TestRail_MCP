"""
Read and write tools for TestRail suites.

Phase 3 (this file): list_suites, get_suite
Phase 4 (this file): add_suite, update_suite, delete_suite

Note: Suites are only relevant for projects with suite_mode = 3 (multiple suites).
For single-suite projects (suite_mode = 1 or 2), these tools still work but
there will only ever be one suite.
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_suites(project_id: int) -> list[dict]:
    """
    List all test suites in a project.

    Suites are the top-level containers for sections and test cases.
    For projects with suite_mode = 1 or 2, there is only one suite.
    For projects with suite_mode = 3, there may be many.

    Use list_projects to find the project_id and check suite_mode.
    """
    return get_client().get_all(f"get_suites/{project_id}", "suites")


@mcp.tool
def get_suite(suite_id: int) -> dict:
    """
    Get full details of a single test suite by its ID.

    Returns id, name, description, and the project it belongs to.
    """
    return get_client().get(f"get_suite/{suite_id}")
