Python extraction is syntax-only. `defines/5` records named `def` and `async def`, including nested functions and methods. The name lacks class and enclosing-function qualifiers. Its arity counts declared parameter nodes, including `self`, `cls`, defaults, `*args`, and `**kwargs`; it is not the accepted runtime argument count.

`calls/5` records only restricted positional call syntax inside unique top-level functions. A `local(Name, Count)` or `member(Object, Method, Count)` records the source spelling, not a resolved callee. Keyword arguments, unpacking, class/nested functions, lambdas, and many complex callees are omitted. Python docstrings are not `doc/5`, and `branch/5` does not describe Python control flow.

Check the active scan's `overview` and the MCP `schema` tool or documented fact schema before using any predicate. Missing facts, errors, and incomplete scans are different outcomes. Use source reading and tests for claims the fact base cannot establish.
