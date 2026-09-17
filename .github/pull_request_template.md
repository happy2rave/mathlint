## What this changes

<!-- One or two sentences. -->

## Checklist

- [ ] A test covers the input that motivated this change
- [ ] `uv run pytest` passes
- [ ] `uv run ruff check .` is clean
- [ ] Parser changes never guess: unreadable input raises `ParseError` with a
      message naming what was not understood
- [ ] `CHANGELOG.md` has an entry under "Unreleased"
