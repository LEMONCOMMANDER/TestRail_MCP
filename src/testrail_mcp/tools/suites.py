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


@mcp.tool
def add_suite(
    project_id: int,
    name: str,
    description: str | None = None,
) -> dict:
    """
    Add a new test suite to a project.

    Only meaningful for projects with suite_mode = 3 (multiple suites).
    Use list_projects to confirm suite_mode before adding suites.

    name is the display name for the suite (required).
    """
    body: dict = {"name": name}
    if description is not None:
        body["description"] = description

    return get_client().post(f"add_suite/{project_id}", body)


@mcp.tool
def update_suite(
    suite_id: int,
    name: str | None = None,
    description: str | None = None,
) -> dict:
    """
    Update an existing test suite's name or description.

    Only fields provided will be changed; omit any field to leave it unchanged.
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description

    return get_client().post(f"update_suite/{suite_id}", body)


@mcp.tool
def delete_suite(suite_id: int) -> dict:
    """
    Permanently delete a test suite and all sections and cases it contains.

    WARNING: This cannot be undone. All test cases in the suite will be
    deleted and removed from all runs and plans that reference them.

    Only use this in test/sandbox projects.
    """
    return get_client().post(f"delete_suite/{suite_id}")
