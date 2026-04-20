"""
MCP Prompt Templates for TestRail.

Phase 7: Reusable instruction templates that guide the LLM when using the
TestRail MCP server. Each prompt encodes the correct workflow, field mappings,
and behavioral rules so the LLM produces consistent, correct results without
needing detailed guidance from the user every time.

Prompts:
  import_test_scenarios          — import a file of test scenarios into TestRail
  generate_project_report        — produce a readable metrics report for a project
  triage_test_failures           — analyse failures in a test run and suggest actions
  create_test_cases_from_description — convert a feature description into BDD cases
"""

from testrail_mcp.server import mcp


@mcp.prompt(
    description=(
        "Import test scenarios from a file into TestRail. "
        "Handles Gherkin (.feature), Markdown, and numbered-list formats."
    )
)
def import_test_scenarios(
    file_content: str,
    format_hint: str = "auto",
) -> str:
    """
    Guide the LLM through importing test scenarios from file content into TestRail.

    file_content: the raw text content of the file to import.
    format_hint: the expected format — "gherkin", "markdown", "numbered", or
      "auto" (default) to let the LLM detect the format from the content.
    """
    format_section = (
        f'The user has indicated the format is **{format_hint}**. '
        f'Use `fmt="{format_hint}"` when calling import_scenarios.'
        if format_hint != "auto"
        else """\
**Detect the format automatically** by inspecting the content:
- If it contains `Scenario:` or `Scenario Outline:` keywords → `fmt="gherkin"`
- If it uses `##` or `###` headings → `fmt="markdown"`
- If it uses numbered lines like `1. ...` → `fmt="numbered"`
Tell the user which format you detected before proceeding."""
    )

    return f"""\
You are about to import the following test content into TestRail.

--- FILE CONTENT START ---
{file_content}
--- FILE CONTENT END ---

## Your task

Follow these steps **in order**. Do not skip any step.

### Step 1 — Detect the format
{format_section}

### Step 2 — Confirm the target location
Before creating any cases, ask the user:
1. Which **project** to import into (name or ID). Call `list_projects` to show options if needed.
2. Which **suite** (only required for multi-suite projects — check suite_mode from list_projects).
3. Which **section** to create the cases in. Call `list_sections` to show the available sections.

Do not proceed to Step 3 until the user has confirmed the project, suite (if needed), and section.

### Step 3 — Import using import_scenarios
Call the `import_scenarios` tool with:
- `content` = the file content above (verbatim — do not modify it)
- `project` = the confirmed project name or ID
- `suite` = the confirmed suite name or ID (omit for single-suite projects)
- `section` = the confirmed section name or ID
- `fmt` = the detected or provided format string

### Step 4 — Report results
After the tool responds, tell the user:
- How many scenarios were found in the file (`total_parsed`)
- How many cases were successfully created (`total_created`)
- The title of each created case
- Details of any failures — if there are failures, explain each one clearly

## BDD field mapping rules (critical)

TestRail's BDD template stores Given/When/Then content in a structured field.
The `import_scenarios` tool handles this automatically — you do **not** need to
call `add_case` directly. Always prefer `import_scenarios` over manual case creation
when working with file content.

If you must call `add_case` directly for any reason, follow these rules exactly:
- Always pass `"template_id": 4` (Behaviour Driven Development template)
- The BDD steps field key is `custom_testrail_bdd_scenario`
- It requires a JSON array: `[{{"content": "Given ...\\nWhen ...\\nThen ..."}}]`
- One test case = one scenario = one array element containing the full step block
- Do NOT split each step into a separate array element
- Do NOT pass a plain string — the API will reject it with a 400 error

## Rules
- Create one test case per scenario — never merge multiple scenarios into one case
- Preserve the original wording exactly — do not paraphrase or summarise
- If a scenario is ambiguous or incomplete, flag it to the user rather than guessing
- If any cases fail to create, report the failures and ask the user how to proceed
"""


@mcp.prompt(
    description=(
        "Generate a comprehensive, human-readable metrics report for a TestRail project. "
        "Covers overall health, test coverage, and milestone progress."
    )
)
def generate_project_report(
    project: str = "",
) -> str:
    """
    Guide the LLM to produce a well-formatted project health report.

    project: the project name or ID to report on. If empty, the LLM will
      ask the user which project they want.
    """
    project_section = (
        f'Generate the report for project **"{project}"**.'
        if project
        else (
            "Ask the user which project they want a report for. "
            "Call `list_projects` to show available options, then proceed once confirmed."
        )
    )

    return f"""\
You are generating a comprehensive TestRail metrics report.

{project_section}

## Your task

### Step 1 — Gather data
Call `get_full_project_report` with the confirmed project name or ID.
Use the default `run_limit` of 10 unless the user asks for more history.

### Step 2 — Present the report
Structure your response with the following sections. Use clear headings and
highlight anything that needs attention.

---

### 📊 Project Health
- State the project name and how many recent runs were analyzed
- Show the overall **pass rate** and **execution rate** as percentages
- Include a summary table of recent runs: run name | passed | failed | untested | pass rate
- Flag any runs with a pass rate below 80% or execution rate below 50%

### 📁 Test Coverage
- For each suite, show: suite name | total cases | execution rate %
- Flag any suite where execution rate is below 50% — these cases are not being exercised
- If a suite has 0 runs, call that out explicitly

### 🏁 Milestone Progress
- If there are active milestones, show each one with:
  - Milestone name and due date (if set)
  - Pass rate and execution rate across its runs
  - Whether it looks on track (high execution + high pass rate) or at risk
- If there are no active milestones, say so

### ⚠️ Summary & Recommendations
- In 3–5 bullet points, summarise the most important observations
- Prioritise: failing tests, low coverage areas, at-risk milestones
- Suggest one concrete next step the team could take

---

## Rules
- Present numbers as percentages where possible — raw counts alone are hard to interpret
- If a metric has no data (e.g. no runs, no milestones), say so clearly rather than showing zeros
- Do not invent data — if the API returns empty results, report that honestly
- Keep the tone factual and constructive
"""


