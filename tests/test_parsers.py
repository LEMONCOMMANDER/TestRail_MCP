"""
Tests for src/testrail_mcp/parsers.py

Covers:
  - parse() dispatcher for gherkin / markdown / numbered
  - _parse_gherkin: Scenario / Scenario Outline / steps
  - _parse_markdown: ## headings, ### headings, **bold-only lines** (new)
  - _parse_numbered: numbered list items
  - parse_hierarchy: ## sections, ### sub-sections, #### / bold case titles, BDD steps
  - HierarchyNode dataclass
"""

import pytest
from testrail_mcp.parsers import parse, parse_hierarchy, ParsedScenario, HierarchyNode


# ── parse() dispatcher ────────────────────────────────────────────────────────

class TestParseDispatcher:
    def test_unsupported_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported format"):
            parse("anything", "xml")

    def test_format_is_case_insensitive(self):
        content = "1. A thing\n2. Another thing"
        assert parse(content, "NUMBERED") == parse(content, "numbered")


# ── Gherkin parser ────────────────────────────────────────────────────────────

class TestParseGherkin:
    def test_single_scenario(self):
        content = """\
Feature: Auth

Scenario: User logs in
  Given the login page
  When valid credentials are entered
  Then the dashboard is shown
"""
        results = parse(content, "gherkin")
        assert len(results) == 1
        assert results[0].title == "User logs in"
        assert "Given the login page" in results[0].bdd_content
        assert "Then the dashboard is shown" in results[0].bdd_content

    def test_multiple_scenarios(self):
        content = """\
Scenario: Happy path
  Given precondition
  When action
  Then outcome

Scenario: Sad path
  Given precondition
  When bad action
  Then error shown
"""
        results = parse(content, "gherkin")
        assert len(results) == 2
        assert results[0].title == "Happy path"
        assert results[1].title == "Sad path"

    def test_scenario_outline(self):
        content = """\
Scenario Outline: Login with <role>
  Given a <role> user
  When they log in
  Then they see their dashboard
"""
        results = parse(content, "gherkin")
        assert len(results) == 1
        assert results[0].title == "Login with <role>"

    def test_and_but_steps_collected(self):
        content = """\
Scenario: Multi-step
  Given precondition
  And another precondition
  When action
  But not this
  Then outcome
"""
        results = parse(content, "gherkin")
        assert len(results) == 1
        bdd = results[0].bdd_content
        assert "And another precondition" in bdd
        assert "But not this" in bdd

    def test_empty_content_returns_empty(self):
        assert parse("Feature: Nothing here", "gherkin") == []

    def test_scenario_with_no_steps(self):
        content = "Scenario: Title only\n"
        results = parse(content, "gherkin")
        assert len(results) == 1
        assert results[0].title == "Title only"
        assert results[0].bdd_content is None


# ── Markdown parser ───────────────────────────────────────────────────────────

class TestParseMarkdown:
    def test_h2_heading_as_title(self):
        content = """\
## User logs in
Given the login page
When credentials entered
Then dashboard shown
"""
        results = parse(content, "markdown")
        assert len(results) == 1
        assert results[0].title == "User logs in"
        assert results[0].bdd_content is not None

    def test_h3_heading_as_title(self):
        content = """\
### Sub scenario
Given something
When something
Then something
"""
        results = parse(content, "markdown")
        assert len(results) == 1
        assert results[0].title == "Sub scenario"

    def test_bold_only_line_as_title(self):
        """New: **bold-only lines** should be treated as case titles."""
        content = """\
**My bold scenario**
Given a user
When they do something
Then it works
"""
        results = parse(content, "markdown")
        assert len(results) == 1
        assert results[0].title == "My bold scenario"
        assert results[0].bdd_content is not None
        assert "Given a user" in results[0].bdd_content

    def test_bold_inline_not_treated_as_title(self):
        """A line with bold inline (not the full line) should NOT become a title."""
        content = """\
## Actual title
Given a **bold word** in a step
When action
Then outcome
"""
        results = parse(content, "markdown")
        assert len(results) == 1
        assert results[0].title == "Actual title"
        # The bold-inline step should be body, not a new case title
        assert "Given a **bold word** in a step" in results[0].bdd_content

    def test_mixed_h2_and_bold(self):
        """## sections and **bold** titles can coexist in the same file."""
        content = """\
## Section heading
**First scenario**
Given step 1
When step 2
Then step 3

**Second scenario**
Given step A
When step B
Then step C
"""
        results = parse(content, "markdown")
        # ## heading becomes a title (with no body since bold line follows immediately)
        # then each bold line becomes its own title
        titles = [r.title for r in results]
        assert "Section heading" in titles
        assert "First scenario" in titles
        assert "Second scenario" in titles

    def test_non_bdd_body_goes_to_description(self):
        content = """\
## A scenario
This is a plain description
with no BDD steps
"""
        results = parse(content, "markdown")
        assert len(results) == 1
        assert results[0].bdd_content is None
        assert results[0].description is not None
        assert "plain description" in results[0].description

    def test_multiple_headings(self):
        content = """\
## First
Given a
When b
Then c

## Second
Given x
When y
Then z
"""
        results = parse(content, "markdown")
        assert len(results) == 2
        assert results[0].title == "First"
        assert results[1].title == "Second"

    def test_empty_returns_empty(self):
        assert parse("", "markdown") == []


