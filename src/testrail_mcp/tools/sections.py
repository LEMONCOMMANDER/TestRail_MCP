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


@mcp.tool
def add_section(
    project_id: int,
    name: str,
    suite_id: int | None = None,
    parent_id: int | None = None,
    description: str | None = None,
) -> dict:
    """
    Add a new section (folder) to a project or suite.

    name is the display name for the section (required).

    suite_id is required for projects with multiple suites (suite_mode = 3).
    Use list_suites to find the correct suite_id.

    parent_id is optional — provide to nest this section inside an existing one.
    Omit parent_id to create a top-level section.

    Use list_sections to see the existing hierarchy before adding.
    """
    client = get_client()
    suite_mode = client.get_suite_mode(project_id)

    if suite_mode == 3 and suite_id is None:
        raise ValueError(
            f"Project {project_id} uses multiple suites (suite_mode=3). "
            "Provide a suite_id — use list_suites to find available suites."
        )

    body: dict = {"name": name}
    if suite_id is not None:
        body["suite_id"] = suite_id
    if parent_id is not None:
        body["parent_id"] = parent_id
    if description is not None:
        body["description"] = description

    return client.post(f"add_section/{project_id}", body)


@mcp.tool
def update_section(
    section_id: int,
    name: str | None = None,
    description: str | None = None,
) -> dict:
    """
    Update an existing section's name or description.

    section_id is the ID of the section to update.
    Only fields provided will be changed; omit any field to leave it unchanged.
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description

    return get_client().post(f"update_section/{section_id}", body)


@mcp.tool
def delete_section(section_id: int) -> dict:
    """
    Permanently delete a section and all test cases it contains.

    WARNING: This cannot be undone. All test cases in the section will be
    deleted and removed from all runs and plans that reference them.

    Only use this in test/sandbox projects. Confirm the section contents
    with list_cases before deleting.
    """
    return get_client().post(f"delete_section/{section_id}")

