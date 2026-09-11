## What & why

<!-- short description; link the issue -->

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `pytest` passes
- [ ] new URL-fetching code goes through `utilikit.safefetch` / `assert_host_allowed`
- [ ] heavy optional deps are behind a function-local import + `FeatureUnavailable`
- [ ] new config added to `Settings` **and** `.env.example`
- [ ] a test was added
- [ ] `CHANGELOG.md` updated if behaviour changed