@mcp.prompt(
    description=(
        "Analyse the failures in a test run and produce a prioritised triage summary "
        "with suggested next steps."
    )
)
def triage_test_failures(
    run: str = "",
) -> str:
    """
    Guide the LLM to analyse and summarise test failures in a run.

    run: the run name or ID to triage. If empty, the LLM will ask the user.
    """
    run_section = (
        f'Triage the run **"{run}"**.'
        if run
        else (
            "Ask the user which test run they want to triage. "
            "Call `list_runs` with the appropriate project_id to show options."
        )
    )

    return f"""\
You are triaging test failures for a TestRail test run.

{run_section}

## Your task

### Step 1 — Get the run summary
Call `get_run_summary` with the run name or ID.
If using a run name, you will also need the project_id — ask the user if you don't have it.

### Step 2 — Assess the situation
From the summary data, determine:
- Total tests in the run and how many have been executed
- How many passed, failed, blocked, and are pending retest
- The overall pass rate

### Step 3 — Present the triage report
Structure your response as follows:

---

### 🔍 Run Overview
- Run name, completion status, and milestone (if linked)
- Execution progress: X of Y tests run (execution_rate_pct%)
- Pass rate: X% (passed / executed)

### 🔴 Failures & Blocks
- Report the count of failed and blocked tests
- If the pass rate is below 90%, call it out as needing attention
- If blocked tests exist, note that they may be hiding additional failures

### 📋 Status Breakdown
Present a simple table:
| Status | Count | % of executed |
|--------|-------|---------------|
| Passed | ... | ... |
| Failed | ... | ... |
| Blocked | ... | ... |
| Retest | ... | ... |
| Untested | ... | N/A |

### ✅ Recommended Actions
Based on the results, suggest prioritised next steps. Examples:
- If pass rate < 70%: investigate the highest-failure areas first
- If execution rate < 50%: the run is not complete — push to finish execution
- If blocked tests exist: resolve blockers before drawing conclusions
- If retest count is high: re-execute those tests before closing the run
- If pass rate > 95%: the run is in good shape — ready to close

---

## Rules
- Base all observations strictly on the data returned by get_run_summary
- Do not speculate about *why* tests are failing — only report what the data shows
- If the run has no results yet (all untested), say so and recommend starting execution
- Keep the tone professional and action-oriented
"""


@mcp.prompt(
    description=(
        "Convert a natural-language feature description into BDD test cases "
        "and import them into TestRail."
    )
)
def create_test_cases_from_description(
    description: str,
    feature_name: str = "",
) -> str:
    """
    Guide the LLM to write BDD scenarios from a description and import them.

    description: a natural-language description of the feature or behaviour
      to be tested (e.g. from a ticket, spec doc, or user story).
    feature_name: optional name for the feature (used as the Gherkin Feature header).
    """
    feature_header = feature_name if feature_name else "the described feature"

    return f"""\
You are creating TestRail test cases from a feature description.

## Feature description provided by the user

{description}

## Your task

### Step 1 — Write BDD scenarios
Convert the description into well-formed Gherkin scenarios for **{feature_header}**.

Rules for writing scenarios:
- Cover the **happy path** first (the expected successful flow)
- Then cover key **failure / edge cases** (invalid input, missing data, permission errors, etc.)
- Write each scenario as a complete Given/When/Then block
- Use concrete, specific language — avoid vague terms like "something happens"
- Each scenario should be independent and testable on its own
- Aim for 3–8 scenarios unless the feature clearly warrants more or fewer
- Use `And` or `But` steps to keep scenarios readable when a step is compound

### Gherkin format to produce
```
Feature: {feature_header}

  Scenario: <scenario name>
    Given <precondition>
    When <action>
    Then <expected outcome>

  Scenario: <scenario name>
    ...
```

### Step 2 — Show the scenarios to the user
Present the Gherkin you've written and ask:
1. Are there any scenarios to add, remove, or change?
2. Which **project**, **suite** (if multi-suite), and **section** should these be imported into?

Wait for confirmation before proceeding.

### Step 3 — Import confirmed scenarios
Once the user approves the scenarios and confirms the target location, call
`import_scenarios` with:
- `content` = the final Gherkin text (including the Feature header)
- `project` = the confirmed project name or ID
- `suite` = the confirmed suite name or ID (omit for single-suite projects)
- `section` = the confirmed section name or ID
- `fmt` = "gherkin"

### Step 4 — Report results
Tell the user which cases were created and their TestRail IDs.
If any failed to create, report the error details.

## Rules
- Always show the scenarios to the user and get approval before importing
- Do not import cases the user has not reviewed and confirmed
- Write scenarios in plain business language — not technical implementation details
- Preserve exact wording once the user approves — do not modify during import
- If the description is too vague to write testable scenarios, ask clarifying questions
  before attempting to write anything
"""
