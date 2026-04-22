"""
Parsers for converting file content into structured scenario objects
ready for import into TestRail.

Supported formats:
  gherkin   — Feature/Scenario/Given/When/Then blocks
  markdown  — ## or ### headings as titles, body as BDD content
  numbered  — numbered list items as titles (no step content)

Hierarchy parsing (parse_hierarchy):
  Reads a structured markdown document and returns a list of HierarchyNode
  objects representing a two-level section tree (## → ###) with test cases
  detected from #### headings and **bold-only lines**.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class ParsedScenario:
    """A single test scenario parsed from a file."""
    title: str
    bdd_content: str | None = None  # Given/When/Then block
    description: str | None = None  # Free-text description if no BDD steps


@dataclass
class HierarchyNode:
    """
    A section node produced by parse_hierarchy.

    level 2 = ## heading  → top-level TestRail section
    level 3 = ### heading → subsection nested under its parent_name
    cases holds all test cases detected under this heading before the next
    same-or-higher heading.
    """
    name: str
    level: int          # 2 or 3
    parent_name: str | None
    cases: list[ParsedScenario] = field(default_factory=list)


def parse(content: str, fmt: str) -> list[ParsedScenario]:
    """
    Parse file content into a list of ParsedScenario objects.

    fmt must be one of: "gherkin", "markdown", "numbered"
    Raises ValueError for unsupported formats.
    """
    fmt = fmt.lower().strip()
    if fmt == "gherkin":
        return _parse_gherkin(content)
    elif fmt == "markdown":
        return _parse_markdown(content)
    elif fmt == "numbered":
        return _parse_numbered(content)
    else:
        raise ValueError(
            f"Unsupported format '{fmt}'. "
            "Supported formats: gherkin, markdown, numbered"
        )


# ── Gherkin ───────────────────────────────────────────────────────────────────

def _parse_gherkin(content: str) -> list[ParsedScenario]:
    """
    Parse Gherkin content into scenarios.

    Splits on 'Scenario:' and 'Scenario Outline:' keywords.
    Each scenario's name becomes the title; the Given/When/Then
    block becomes the BDD content.

    Example input:
        Feature: User Authentication

        Scenario: User logs in with valid credentials
            Given the user is on the login page
            When they enter valid credentials
            Then they should be redirected to the dashboard

        Scenario: User cannot log in with invalid password
            Given the user is on the login page
            When they enter an invalid password
            Then they should see an error message
    """
    scenarios: list[ParsedScenario] = []
    lines = content.splitlines()

    current_title: str | None = None
    current_steps: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Detect scenario boundary
        if stripped.lower().startswith("scenario outline:"):
            if current_title:
                scenarios.append(_build_gherkin_scenario(current_title, current_steps))
            current_title = stripped[len("scenario outline:"):].strip()
            current_steps = []

        elif stripped.lower().startswith("scenario:"):
            if current_title:
                scenarios.append(_build_gherkin_scenario(current_title, current_steps))
            current_title = stripped[len("scenario:"):].strip()
            current_steps = []

        # Collect steps (Given / When / Then / And / But)
        elif current_title and stripped.lower().startswith(
            ("given ", "when ", "then ", "and ", "but ", "* ")
        ):
            current_steps.append(stripped)

        # Skip Feature:, Background:, blank lines, comments
        # (anything else while we have a current scenario — ignore)

    # Flush last scenario
    if current_title:
        scenarios.append(_build_gherkin_scenario(current_title, current_steps))

    return scenarios


def _build_gherkin_scenario(title: str, steps: list[str]) -> ParsedScenario:
    bdd = "\n".join(steps) if steps else None
    return ParsedScenario(title=title, bdd_content=bdd)


# ── Markdown ──────────────────────────────────────────────────────────────────

def _parse_markdown(content: str) -> list[ParsedScenario]:
    """
    Parse Markdown content into scenarios.

    Uses ## or ### headings as scenario titles. The content under
    each heading (until the next heading) is treated as BDD steps
    if it contains Given/When/Then lines, or as a description otherwise.

    Example input:
        ## User logs in with valid credentials
        Given the user is on the login page
        When they enter valid credentials
        Then they should be redirected to the dashboard

        ## User cannot log in with invalid password
        Given the user is on the login page
        When they enter an invalid password
        Then they should see an error message
    """
    scenarios: list[ParsedScenario] = []
    lines = content.splitlines()

    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        stripped = line.strip()

        # ## or ### heading → new scenario title
        if stripped.startswith("## ") or stripped.startswith("### "):
            if current_title:
                scenarios.append(_build_markdown_scenario(current_title, current_body))
            # Strip leading #s and whitespace
            current_title = stripped.lstrip("#").strip()
            current_body = []

        # **bold-only line** → new scenario title (common in exported docs)
        elif re.match(r'^\*\*[^*]+\*\*$', stripped):
            if current_title:
                scenarios.append(_build_markdown_scenario(current_title, current_body))
            current_title = stripped[2:-2].strip()
            current_body = []

        elif current_title and stripped:
            current_body.append(stripped)

    if current_title:
        scenarios.append(_build_markdown_scenario(current_title, current_body))

    return scenarios


def _build_markdown_scenario(title: str, body_lines: list[str]) -> ParsedScenario:
    if not body_lines:
        return ParsedScenario(title=title)

    body = "\n".join(body_lines)
    # If any line looks like a BDD step, treat the whole block as BDD content
    bdd_keywords = ("given ", "when ", "then ", "and ", "but ")
    has_bdd = any(line.lower().startswith(bdd_keywords) for line in body_lines)

    if has_bdd:
        return ParsedScenario(title=title, bdd_content=body)
    else:
        return ParsedScenario(title=title, description=body)


# ── Numbered list ─────────────────────────────────────────────────────────────

def _parse_numbered(content: str) -> list[ParsedScenario]:
    """
    Parse a numbered list into scenarios (titles only, no step content).

    Example input:
        1. User can log in with valid credentials
        2. User cannot log in with invalid password
        3. User is locked out after 5 failed attempts
    """
    scenarios: list[ParsedScenario] = []

    for line in content.splitlines():
        stripped = line.strip()
        match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if match:
            scenarios.append(ParsedScenario(title=match.group(1).strip()))

    return scenarios


# ── Hierarchy parser ──────────────────────────────────────────────────────────

def parse_hierarchy(content: str) -> list[HierarchyNode]:
    """
    Parse a structured markdown document into a two-level section hierarchy.

    Heading mapping:
      #   (h1) → ignored (document title)
      ##  (h2) → top-level TestRail section
      ### (h3) → subsection nested under the nearest ## section

    Within each section, case titles are detected from:
      #### headings       — explicit case title marker
      **bold-only lines** — common in exported / hand-written docs

    BDD step lines (Given/When/Then/And/But) and any other non-blank lines
    under a case title are collected as the case body.

    Returns a list of HierarchyNode objects in document order.
    """
    nodes: list[HierarchyNode] = []
    # current_h2_name tracks the nearest ## so ### can reference it as parent
    current_h2_name: str | None = None
    current_node: HierarchyNode | None = None

    current_case_title: str | None = None
    current_case_body: list[str] = []

    def _flush_case() -> None:
        nonlocal current_case_title, current_case_body
        if current_case_title is not None and current_node is not None:
            current_node.cases.append(
                _build_markdown_scenario(current_case_title, current_case_body)
            )
        current_case_title = None
        current_case_body = []

    for line in content.splitlines():
        stripped = line.strip()

        # ## heading → new top-level section
        if re.match(r'^## [^#]', stripped):
            _flush_case()
            name = stripped[3:].strip()
            current_h2_name = name
            node = HierarchyNode(name=name, level=2, parent_name=None)
            nodes.append(node)
            current_node = node

        # ### heading → subsection
        elif re.match(r'^### [^#]', stripped):
            _flush_case()
            name = stripped[4:].strip()
            node = HierarchyNode(name=name, level=3, parent_name=current_h2_name)
            nodes.append(node)
            current_node = node

        # #### heading → case title
        elif re.match(r'^#### ', stripped) and current_node is not None:
            _flush_case()
            current_case_title = stripped[5:].strip()
            current_case_body = []

        # **bold-only line** → case title
        elif re.match(r'^\*\*[^*]+\*\*$', stripped) and current_node is not None:
            _flush_case()
            current_case_title = stripped[2:-2].strip()
            current_case_body = []

        # Body line for the current case
        elif current_case_title is not None and stripped:
            current_case_body.append(stripped)

        # Blank lines and h1 lines (#) are silently skipped

    _flush_case()
    return nodes


