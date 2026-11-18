---
name: review
description: Review selected code, files, or a change set for actionable correctness, security, performance, accessibility, maintainability, and test issues.
agent: "Code Reviewer"
argument-hint: "[files or diff] [optional review focus]"
---

Review the selected code (if any) and the target below. Inspect relevant callers, related templates, API behavior, and tests when needed. Do not modify files or apply suggested fixes.

**Review target:** `${input:review-target:Provide file paths or a diff; leave blank to review the current selection}`

**Optional focus:** `${input:review-focus:Correctness, security, performance, accessibility, maintainability, or tests}`

**Current selection, if provided:** `${selection}`

Check for:

- Bugs, regressions, invalid assumptions, and unhandled errors.
- Security issues, especially around student data, input validation, SQL, HTML, and CSV.
- Meaningful performance problems.
- Accessibility issues in HTML, CSS, and interactive JavaScript.
- Maintainability concerns and missing tests for changed behavior.

Return prioritized findings in Markdown, ordered Critical, High, Medium, then Low. Each finding must include a title, exact file and line reference, evidence, impact, and a suggested fix or test. Do not report unsupported concerns or generic style preferences. If there are no actionable findings, state that and identify anything you could not verify. Do not claim tests were run.
