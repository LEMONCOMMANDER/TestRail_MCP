# TestRail MCP — Agent Instructions

This file is the single source of truth for any agent using the TestRail MCP server.

**Before starting any task, read this file in full.**

If you do not have filesystem access to this file (e.g. connecting via Docker/HTTP),
call the `getting_started` prompt from the MCP server — it contains the same content.

---

## What This Server Does

Provides tools to interact with TestRail: manage projects, suites, sections, test cases,
test plans, test runs, and results. Also supports importing test scenarios from markdown
or Gherkin files, and generating pass/fail metrics and coverage reports.

---

## Available Prompts

Use a prompt whenever your task matches one — prompts encode the correct workflow,
field rules, and ordering so you don't have to figure them out from scratch.

| Prompt | Use when |
|--------|----------|
| `getting_started` | You need a full tool/prompt index (same as this file, served via MCP) |
| `import_test_scenarios` | Importing a file of scenarios into TestRail (flat or hierarchical) |
| `generate_project_report` | Producing a health/coverage/milestone report for a project |
| `triage_test_failures` | Analysing pass/fail results for a specific test run |
| `create_test_cases_from_description` | Writing BDD scenarios from a description then importing them |

---

## Available Tools

### Discovery — always call these before writing anything

| Tool | What it does |
|------|--------------|
| `list_projects` | List all projects; shows `suite_mode` (1=single suite, 3=multi-suite) |
| `list_suites` | List suites in a project (required when `suite_mode=3`) |
| `list_sections` | List sections/folders in a project or suite |
| `list_cases` | List test cases in a section |
| `list_runs` | List test runs in a project |
| `list_plans` | List test plans in a project |
| `list_milestones` | List milestones in a project |

### Importing Scenarios

| Tool | Use when |
|------|----------|
| `import_from_hierarchy` | **Preferred.** Markdown file has `##`/`###` headings that should become TestRail sections. Auto-creates section tree and imports all cases in one call. |
| `import_scenarios` | Flat file (Gherkin, markdown titles, or numbered list) — all cases go into one existing section. |

**Decision rule:**
```
Do the ## or ### headings in the file represent section/folder names?
  YES → import_from_hierarchy
  NO  → import_scenarios (point it at an existing section)
```

### Writing

| Tool | What it does |
|------|--------------|
| `add_section` | Create a new section/folder |
| `add_case` | Create a single test case manually |
| `update_case` | Update an existing test case |
| `delete_case` | Delete a test case |
| `add_run` | Create a test run |
| `add_plan` | Create a test plan |
| `add_result` | Record a result for a test |
| `add_results_for_cases` | Record results for multiple tests at once |

### Metrics & Reporting

| Tool | What it does |
|------|--------------|
| `get_run_summary` | Pass/fail/coverage stats for a single test run |
| `get_milestone_progress` | Completion metrics across all runs in a milestone |
| `get_project_health` | Aggregate health across the most recent runs in a project |
| `get_coverage_report` | Case coverage breakdown for a project or suite |
| `get_full_project_report` | All of the above in a single call |

---

## Supported Import Formats

| Format | `fmt` value | How case titles are detected |
|--------|-------------|------------------------------|
| Gherkin | `"gherkin"` | `Scenario:` and `Scenario Outline:` keywords |
| Markdown | `"markdown"` | `##`/`###` headings **and** `**bold-only lines**` |
| Numbered list | `"numbered"` | Lines starting with `1.`, `2.`, etc. |

For `import_from_hierarchy`, case titles within each section are detected from:
- `####` headings
- `**bold-only lines**`

---

## BDD Field Rules — Follow Exactly

These rules apply whenever creating a test case using the BDD template.
The import tools handle this automatically. Only relevant if calling `add_case` directly.

- Always pass `"template_id": 4` (Behaviour Driven Development template)
- BDD steps field key: `custom_testrail_bdd_scenario`
- Value **must** be a JSON array: `[{"content": "Given ...\nWhen ...\nThen ..."}]`
- One test case = one array element containing the **full** Given/When/Then block
- Do **not** split each step into a separate array element
- Do **not** pass a plain string — the API will reject it with a 400 error

---

## General Rules

1. **Always discover before writing.** Call `list_projects`, `list_suites`, `list_sections`
   to confirm the correct IDs before any write operation.

2. **Prefer names over IDs in tool calls.** The workflow tools (`import_scenarios`,
   `import_from_hierarchy`) accept project/suite/section names as strings — you don't
   need to look up IDs unless names are ambiguous.

3. **Preserve wording when importing.** Never paraphrase or summarise scenario titles
   or steps — import verbatim.

4. **Report failures clearly.** If any cases fail to create, report the error details
   rather than silently skipping them.

5. **One case per scenario.** Never merge multiple scenarios into one test case.

---

## Recommended Prompt Starter

For any task involving this MCP server, begin your prompt with:

```
Reference instructions.md (or call the getting_started MCP prompt if unavailable).
Then: [your task here]
```

This ensures the agent knows all available tools and prompts before choosing an approach,
and will reach for the right tool on the first attempt rather than iterating.

