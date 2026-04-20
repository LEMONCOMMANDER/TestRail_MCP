"""
Read and write tools for TestRail milestones.

Phase 3 (this file): list_milestones, get_milestone
Phase 4 (this file): add_milestone, update_milestone, delete_milestone
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_milestones(project_id: int) -> list[dict]:
    """
    List all milestones in a project.

    Milestones represent releases, sprints, or other delivery targets.
    Test plans and runs can be associated with a milestone for tracking.

    Use list_projects to find the correct project_id.
    """
    return get_client().get_all(f"get_milestones/{project_id}", "milestones")


@mcp.tool
def get_milestone(milestone_id: int) -> dict:
    """
    Get full details of a single milestone.

    Returns name, description, due date, completion status, and any
    sub-milestones. Use list_milestones to find the correct milestone_id.
    """
    return get_client().get(f"get_milestone/{milestone_id}")


@mcp.tool
def add_milestone(
    project_id: int,
    name: str,
    description: str | None = None,
    due_on: int | None = None,
    start_on: int | None = None,
) -> dict:
    """
    Create a new milestone in a project.

    name is the display name for the milestone (required).
    description is optional free-text context.
    due_on and start_on are Unix timestamps (seconds since epoch).
    Use list_projects to find the correct project_id.
    """
    body: dict = {"name": name}
    if description is not None:
        body["description"] = description
    if due_on is not None:
        body["due_on"] = due_on
    if start_on is not None:
        body["start_on"] = start_on

    return get_client().post(f"add_milestone/{project_id}", body)


@mcp.tool
def update_milestone(
    milestone_id: int,
    name: str | None = None,
    description: str | None = None,
    due_on: int | None = None,
    is_completed: bool | None = None,
) -> dict:
    """
    Update an existing milestone.

    Only fields provided will be changed; omit any field to leave it unchanged.
    Set is_completed to True to mark the milestone as completed.
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if due_on is not None:
        body["due_on"] = due_on
    if is_completed is not None:
        body["is_completed"] = is_completed

    return get_client().post(f"update_milestone/{milestone_id}", body)


@mcp.tool
def delete_milestone(milestone_id: int) -> dict:
    """
    Permanently delete a milestone.

    WARNING: This cannot be undone. Test plans and runs associated with
    this milestone will have their milestone reference cleared.

    Only use this in test/sandbox projects.
    """
    return get_client().post(f"delete_milestone/{milestone_id}")
