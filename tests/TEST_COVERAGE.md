# Test Coverage

54 tests across 2 files. No live TestRail connection required.

Run with: `uv run pytest tests/ -v`

---

## test_parsers.py — 38 tests

Tests the pure parsing logic in `src/testrail_mcp/parsers.py`. No mocking needed — inputs are strings, outputs are dataclass lists.

---

### Dispatcher (2 tests)

| Test | What it checks | Why it matters |
|------|---------------|----------------|
| `test_unsupported_format_raises` | `parse("anything", "xml")` raises `ValueError: Unsupported format` | Confirms bad format strings fail loudly rather than silently returning nothing |
| `test_format_is_case_insensitive` | `parse(content, "NUMBERED")` == `parse(content, "numbered")` | Format strings from agents may be any case — this should never cause a failure |

---

### Gherkin parser (6 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_single_scenario` | One `Scenario:` block is parsed into one `ParsedScenario` | `title == "User logs in"`, `"Given the login page" in bdd_content` |
| `test_multiple_scenarios` | Two `Scenario:` blocks produce two results in document order | `len == 2`, titles match |
| `test_scenario_outline` | `Scenario Outline:` keyword is treated the same as `Scenario:` | `title == "Login with <role>"` |
| `test_and_but_steps_collected` | `And` and `But` step lines are included in `bdd_content` | Both step types present in output |
| `test_empty_content_returns_empty` | A file with only a `Feature:` line (no scenarios) returns `[]` | `result == []` |
| `test_scenario_with_no_steps` | A scenario with a title but no steps produces a case with `bdd_content=None` | `title` set, `bdd_content is None` |

---

### Markdown parser (8 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_h2_heading_as_title` | `## heading` becomes the case title; BDD steps underneath become `bdd_content` | `title == "User logs in"`, `bdd_content is not None` |
| `test_h3_heading_as_title` | `### heading` also works as a case title | `title == "Sub scenario"` |
| `test_bold_only_line_as_title` | **New behaviour:** a line that is entirely `**bold**` becomes a case title | `title == "My bold scenario"`, `bdd_content` contains the steps |
| `test_bold_inline_not_treated_as_title` | A line like `Given a **bold word** in a step` is body text, not a new title | Only 1 result; the step appears in `bdd_content`, not as a title |
| `test_mixed_h2_and_bold` | `##` headings and `**bold**` titles coexist in the same file | All three titles (`Section heading`, `First scenario`, `Second scenario`) present |
| `test_non_bdd_body_goes_to_description` | Body lines with no Given/When/Then land in `description`, not `bdd_content` | `bdd_content is None`, `"plain description" in description` |
| `test_multiple_headings` | Multiple `##` headings each produce their own case, in order | `len == 2`, titles match document order |
| `test_empty_returns_empty` | Empty string input returns `[]` | `result == []` |

---

### Numbered list parser (5 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_dot_separator` | Lines like `1. Title` parsed as case titles | `len == 3`, `titles[0] == "First item"` |
| `test_paren_separator` | Lines like `1) Title` also parsed | `titles[0] == "First"` |
| `test_non_numbered_lines_ignored` | Non-numbered lines between items are silently skipped | `len == 2` |
| `test_titles_only_no_bdd` | Numbered items produce title-only cases with no body | `bdd_content is None`, `description is None` |
| `test_empty_returns_empty` | Empty string returns `[]` | `result == []` |

---

### Hierarchy parser (17 tests)

