# TestRail Import Instructions — BDD Scenarios

These instructions apply when importing test scenarios into TestRail.
Follow them exactly for every test case you create.

---

## Template

Always use the **Behaviour Driven Development** template when creating test cases.
Do not use any other template (e.g. Test Case (Text), Test Case (Steps), Exploratory Session).

### Available templates (project: cortado_clone)

| template_id | Name |
|-------------|------|
| 1 | Test Case (Text) |
| 2 | Test Case (Steps) |
| 3 | Exploratory Session |
| **4** | **Behaviour Driven Development** ← always use this |

When calling the API or MCP `add_case` / `update_case`, always pass `"template_id": 4`.

---

## Field Mapping

When given a BDD scenario, map its content to TestRail fields as follows:

| Source                    | TestRail Field                    | API field name                    |
|---------------------------|-----------------------------------|-----------------------------------|
| Scenario description/name | **Title**                         | `title`                           |
| Given / When / Then block | **BDD Scenarios**                 | `custom_testrail_bdd_scenario`    |

### Title
- Use the scenario name or description as the test case title.
- Write it as a plain sentence, not prefixed with "Scenario:".
- Example: `User logs in with valid credentials`

### BDD Scenarios — `custom_testrail_bdd_scenario`
- This field requires a **JSON array** — passing a plain string will be rejected with a 400 error.
- Each element in the array is an object with a `"content"` key.
- **One test case = one scenario = one array element** containing the full Given/When/Then block as a single string.
- Do NOT split each Given/When/Then line into separate array elements.
- Preserve the original wording — do not paraphrase or summarise.
- Each step should be on its own line within the content string (`\n` separated).

#### Correct format
```json
"custom_testrail_bdd_scenario": [
  {
    "content": "Given the user is on the login page\nWhen they enter valid credentials and click Sign In\nThen they should be redirected to the dashboard"
  }
]
```

#### Incorrect formats (do not use)
```json
// ❌ Plain string — rejected by API
"custom_testrail_bdd_scenario": "Given the user is on the login page\n..."

// ❌ One element per step — creates multiple scenarios instead of one
"custom_testrail_bdd_scenario": [
  {"content": "Given the user is on the login page"},
  {"content": "When they enter valid credentials"},
  {"content": "Then they should be redirected to the dashboard"}
]
```

---

## API Notes

- `custom_testrail_bdd_scenario` is field `type_id: 13` (TestRail proprietary BDD Scenario type).
- The field accepts writes via the REST API when the correct array format is used.
- Passing `None` or an empty string will silently fail — always pass the array.
- `custom_preconds` (Preconditions) is writable as plain text and can be used as a fallback if needed, but the BDD Scenarios field is preferred.

---

## Behaviour

- Create one test case per scenario.
- Do not merge multiple scenarios into one test case.
- Do not add steps, notes, or commentary beyond what is in the source material.
- If a scenario is ambiguous or incomplete, flag it rather than guessing.
- Confirm the target section before creating any cases — ask if unsure.
