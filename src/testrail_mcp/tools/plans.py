"""
Read and write tools for TestRail test plans.

Phase 3 (this file): list_plans, get_plan
Phase 4 (this file): add_plan, update_plan, close_plan, delete_plan
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_plans(project_id: int) -> list[dict]:
    """
    List all test plans in a project.

    Test plans group related test runs together, often aligned to a milestone
    or release. Returns a summary list — use get_plan for full run details.
    """
    return get_client().get_all(f"get_plans/{project_id}", "plans")


@mcp.tool
def get_plan(plan_id: int) -> dict:
    """
    Get full details of a single test plan, including all its runs and entries.

    Use list_plans to find the correct plan_id.
    """
    return get_client().get(f"get_plan/{plan_id}")


@mcp.tool
def add_plan(
    project_id: int,
    name: str,
    description: str | None = None,
    milestone_id: int | None = None,
) -> dict:
    """
    Create a new test plan in a project.

    name is the display name for the plan (required).
    milestone_id optionally links the plan to a release milestone.
    Use list_milestones to find the correct milestone_id.

    Test runs can be added to the plan after creation using add_run
    with the plan_id parameter.
    """
    body: dict = {"name": name}
    if description is not None:
        body["description"] = description
    if milestone_id is not None:
        body["milestone_id"] = milestone_id

    return get_client().post(f"add_plan/{project_id}", body)


@mcp.tool
def update_plan(
    plan_id: int,
    name: str | None = None,
    description: str | None = None,
    milestone_id: int | None = None,
) -> dict:
    """
    Update an existing test plan.

    Only fields provided will be changed; omit any field to leave it unchanged.
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if milestone_id is not None:
        body["milestone_id"] = milestone_id

    return get_client().post(f"update_plan/{plan_id}", body)


@mcp.tool
def close_plan(plan_id: int) -> dict:
    """
    Close a test plan, marking it as completed.

    Closed plans are read-only — no further results can be added.
    Use this when a release or test cycle is finished.
    This action cannot be undone via the API.
    """
    return get_client().post(f"close_plan/{plan_id}")


@mcp.tool
def delete_plan(plan_id: int) -> dict:
    """
    Permanently delete a test plan and all its runs and results.

    WARNING: This cannot be undone. All run history within the plan
    will be permanently lost.

    Only use this in test/sandbox projects.
    """
    return get_client().post(f"delete_plan/{plan_id}")

