"""
Read and write tools for TestRail test cases.

Phase 3 (this file): list_cases, get_case
Phase 4 (this file): add_case, update_case, delete_case
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_cases(
    project_id: int,
    suite_id: int | None = None,
    section_id: int | None = None,
) -> list[dict]:
    """
    List all test cases in a project, optionally filtered by suite or section.

    suite_id is required for projects with multiple suites (suite_mode = 3).
    Use list_projects to check suite_mode, and list_suites to find suite IDs.
    section_id is optional — omit to return all cases across the suite.

    Returns a list of cases each with id, title, section_id, priority_id, and type_id.
    """
    client = get_client()
    suite_mode = client.get_suite_mode(project_id)

    if suite_mode == 3 and suite_id is None:
        raise ValueError(
            f"Project {project_id} uses multiple suites (suite_mode=3). "
            "Provide a suite_id — use list_suites to find available suites."
        )

    params: dict = {}
    if suite_id is not None:
        params["suite_id"] = suite_id
    if section_id is not None:
        params["section_id"] = section_id

    return client.get_all(f"get_cases/{project_id}", "cases", params=params)


@mcp.tool
def get_case(case_id: int) -> dict:
    """
    Get full details of a single test case by its ID.

    Returns all fields including title, steps, expected result, priority,
    type, and any custom fields defined for the project.
    """
    return get_client().get(f"get_case/{case_id}")

