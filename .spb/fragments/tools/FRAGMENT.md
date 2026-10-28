Use Symbolic for codebase discovery and bounded structural questions. Its project config scans `src/` and `tests/`; it does not scan `docs/` or the repository's other files.

- `mcp__symbolic__parse` refreshes the configured project and reports scan completeness and failed files.
- Before a query, use `mcp__symbolic__overview` first to confirm the family is loaded, then `mcp__symbolic__schema` to check argument order and types. Both are required. Do not state a concrete signature or sample goal until verified from the schema.
- `mcp__symbolic__search_functions` finds definitions by name. `mcp__symbolic__query` proves a goal over the loaded facts. `mcp__symbolic__search` finds indexed comments and other indexed prose, not definitions.
- Read source files to check context and code Symbolic does not capture. Use the shell to run `pipenv run pytest`, `just check`, `just docs`, and `just package-check` when relevant.

Use the actual Symbolic MCP tool names exposed by the harness. If MCP is unavailable or its parse fails, quote the error and use the installed `symbolic parse`, `symbolic overview`, and `symbolic query` CLI against this project's configured database when possible. The CLI has no `schema` command: use Symbolic's documented fact schema and confirm families with `overview`. Tool metadata in `.spb/config.yaml` describes tools; it does not connect an MCP server.
