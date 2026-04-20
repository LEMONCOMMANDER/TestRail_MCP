"""
Phase 7 verification script — prompt template registration and content checks.

What this script tests (automatable):
  - All 4 prompts are registered with the correct names and descriptions
  - Each prompt renders without errors, with and without optional parameters
  - Rendered content contains key instructions (tool names, field names, step order)
  - Optional parameters change the rendered output as expected

What this script CANNOT test (requires a live LLM):
  - Whether the LLM actually follows the instructions correctly
  - Whether the guidance is clear enough for ambiguous inputs
  - Output quality — this must be evaluated manually in Claude/Cursor

Manual testing checklist (from Phase 7 review criteria):
  [ ] Use import_test_scenarios with a real .feature file — does the LLM map
      fields correctly without extra guidance?
  [ ] Use create_test_cases_from_description with a vague feature description
      — does the LLM ask clarifying questions rather than guessing?
  [ ] Use generate_project_report — does the report look readable and highlight
      anything that needs attention?
  [ ] Use triage_test_failures on a run with failures — are the recommended
      actions sensible?

Run with:
    uv run python scripts/verify_phase7.py
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ.setdefault("TESTRAIL_URL", "https://example.testrail.io")
os.environ.setdefault("TESTRAIL_EMAIL", "test@example.com")
os.environ.setdefault("TESTRAIL_API_KEY", "dummy")

PASS = "✅"
FAIL = "❌"
NOTE = "📝"


def check(label: str, fn):
    try:
        result = fn()
        print(f"{PASS} {label}")
        return result
    except AssertionError as e:
        print(f"{FAIL} {label}: {e}")
        return None
    except Exception as e:
        print(f"{FAIL} {label}: {type(e).__name__}: {e}")
        return None


async def run_checks():
    from testrail_mcp.server import mcp

    print("\n── Phase 7 Verification ──────────────────────────────────────\n")

    # ── Registration checks ────────────────────────────────────────────────────
    print("Registration checks:\n")

    prompts = await mcp.list_prompts()
    prompt_map = {p.name: p for p in prompts}
    expected_names = [
        "import_test_scenarios",
        "generate_project_report",
        "triage_test_failures",
        "create_test_cases_from_description",
    ]

    check(
        f"All 4 prompts registered (found {len(prompts)})",
        lambda: len(prompts) == 4
        or (_ for _ in ()).throw(AssertionError(f"Expected 4, got {len(prompts)}: {list(prompt_map.keys())}")),
    )
    for name in expected_names:
        check(
            f"Prompt '{name}' is registered",
            lambda n=name: n in prompt_map
            or (_ for _ in ()).throw(AssertionError(f"'{n}' not found in {list(prompt_map.keys())}")),
        )
        if name in prompt_map:
            check(
                f"Prompt '{name}' has a description",
                lambda n=name: bool(prompt_map[n].description)
                or (_ for _ in ()).throw(AssertionError("description is empty")),
            )

    print()

    # ── Render checks — import_test_scenarios ──────────────────────────────────
    print("import_test_scenarios render checks:\n")

    sample_gherkin = """\
Feature: Login
  Scenario: User logs in
    Given the login page is open
    When valid credentials are entered
    Then the dashboard is shown
