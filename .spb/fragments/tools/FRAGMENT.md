Use Symbolic for codebase discovery and bounded structural questions. Its project config scans `src/` and `tests/`; it does not scan `docs/` or the repository's other files.

- `parse` refreshes the configured project and reports scan completeness and failed files.
- `overview` reports loaded predicate families and fact counts; `schema` documents argument order and types. Consult both before a new query.
- `search_functions` finds definitions by name. `query` proves a goal over the loaded facts. `search` finds indexed comments and other indexed prose, not definitions.
- Read source files to check context and code Symbolic does not capture. Use the shell to run `pipenv run pytest`, `just check`, `just docs`, and `just package-check` when relevant.

Use the actual Symbolic MCP tool names exposed by the harness. If MCP is unavailable or its parse fails, quote the error and use the installed `symbolic parse`, `symbolic overview`, and `symbolic query` CLI against this project's configured database when possible. The CLI has no `schema` command: use Symbolic's documented fact schema and confirm families with `overview`. Tool metadata in `.spb/config.yaml` describes tools; it does not connect an MCP server.
