"""
Read and write tools for TestRail sections.

Phase 3 (this file): list_sections, get_section
Phase 4 (this file): add_section, update_section, delete_section
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_sections(
    project_id: int,
    suite_id: int | None = None,
) -> list[dict]:
    """
    List all sections (folders) in a project or suite.

    suite_id is required for projects with multiple suites (suite_mode = 3).
    Use list_projects to check suite_mode, and list_suites to find suite IDs.

    Sections form a hierarchy — each section may have a parent_id pointing
    to its parent section. A null parent_id means it is a top-level section.
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

    return client.get_all(f"get_sections/{project_id}", "sections", params=params)


@mcp.tool
def get_section(section_id: int) -> dict:
    """
    Get full details of a single section by its ID.

    Returns id, name, parent_id, suite_id, and depth in the hierarchy.
    """
    return get_client().get(f"get_section/{section_id}")

