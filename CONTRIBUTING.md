# Contributing

Technical decisions are recorded where they take effect --
in inline comments and in commit messages --
not in this file.
When you wonder *why* something is the way it is,
read the comment next to it;
this file only tells you where to look.

## Project structure

| Path                     | Contents |
| ------------------------ | -------- |
| `stubs/`                 | The generated `.pyi` files, one `-stubs` package per module. **Never edited by hand.** |
| `tools/generate_stubs.py`| The generator that derives `stubs/` from `references/`. |
| `tools/stub_overrides.py`| Declarative corrections the generator cannot derive on its own. |
| `references/python38/`   | The annotated `sublime.py`, `sublime_plugin.py` and `sublime_types.py` shipped with the targeted Sublime Text build. |
| `tests/typing/`          | Sample consumer code, type-checked to validate the stubs. |
| `.github/workflows/`     | `ci.yml` for the stubs, `tools.yml` for the generator, `release.yml` for PyPI. |

The reference sources already carry the full signatures
and the reStructuredText docstrings the official docs are built from,
so the stubs are derived from them mechanically
rather than transcribed by hand.

### Branches

Each supported Sublime Text build line lives on its own branch,
because the build lines target different Python versions
and therefore need different stub syntax and type checker settings:

- `main` -- ST build 4200, Python 3.8, tagged `v1.4200.x`
- (planned) `st-4206` -- ST build 4206, Python 3.14, tagged `v1.4206.x`

Fixes that apply to more than one build line
are cherry-picked between branches,
so keep such commits small and self-contained.

## Generating the stubs

```sh
uv run python tools/generate_stubs.py            # rewrite the .pyi files
uv run python tools/generate_stubs.py --check    # what CI runs; fails on drift
```

The generator refuses to guess.
Anything it cannot derive -- an unannotated parameter,
a bare `dict` that strict mode rejects --
is reported with the exact `stub_overrides` key to add,
and nothing is written until every one is resolved.

The check runs in the other direction too:
every override table is keyed by a name from the reference,
and an entry that matches nothing there is reported as stale.
Corrections therefore cannot quietly stop applying
when a member is renamed or removed in a later build.

## Adjusting the stubs

Corrections belong in `tools/stub_overrides.py`
if they concern a single member,
and in `tools/generate_stubs.py`
if they concern how the stubs are shaped as a whole.
The override tables are keyed by dotted names rooted at the module:
`sublime.Settings.to_dict` for a method,
`sublime.CompletionItem.__init__.kind` for a single parameter.
Each table's docstring says what it corrects;
add the entry, rerun the generator, commit the regenerated `.pyi` alongside it.

Record the reasoning for a non-obvious entry as a comment next to it,
with a `references/python38/<file>:<line>` pointer
to the reference code that justifies it.

## Validating

```sh
uv sync --group dev
uv run pyright
uv run basedpyright
uv run mypy
uv run ty check --error-on-warning
```

Because the real modules cannot be imported,
correctness is validated by strict-checking the sample consumer code
under `tests/typing/` with all four checkers.
There is no `stubtest` run,
which means divergence from the actual runtime API
is not caught automatically.
Extend `tests/typing/` when you touch an API that nothing there exercises.

Checker settings, and why each is what it is,
are documented in `pyproject.toml`.

## The `tools/` sub-project

`tools/` is a separate, standalone uv project
with its own `pyproject.toml`, lockfile and virtualenv,
excluded from the four root checkers:

```sh
uv run --directory tools basedpyright     # or: cd tools && uv run basedpyright
uv run --directory tools ruff check
```

basedpyright is the only type checker there,
with every rule at `error`;
ruff lints the same directory.
Both have their own [`Tools`](.github/workflows/tools.yml) workflow.
See `tools/pyproject.toml` for the settings and the reasons behind them.

The stubs and the sample consumer code are not linted with ruff:
`.pyi` files and code written to exercise a type checker
follow conventions of their own.

## Onboarding a new Sublime Text build

1. Copy the build's `sublime.py`, `sublime_plugin.py` and `sublime_types.py`
   into `references/python<version>/`.
2. Point `REFERENCE_DIR` and `ST_BUILD` in `tools/generate_stubs.py` at it.
3. Run the generator and resolve everything it reports as unresolved,
   including any override it reports as stale.
4. Run the four type checkers and commit the regenerated `.pyi` files.

## Releasing

Tag `v1.${st_build_version}.${patch}` on the branch for that build line.
hatch-vcs derives the distribution version from the tag,
and the `Release` workflow publishes to PyPI via trusted publishing.
Add the changes to `CHANGELOG.md` before tagging.
