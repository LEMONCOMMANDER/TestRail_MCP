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