# ── Numbered parser ───────────────────────────────────────────────────────────

class TestParseNumbered:
    def test_dot_separator(self):
        content = "1. First item\n2. Second item\n3. Third item"
        results = parse(content, "numbered")
        assert len(results) == 3
        assert results[0].title == "First item"
        assert results[2].title == "Third item"

    def test_paren_separator(self):
        content = "1) First\n2) Second"
        results = parse(content, "numbered")
        assert len(results) == 2
        assert results[0].title == "First"

    def test_non_numbered_lines_ignored(self):
        content = "1. Valid\nThis line is skipped\n2. Also valid"
        results = parse(content, "numbered")
        assert len(results) == 2

    def test_titles_only_no_bdd(self):
        content = "1. A test case"
        results = parse(content, "numbered")
        assert results[0].bdd_content is None
        assert results[0].description is None

    def test_empty_returns_empty(self):
        assert parse("", "numbered") == []


# ── parse_hierarchy ───────────────────────────────────────────────────────────

class TestParseHierarchy:
    def test_returns_hierarchy_nodes(self):
        content = "## My Section\n"
        nodes = parse_hierarchy(content)
        assert len(nodes) == 1
        assert isinstance(nodes[0], HierarchyNode)

    def test_h2_creates_level2_node(self):
        content = "## Top Section\n"
        nodes = parse_hierarchy(content)
        assert nodes[0].level == 2
        assert nodes[0].name == "Top Section"
        assert nodes[0].parent_name is None

    def test_h3_creates_level3_node_with_parent(self):
        content = "## Parent\n### Child\n"
        nodes = parse_hierarchy(content)
        assert len(nodes) == 2
        assert nodes[1].level == 3
        assert nodes[1].name == "Child"
        assert nodes[1].parent_name == "Parent"

    def test_h3_without_preceding_h2_has_no_parent(self):
        content = "### Orphan\n"
        nodes = parse_hierarchy(content)
        assert len(nodes) == 1
        assert nodes[0].parent_name is None

    def test_h1_is_ignored(self):
        content = "# Document Title\n## Real Section\n"
        nodes = parse_hierarchy(content)
        assert len(nodes) == 1
        assert nodes[0].name == "Real Section"

    def test_bold_line_creates_case(self):
        content = """\
## My Section
**My Test Case**
Given a precondition
When an action
Then an outcome
"""
        nodes = parse_hierarchy(content)
        assert len(nodes) == 1
        assert len(nodes[0].cases) == 1
        assert nodes[0].cases[0].title == "My Test Case"

    def test_h4_line_creates_case(self):
        content = """\
## My Section
#### My H4 Case
Given something
When something
Then something
"""
        nodes = parse_hierarchy(content)
        assert len(nodes) == 1
        assert len(nodes[0].cases) == 1
        assert nodes[0].cases[0].title == "My H4 Case"

    def test_bdd_steps_captured_as_bdd_content(self):
        content = """\
## Auth
**Login happy path**
Given the user is on the login page
When they enter valid credentials
Then they are redirected to the dashboard
"""
        nodes = parse_hierarchy(content)
        case = nodes[0].cases[0]
        assert case.bdd_content is not None
        assert "Given the user is on the login page" in case.bdd_content
        assert "Then they are redirected to the dashboard" in case.bdd_content

    def test_multiple_cases_per_section(self):
        content = """\
## Auth
**Happy path**
Given valid creds
When login
Then success

**Sad path**
Given invalid creds
When login
Then error shown
"""
        nodes = parse_hierarchy(content)
        assert len(nodes) == 1
        assert len(nodes[0].cases) == 2
        assert nodes[0].cases[0].title == "Happy path"
        assert nodes[0].cases[1].title == "Sad path"

    def test_nested_sections_with_cases(self):
        content = """\
## Auth
### Login
**Happy path**
Given valid user
When login
Then success

### Logout
**Logs out successfully**
Given logged in user
When logout clicked
Then redirected to login
"""
        nodes = parse_hierarchy(content)
        assert len(nodes) == 3  # Auth, Login, Logout

        auth = nodes[0]
        login = nodes[1]
        logout = nodes[2]

        assert auth.name == "Auth"
        assert auth.level == 2
        assert len(auth.cases) == 0  # no direct cases under ##

        assert login.name == "Login"
        assert login.level == 3
        assert login.parent_name == "Auth"
        assert len(login.cases) == 1

        assert logout.name == "Logout"
        assert logout.level == 3
        assert logout.parent_name == "Auth"
        assert len(logout.cases) == 1

    def test_multiple_h2_sections(self):
        content = """\
## Section A
**Case A1**
Given a
When a
Then a

## Section B
**Case B1**
Given b
When b
Then b

**Case B2**
Given c
When c
Then c
"""
        nodes = parse_hierarchy(content)
        assert len(nodes) == 2
        assert nodes[0].name == "Section A"
        assert len(nodes[0].cases) == 1
        assert nodes[1].name == "Section B"
        assert len(nodes[1].cases) == 2

    def test_parent_name_updates_after_new_h2(self):
        """### sections should reference their nearest preceding ## as parent."""
        content = """\
## First
### Sub of first

## Second
### Sub of second
"""
        nodes = parse_hierarchy(content)
        sub_first = next(n for n in nodes if n.name == "Sub of first")
        sub_second = next(n for n in nodes if n.name == "Sub of second")
        assert sub_first.parent_name == "First"
        assert sub_second.parent_name == "Second"

    def test_empty_content_returns_empty(self):
        assert parse_hierarchy("") == []

    def test_sections_with_no_cases_still_returned(self):
        content = "## Empty Section\n"
        nodes = parse_hierarchy(content)
        assert len(nodes) == 1
        assert nodes[0].cases == []

    def test_non_bdd_case_body_goes_to_description(self):
        content = """\
## Section
**A plain case**
This is a plain description
not a BDD step
"""
        nodes = parse_hierarchy(content)
        case = nodes[0].cases[0]
        assert case.bdd_content is None
        assert case.description is not None
        assert "plain description" in case.description

    def test_document_order_preserved(self):
        content = """\
## Alpha
**Case 1**
## Beta
**Case 2**
## Gamma
**Case 3**
"""
        nodes = parse_hierarchy(content)
        assert [n.name for n in nodes] == ["Alpha", "Beta", "Gamma"]

    def test_real_world_structure(self):
        """Mirrors the cortado_clone scenario file structure that triggered the original bug."""
        content = """\
# Testing Scenarios

## User Authentication

**User registers with valid credentials**
Given the registration page is open
When valid credentials are submitted
Then the account is created

**User cannot register with duplicate email**
Given the registration page is open
When an existing email is used
Then an error message is displayed

## Dashboard

### Overview

**Dashboard loads correctly**
Given the user is logged in
When the dashboard page is accessed
Then all widgets are visible
"""
        nodes = parse_hierarchy(content)

        names = [n.name for n in nodes]
        assert "User Authentication" in names
        assert "Dashboard" in names
        assert "Overview" in names

        auth = next(n for n in nodes if n.name == "User Authentication")
        assert len(auth.cases) == 2
        assert auth.cases[0].title == "User registers with valid credentials"
        assert auth.cases[1].title == "User cannot register with duplicate email"

        overview = next(n for n in nodes if n.name == "Overview")
        assert overview.parent_name == "Dashboard"
        assert len(overview.cases) == 1
        assert overview.cases[0].title == "Dashboard loads correctly"

