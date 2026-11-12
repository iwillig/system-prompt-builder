%% Project query helpers, adapted from symbolic-tools' default rules.
%% calls/5 = calls(Caller, CallerArity, CallSpec, File, Line).

%% Keep call-based queries valid even when a scan contains no calls.
calls(none, 0, none, none, 0) :- fail.

%% Distinct call targets for a function name (across arities).
callees(Fun, Callees) :-
    findall(C, calls(Fun, _CallerArity, C, _, _), Raw),
    sort(Raw, Callees).

%% Distinct local callers of a function/arity.
callers(Fun, Arity, Callers) :-
    findall(Caller, calls(Caller, _CallerArity, local(Fun, Arity), _, _), Raw),
    sort(Raw, Callers).

%% Direct recursion within the same file and arity.
self_recursive(Fun, Arity, File) :-
    defines(Fun, Arity, _, File, _),
    calls(Fun, Arity, local(Fun, Arity), File, _).
