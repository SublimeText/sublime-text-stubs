# AGENTS.md

PEP 561 typing stubs for the Sublime Text plugin API
(`sublime`, `sublime_plugin`, `sublime_types`).

## Layout

- `stubs/` -- **generated** `.pyi` files. Never edit them; edit the generator instead.
- `tools/generate_stubs.py` -- derives `stubs/` from `references/`.
- `tools/stub_overrides.py` -- declarative per-member corrections.
- `references/python38/` -- the reference sources shipped with ST build 4200; read-only input.
- `tests/typing/` -- sample consumer code, the only validation of the stubs.
- `tools/` is a **separate uv project** with its own lockfile, virtualenv and Python target,
  excluded from the root type checkers.

## Commands

```sh
uv run python tools/generate_stubs.py            # rewrite the .pyi files
uv run python tools/generate_stubs.py --check    # fails on drift; run after every change

uv run pyright
uv run basedpyright
uv run mypy
uv run ty check --error-on-warning
uv run ruff check

uv run --directory tools basedpyright
uv run --directory tools ruff check
```

Run all of these before considering a change complete.
The four root checkers and both ruff runs must stay silent;
the generator must report no unresolved and no stale entries.
A ruff finding under `stubs/` is fixed in the generator, never in the `.pyi`.

## Where things are documented

- `README.md` -- for users of the stubs: installation, versioning, API quirks they will meet.
- `CONTRIBUTING.md` -- for contributors: structure, generating, validating, adjusting overrides,
  onboarding a new ST build, releasing.
- `CHANGELOG.md` -- user-visible changes, grouped under `[Unreleased]` until a tag.
- Technical decisions live in **inline comments** next to the code they govern
  (`pyproject.toml` for checker settings, `tools/*.py` for generator behaviour)
  and in **commit messages**. Keep them there; do not restate them in the Markdown files.

## Conventions

- Justify a non-obvious override with a comment citing `references/python38/<file>:<line>`.
- Commit the regenerated `.pyi` files together with the generator change that produced them.
- Keep commits small and self-contained: fixes are cherry-picked between build-line branches.
