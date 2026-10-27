After checking the schema and loaded fact families, construct a bounded goal. For example:

```prolog
% Find the declared definition; confirm its file and line in the result.
defines(render_prompt, Arity, Params, File, Line)

% Inspect simple local calls within a named top-level function.
calls(render_prompt, CallerArity, local(Callee, ArgCount), File, Line)
```

Bind a specific file when names or arities may be ambiguous. Do not join call and definition arities as if they proved a valid Python invocation. An absent call fact is not evidence that no call exists; check the source.
