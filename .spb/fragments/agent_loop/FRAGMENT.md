## Coding workflow

For implementation, debugging, and refactoring, repeat this loop as needed:

1. **Gather context:** Understand the request, expected behavior, and relevant constraints. Read the relevant code, tests, and project guidance. Inspect related behavior and the working tree before editing; preserve unrelated changes. Ask the user when requirements or consequential choices are unclear.
2. **Act:** Make a focused change that fits the existing design. Use tools suited to the task and avoid unrelated edits. For a bug, reproduce it when practical, address the supported cause, and add a regression test. For a refactor, preserve behavior unless the user asks to change it. For a dependency change, check the project's dependency files and verify the intended use.
3. **Verify:** Run focused tests or a reproduction, including relevant edge cases, then broader checks as appropriate. For this project, use `just check` for local quality gates, `just docs` for documentation changes, and `just package-check` for packaging or release changes when feasible. Investigate failures and repeat the loop if needed. Do not assume a change works because it was saved or a command ran.

Use static discovery and runtime tests together; neither replaces reading the code. For multi-step work, give brief progress updates. Report changes, checks run, failures, and any checks you could not run. Do not claim success without evidence.
