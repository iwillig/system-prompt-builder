Python fact shapes useful here:

```prolog
defines(Name, Arity, Params, File, Line)
calls(Caller, CallerArity, local(Name, ArgCount), File, Line)
calls(Caller, CallerArity, member(Object, Method, ArgCount), File, Line)
comment(File, Line, Text)
```

File values from a scan are absolute paths. `Params` and `Text` are text values. Use file and line, not just name and arity, to distinguish same-named methods. Query results describe syntax, not execution.
