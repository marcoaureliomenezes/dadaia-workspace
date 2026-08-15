## Summary

<!-- 1-3 bullet points describing what this PR changes and why. -->

-

## Type of change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that causes existing functionality to change)
- [ ] Refactor / chore (no functional change)
- [ ] Documentation

## Checklist

- [ ] PR title follows Conventional Commits (`feat:`, `fix:`, `chore:`, etc.)
- [ ] Tests added or updated for new behaviour
- [ ] `poetry run pytest` passes locally
- [ ] `poetry run ruff check . && poetry run ruff format --check .` passes
- [ ] `MYPY_CACHE_DIR=$(mktemp -d) poetry run mypy --strict dadaia_workspace/` passes (redirects the cache outside the repo -- omitting `MYPY_CACHE_DIR` leaves a `.mypy_cache/` in the checkout even with `incremental = false`; `dadaia ci preflight` redirects it automatically)
- [ ] No secrets, absolute machine paths, or consumer-specific data introduced
- [ ] `dadaia public stage && dadaia public install --target all` run if `public/` assets changed

## Related issues / tasks

<!-- Link to the release task or GitHub issue, e.g. Closes #42 -->
