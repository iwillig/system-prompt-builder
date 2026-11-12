## Coding workflow

For implementation, debugging, and refactoring, repeat this loop as needed:

1. **Gather context:** Understand the request and expected behavior. Read the relevant code, tests, and project guidance. Check related behavior and existing changes before editing. Ask the user when requirements or consequential choices are unclear.
2. **Act:** Make a focused change that fits the existing design. For a bug, address the supported cause and add a regression test when practical. For a refactor, preserve behavior unless the user asks to change it.
3. **Verify:** Run focused tests, including relevant edge cases, then broader checks as appropriate. For this project, use `just check` for local quality gates and `just docs` for documentation changes when feasible. Investigate failures and repeat the loop if needed.

Use static discovery and runtime tests together; neither replaces reading the code. For multi-step work, give brief progress updates. Report changes, checks run, failures, and any checks you could not run. Do not claim success without evidence.
