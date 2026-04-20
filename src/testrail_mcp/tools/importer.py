"""
File ingestion tool — imports test scenarios from text content into TestRail.

Phase 5: import_from_file
"""

from testrail_mcp.server import mcp, get_client
from testrail_mcp.parsers import parse

# Hard limit on content size. Files larger than this are rejected immediately
# before any processing begins. 500KB is generous for any real test plan file.
_MAX_CONTENT_BYTES = 500 * 1024  # 500KB

# Number of cases to create per batch. Keeps memory bounded and plays
# nicely with rate limiting.
_BATCH_SIZE = 25

# TestRail BDD template ID and the field key for the Given/When/Then content.
# These are standard for TestRail Cloud; update if your instance differs.
_BDD_TEMPLATE_ID = 4
_BDD_FIELD_KEY = "custom_testrail_bdd_scenario"


@mcp.tool
def import_from_file(
    content: str,
    section_id: int,
    fmt: str = "gherkin",
    type_id: int | None = None,
    priority_id: int | None = None,
) -> dict:
    """
    Parse text content and create TestRail test cases from the scenarios found.

    content: the full text of the file (passed as a string — the MCP client
      reads the file and sends its contents here). Maximum 500KB.

    section_id: the TestRail section to create cases in. Use list_sections
      to find the correct section_id before calling this tool.

    fmt: the format of the content. One of:
      "gherkin"   — Feature/Scenario/Given/When/Then blocks (default)
      "markdown"  — ## or ### headings as titles, body as BDD steps
      "numbered"  — numbered list items as titles only (no step content)

    type_id: optional test case type for all created cases.
      Common values: 1=Automated, 2=Functionality, 4=Regression, 5=Smoke & Sanity

    priority_id: optional priority for all created cases.
      Values: 1=Low, 2=Medium, 3=High, 4=Critical

    Returns a summary with:
      - total_parsed: number of scenarios found in the content
      - total_created: number of cases successfully created
      - created: list of {id, title} for each created case
      - failed: list of {title, error} for any scenarios that failed
    """
    # ── Gate 1: size check ────────────────────────────────────────────────────
    content_bytes = len(content.encode("utf-8"))
    if content_bytes > _MAX_CONTENT_BYTES:
        size_kb = content_bytes / 1024
        raise ValueError(
            f"Content too large ({size_kb:.0f}KB). "
            f"Maximum allowed is {_MAX_CONTENT_BYTES // 1024}KB. "
            "Consider splitting your file into smaller sections and importing each separately."
        )

    # ── Gate 2: content must be valid text (not binary) ───────────────────────
    # If the content contains null bytes it is almost certainly binary.
    if "\x00" in content:
        raise ValueError(
            "Content appears to be a binary file, not text. "
            "Only plain text files (.md, .feature, .txt) are supported."
        )

    # ── Parse ─────────────────────────────────────────────────────────────────
    scenarios = parse(content, fmt)

    if not scenarios:
        return {
            "total_parsed": 0,
            "total_created": 0,
            "created": [],
            "failed": [],
            "message": (
                f"No scenarios found in the provided content using format '{fmt}'. "
                "Check that the format parameter matches the actual file structure."
            ),
        }

    # ── Create in batches ─────────────────────────────────────────────────────
    client = get_client()
    created = []
    failed = []

    for i in range(0, len(scenarios), _BATCH_SIZE):
        batch = scenarios[i : i + _BATCH_SIZE]

        for scenario in batch:
            try:
                body: dict = {
                    "title": scenario.title,
                    "template_id": _BDD_TEMPLATE_ID,
                }

                # TestRail BDD field expects an array: [{"content": "Given...\nWhen...\nThen..."}]
                if scenario.bdd_content:
                    body[_BDD_FIELD_KEY] = [{"content": scenario.bdd_content}]
                elif scenario.description:
                    # Non-BDD content goes into the preconditions field as context
                    body["custom_preconds"] = scenario.description

                if type_id is not None:
                    body["type_id"] = type_id
                if priority_id is not None:
                    body["priority_id"] = priority_id

                case = client.post(f"add_case/{section_id}", body)
                created.append({"id": case["id"], "title": case["title"]})

            except Exception as e:
                failed.append({"title": scenario.title, "error": str(e)})

    return {
        "total_parsed": len(scenarios),
        "total_created": len(created),
        "created": created,
        "failed": failed,
        "message": (
            f"Successfully created {len(created)} of {len(scenarios)} cases."
            + (f" {len(failed)} failed — see 'failed' for details." if failed else "")
        ),
    }
