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


@mcp.tool
def add_case(
    section_id: int,
    title: str,
    type_id: int | None = None,
    priority_id: int | None = None,
    estimate: str | None = None,
    milestone_id: int | None = None,
    refs: str | None = None,
    custom_fields: dict | None = None,
) -> dict:
    """
    Add a new test case to a section.

    section_id is required — use list_sections to find the right section.
    title is the name of the test case (required).

    type_id values (common): 1=Automated, 2=Functionality, 3=Other,
      4=Regression, 5=Smoke & Sanity, 6=Exploratory, 7=Acceptance,
      8=Accessibility, 9=Performance, 10=Security

    priority_id values: 1=Low, 2=Medium, 3=High, 4=Critical

    estimate: time string e.g. "30s", "1m 45s", "2h"

    refs: comma-separated reference IDs (e.g. Jira tickets "PROJ-1,PROJ-2")

    custom_fields: dict of any org-specific custom field values,
      e.g. {"custom_automation_type": 1, "custom_risk_level": "High"}
      Field keys must be prefixed with "custom_" as defined in TestRail.
    """
    body: dict = {"title": title}
    if type_id is not None:
        body["type_id"] = type_id
    if priority_id is not None:
        body["priority_id"] = priority_id
    if estimate is not None:
        body["estimate"] = estimate
    if milestone_id is not None:
        body["milestone_id"] = milestone_id
    if refs is not None:
        body["refs"] = refs
    if custom_fields:
        body.update(custom_fields)

    return get_client().post(f"add_case/{section_id}", body)


@mcp.tool
def update_case(
    case_id: int,
    title: str | None = None,
    type_id: int | None = None,
    priority_id: int | None = None,
    estimate: str | None = None,
    milestone_id: int | None = None,
    refs: str | None = None,
    custom_fields: dict | None = None,
) -> dict:
    """
    Update an existing test case. Only fields provided will be changed.

    case_id is the ID of the case to update — use list_cases or get_case to find it.
    All fields are optional; omit any field to leave it unchanged.

    custom_fields: dict of org-specific custom field values to update.
      Keys must be prefixed with "custom_" as defined in TestRail.
    """
    body: dict = {}
    if title is not None:
        body["title"] = title
    if type_id is not None:
        body["type_id"] = type_id
    if priority_id is not None:
        body["priority_id"] = priority_id
    if estimate is not None:
        body["estimate"] = estimate
    if milestone_id is not None:
        body["milestone_id"] = milestone_id
    if refs is not None:
        body["refs"] = refs
    if custom_fields:
        body.update(custom_fields)

    return get_client().post(f"update_case/{case_id}", body)


@mcp.tool
def delete_case(case_id: int) -> dict:
    """
    Permanently delete a test case.

    WARNING: This action cannot be undone. The case will be removed from
    all test runs and plans that reference it.

    Only use this in test/sandbox projects. Confirm the case_id with
    get_case before deleting.
    """
    return get_client().post(f"delete_case/{case_id}")

