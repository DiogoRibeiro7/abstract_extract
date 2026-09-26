## Summary

Describe the change and why it is needed.

## Validation

- [ ] `poetry run ruff check .`
- [ ] `poetry run ruff format --check .`
- [ ] `poetry run mypy src`
- [ ] `poetry run pytest --cov=abstract_extract --cov-report=term-missing`

## Checklist

- [ ] The change is focused and does not mix unrelated work.
- [ ] Tests were added or updated when behavior changed.
- [ ] Documentation was updated when public behavior changed.
- [ ] No credentials, secrets, or generated artifacts are included.
- [ ] Any public API change is intentional and described above.