"""

    result_auto = await mcp.render_prompt(
        "import_test_scenarios",
        {"file_content": sample_gherkin, "format_hint": "auto"},
    )
    text_auto = result_auto.messages[0].content.text

    check(
        "Renders without error with format_hint='auto'",
        lambda: bool(text_auto),
    )
    check(
        "Contains the file content verbatim",
        lambda: "User logs in" in text_auto
        or (_ for _ in ()).throw(AssertionError("file content not found in rendered prompt")),
    )
    check(
        "Contains auto-detect format instructions",
        lambda: "Detect the format automatically" in text_auto
        or (_ for _ in ()).throw(AssertionError("auto-detect instructions missing")),
    )
    check(
        "References the import_scenarios tool by name",
        lambda: "import_scenarios" in text_auto
        or (_ for _ in ()).throw(AssertionError("tool name 'import_scenarios' not found")),
    )
    check(
        "Contains BDD field name (custom_testrail_bdd_scenario)",
        lambda: "custom_testrail_bdd_scenario" in text_auto
        or (_ for _ in ()).throw(AssertionError("BDD field name missing — LLM won't know the correct field")),
    )
    check(
        "Contains template_id instruction",
        lambda: "template_id" in text_auto
        or (_ for _ in ()).throw(AssertionError("template_id instruction missing")),
    )
    check(
        "Warns against using plain string for BDD field",
        lambda: "plain string" in text_auto.lower() or "400" in text_auto
        or (_ for _ in ()).throw(AssertionError("plain-string warning missing")),
    )
    check(
        "Instructs to confirm target section before creating cases",
        lambda: "confirm" in text_auto.lower() and "section" in text_auto.lower()
        or (_ for _ in ()).throw(AssertionError("section-confirmation step missing")),
    )

    # With explicit format_hint — should NOT contain auto-detect language
    result_explicit = await mcp.render_prompt(
        "import_test_scenarios",
        {"file_content": sample_gherkin, "format_hint": "gherkin"},
    )
    text_explicit = result_explicit.messages[0].content.text

    check(
        "format_hint='gherkin' produces different output than format_hint='auto'",
        lambda: text_explicit != text_auto
        or (_ for _ in ()).throw(AssertionError("explicit format_hint has no effect on rendered content")),
    )
    check(
        "format_hint='gherkin' does NOT contain auto-detect instructions",
        lambda: "Detect the format automatically" not in text_explicit
        or (_ for _ in ()).throw(AssertionError("auto-detect instructions still present with explicit hint")),
    )
    check(
        "format_hint='gherkin' instructs to use fmt=\"gherkin\"",
        lambda: 'fmt="gherkin"' in text_explicit
        or (_ for _ in ()).throw(AssertionError('fmt="gherkin" instruction missing')),
    )

    print()

    # ── Render checks — generate_project_report ────────────────────────────────
    print("generate_project_report render checks:\n")

    result_report_named = await mcp.render_prompt(
        "generate_project_report",
        {"project": "My App"},
    )
    text_report_named = result_report_named.messages[0].content.text

    result_report_empty = await mcp.render_prompt(
        "generate_project_report",
        {"project": ""},
    )
    text_report_empty = result_report_empty.messages[0].content.text

    check(
        "Renders without error with project name provided",
        lambda: bool(text_report_named),
    )
    check(
        "Contains project name in rendered output",
        lambda: "My App" in text_report_named
        or (_ for _ in ()).throw(AssertionError("project name not in output")),
    )
    check(
        "References get_full_project_report tool",
        lambda: "get_full_project_report" in text_report_named
        or (_ for _ in ()).throw(AssertionError("tool name missing")),
    )
    check(
        "Empty project triggers ask-user instruction",
        lambda: "ask" in text_report_empty.lower() and "list_projects" in text_report_empty
        or (_ for _ in ()).throw(AssertionError("ask-user / list_projects instruction missing for empty project")),
    )
    check(
        "Contains section headers for health, coverage, milestones",
        lambda: all(k in text_report_named for k in ["Health", "Coverage", "Milestone"])
        or (_ for _ in ()).throw(AssertionError("one or more report sections missing")),
    )
    check(
        "Instructs to flag runs with low pass rate",
        lambda: "80%" in text_report_named or "below" in text_report_named.lower()
        or (_ for _ in ()).throw(AssertionError("low-pass-rate flagging instruction missing")),
    )

    print()

    # ── Render checks — triage_test_failures ──────────────────────────────────
    print("triage_test_failures render checks:\n")

    result_triage = await mcp.render_prompt(
        "triage_test_failures",
        {"run": "Sprint 5 Regression"},
    )
    text_triage = result_triage.messages[0].content.text

    result_triage_empty = await mcp.render_prompt(
        "triage_test_failures",
        {"run": ""},
    )
    text_triage_empty = result_triage_empty.messages[0].content.text

    check(
        "Renders without error with run name provided",
        lambda: bool(text_triage),
    )
    check(
        "Contains run name in rendered output",
        lambda: "Sprint 5 Regression" in text_triage
        or (_ for _ in ()).throw(AssertionError("run name not in output")),
    )
    check(
        "References get_run_summary tool",
        lambda: "get_run_summary" in text_triage
        or (_ for _ in ()).throw(AssertionError("tool name missing")),
    )
    check(
        "Empty run triggers ask-user instruction",
        lambda: "ask" in text_triage_empty.lower() or "list_runs" in text_triage_empty
        or (_ for _ in ()).throw(AssertionError("ask-user / list_runs instruction missing")),
    )
    check(
        "Contains status breakdown section",
        lambda: "Status" in text_triage and "Passed" in text_triage and "Failed" in text_triage
        or (_ for _ in ()).throw(AssertionError("status breakdown section missing")),
    )
    check(
        "Contains recommended actions section",
        lambda: "Recommended" in text_triage or "Actions" in text_triage
        or (_ for _ in ()).throw(AssertionError("recommended actions section missing")),
    )

    print()

    # ── Render checks — create_test_cases_from_description ────────────────────
    print("create_test_cases_from_description render checks:\n")

    desc = "Users should be able to reset their password by receiving an email link."
    result_create = await mcp.render_prompt(
        "create_test_cases_from_description",
        {"description": desc, "feature_name": "Password Reset"},
    )
    text_create = result_create.messages[0].content.text

    result_create_no_name = await mcp.render_prompt(
        "create_test_cases_from_description",
        {"description": desc, "feature_name": ""},
    )
    text_create_no_name = result_create_no_name.messages[0].content.text

    check(
        "Renders without error",
        lambda: bool(text_create),
    )
    check(
        "Contains the description verbatim",
        lambda: desc in text_create
        or (_ for _ in ()).throw(AssertionError("description not found in rendered output")),
    )
    check(
        "Contains feature_name when provided",
        lambda: "Password Reset" in text_create
        or (_ for _ in ()).throw(AssertionError("feature_name not in output")),
    )
    check(
        "Uses fallback label when feature_name is empty",
        lambda: "the described feature" in text_create_no_name
        or (_ for _ in ()).throw(AssertionError("fallback feature label missing")),
    )
    check(
        "References import_scenarios tool",
        lambda: "import_scenarios" in text_create
        or (_ for _ in ()).throw(AssertionError("tool name missing")),
    )
    check(
        "Instructs to show scenarios to user for approval before importing",
        lambda: "approval" in text_create.lower() or "confirm" in text_create.lower()
        or (_ for _ in ()).throw(AssertionError("approval step missing — LLM may import without user review")),
    )
    check(
        "Instructs to cover happy path and failure/edge cases",
        lambda: "happy path" in text_create.lower() and "edge" in text_create.lower()
        or (_ for _ in ()).throw(AssertionError("happy path / edge case guidance missing")),
    )
    check(
        "Instructs to ask clarifying questions for vague descriptions",
        lambda: "clarif" in text_create.lower()
        or (_ for _ in ()).throw(AssertionError("clarifying-question instruction missing")),
    )

    print()
    print(f"{NOTE} Manual testing still required — see the checklist at the top of this script.")
    print()
    print("── Done ──────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    asyncio.run(run_checks())
