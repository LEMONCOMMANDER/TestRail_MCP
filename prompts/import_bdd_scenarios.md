# TestRail Import Instructions — BDD Scenarios

These instructions apply when importing test scenarios into TestRail.
Follow them exactly for every test case you create.

---

## Template

Always use the **BDD** template when creating test cases.
Do not use any other template (e.g. Test Steps, Exploratory).

---

## Field Mapping

When given a BDD scenario, map its content to TestRail fields as follows:

| Source                        | TestRail Field       |
|-------------------------------|----------------------|
| Scenario description/name     | **Title**            |
| Given / When / Then block     | **BDD Scenarios**    |

### Title
- Use the scenario name or description as the test case title.
- Write it as a plain sentence, not prefixed with "Scenario:".
- Example: `User logs in with valid credentials`

### BDD Scenarios
- Paste the full Given / When / Then block exactly as written.
- Preserve the original wording — do not paraphrase or summarise.
- Each step should be on its own line.
- Example:
  ```
  Given the user is on the login page
  When they enter valid credentials and click Sign In
  Then they should be redirected to the dashboard
  ```

---

## Behaviour

- Create one test case per scenario.
- Do not merge multiple scenarios into one test case.
- Do not add steps, notes, or commentary beyond what is in the source material.
- If a scenario is ambiguous or incomplete, flag it rather than guessing.
- Confirm the target section before creating any cases — ask if unsure.