Tests the `parse_hierarchy()` function which powers `import_from_hierarchy`.

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_returns_hierarchy_nodes` | Output contains `HierarchyNode` instances | `isinstance(nodes[0], HierarchyNode)` |
| `test_h2_creates_level2_node` | `## heading` produces a node with `level=2`, `parent_name=None` | `name == "Top Section"`, `parent_name is None` |
| `test_h3_creates_level3_node_with_parent` | `### heading` under a `##` gets `level=3` and `parent_name` set | `nodes[1].parent_name == "Parent"` |
| `test_h3_without_preceding_h2_has_no_parent` | `###` with no preceding `##` gets `parent_name=None` | `parent_name is None` |
| `test_h1_is_ignored` | `# Document Title` lines are silently skipped | `len == 1`, only the `##` section is returned |
| `test_bold_line_creates_case` | `**bold line**` under a section creates a case in that section | `len(nodes[0].cases) == 1`, `title == "My Test Case"` |
| `test_h4_line_creates_case` | `#### heading` under a section also creates a case | `len(nodes[0].cases) == 1`, `title == "My H4 Case"` |
| `test_bdd_steps_captured_as_bdd_content` | Given/When/Then lines under a case title go into `bdd_content` | Both `Given` and `Then` lines present in `case.bdd_content` |
| `test_multiple_cases_per_section` | Two bold-line cases under one `##` both land in that section | `len(nodes[0].cases) == 2`, titles correct |
| `test_nested_sections_with_cases` | `##` + `###` + cases: Auth has 0 cases, Login and Logout have 1 each | Correct levels, parent_names, and case counts |
| `test_multiple_h2_sections` | Two `##` sections with different case counts are fully independent | Section A: 1 case, Section B: 2 cases |
| `test_parent_name_updates_after_new_h2` | When a second `##` appears, subsequent `###` reference it, not the first | `sub_second.parent_name == "Second"` |
| `test_empty_content_returns_empty` | Empty string returns `[]` | `result == []` |
| `test_sections_with_no_cases_still_returned` | A `##` with no cases underneath is still returned as a node | `len == 1`, `cases == []` |
| `test_non_bdd_case_body_goes_to_description` | Case body with no BDD keywords goes into `description`, not `bdd_content` | `bdd_content is None`, `"plain description" in description` |
| `test_document_order_preserved` | Sections appear in the same order as the document | `[n.name for n in nodes] == ["Alpha", "Beta", "Gamma"]` |
| `test_real_world_structure` | Full realistic document: `# title`, `##` section, `###` subsection, `**bold**` cases, BDD steps | Auth has 2 cases with correct titles; Overview is nested under Dashboard with correct parent and 1 case |

---

## test_workflows.py — 16 tests

Tests `import_from_hierarchy` in `src/testrail_mcp/tools/workflows.py` end-to-end using a mocked TestRail client. No API calls are made.

---

### Guards (3 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_empty_content_returns_early` | Empty string returns immediately without hitting the API | `total_parsed == 0`, `sections_created == []`, `"No sections" in message` |
| `test_binary_content_rejected` | Content containing null bytes raises `ValueError: binary` | `pytest.raises(ValueError, match="binary")` |
| `test_oversized_content_rejected` | Content over 500KB raises `ValueError: too large` | `pytest.raises(ValueError, match="too large")` |

---

### Section creation (4 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_h2_creates_top_level_section` | `## Auth` results in a section named "Auth" with no parent | `name == "Auth"`, `parent_id is None` |
| `test_h3_parent_id_set_to_h2_id` | `### Login` under `## Auth` gets `parent_id` equal to Auth's section ID | `sections_created[1]["parent_id"] == auth_id` |
| `test_multiple_h2_sections_all_created` | Two `##` headings result in two separate sections | Both names present in `sections_created` |
| `test_empty_section_still_created` | A `##` with no cases still gets created in TestRail | `len(sections_created) == 1`, `total_parsed == 0` |

---

### Case creation (4 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_case_created_in_section` | A single bold-line case is created and appears in `by_section` | `total_created == 1`, `cases[0]["title"] == "Login"` |
| `test_multiple_cases_in_one_section` | Two cases in one section are both created | `total_parsed == 2`, `total_created == 2` |
| `test_cases_split_across_sections` | Cases spread across two sections are all created correctly | `total_parsed == 3`, `total_created == 3` |
| `test_type_id_and_priority_id_forwarded` | `type_id=2, priority_id=3` appear in the actual API body sent to TestRail | `body["type_id"] == 2`, `body["priority_id"] == 3` |

---

### Failure handling (2 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_section_creation_failure_skips_its_cases` | If a section fails to create, its cases appear in `failed` rather than crashing | `any(f["title"] == "C2" for f in r["failed"])` |
| `test_case_creation_failure_reported` | If a case API call throws, the case is in `failed` with the error message | `total_created == 0`, `failed[0]["title"] == "Fail"`, error message present |

---

### Response shape (3 tests)

| Test | What it checks | Key assertions |
|------|---------------|----------------|
| `test_response_has_resolved_block` | Response includes a `resolved` dict with project info | `"resolved" in r`, `"project" in r["resolved"]`, `"project_id" in r["resolved"]` |
| `test_by_section_has_required_keys` | Each entry in `by_section` has all expected keys | `section_name`, `section_id`, `cases_parsed`, `cases_created`, `cases` all present |
| `test_message_mentions_counts` | The human-readable `message` field references the created counts | `"1" in r["message"]` |

