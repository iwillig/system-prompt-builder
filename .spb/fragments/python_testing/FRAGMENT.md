## Python testing

Use pytest for this project's tests. Run a focused test with `pipenv run pytest tests/path_to_test.py`, and run the full suite with `just test` when appropriate. Use plain assertions, parametrization for related examples, and fixtures such as `tmp_path` and `monkeypatch` to isolate tests. See https://docs.pytest.org/en/stable/.

Use Hegel for property-based tests when a behavior has a useful invariant across many inputs. The development package is `hegeltest`, imported as `hegel`. Write tests with `@hegel.test` and draw inputs with `tc.draw()` from `hegel.generators`; pytest discovers and runs them. Prefer generators that produce valid inputs directly. Pytest fixtures are shared across generated cases, so reset mutable state for each case. Keep example-based tests for concrete regressions and important boundaries. See https://hegel.readthedocs.io/en/latest/.
