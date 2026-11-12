## Evidence-based debugging

Treat your first explanation as a hypothesis, not a fact. Your knowledge of this codebase and its runtime behavior is limited. Reproduce the issue when practical, inspect the relevant code and tests, and use observations to test competing explanations. State uncertainty and ask for missing information when the evidence is not enough. Do not invent tool results, causes, or verification.

Use the Symbolic MCP tools when they can help answer a specific codebase question:

- Use `parse` to refresh project facts when needed. Check scan completeness and failed files before relying on the results. The project's Symbolic configuration defines the scan scope.
- Use `search_functions` to find definitions. For structural questions, check `overview` and `schema` before using `query`; use returned file and line evidence to guide source inspection.
- Treat results as bounded observations, not proof of runtime behavior or a complete call graph. A query with no results does not prove that behavior is absent. Read the source and tests, including files outside the scan.
- If Symbolic is unavailable or cannot answer the question, inspect the code directly and use suitable search and test tools. Report relevant limits or failures; do not treat a tool error as a negative result.

Verify a proposed fix with a focused test or reproduction when possible. Report what you checked, the result, and any remaining uncertainty.
