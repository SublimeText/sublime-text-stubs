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
| `references/python314/`  | The annotated `sublime.py`, `sublime_plugin.py` and `sublime_types.py` shipped with the targeted Sublime Text build. |
| `tests/typing/`          | Sample consumer code, type-checked to validate the stubs. |
| `.github/workflows/`     | `ci.yml` for the stubs, `tools.yml` for the generator, `release.yml` for PyPI, `update-reference.yml` for new Sublime Text builds. |

The reference sources already carry the full signatures
and the reStructuredText docstrings the official docs are built from,
so the stubs are derived from them mechanically
rather than transcribed by hand.

### Branches

`main` targets ST build 4213 with Python 3.14
and is tagged `v4213.x`.
Build 4200 continues on the `st-4200` branch
and is tagged `v4200.x`.
Build lines live on separate branches
because they target different Python versions
and therefore need different stub syntax and type checker settings.

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
almost every override table is keyed by a name from the reference,
and an entry that matches nothing there is reported as stale.
Corrections therefore cannot quietly stop applying
when a member is renamed or removed in a later build.
The two exceptions are covered in "Adjusting the stubs" below.

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
with a `references/python314/<file>:<line>` pointer
to the reference code that justifies it.
If the correction changes what plugin authors have to write or can expect,
add the consequence -- not the reasoning -- to the notes in `README.md`.

The two exceptions to the staleness check are `EXTRA_TYPE_ALIASES`
and `EXTRA_TYPE_ALIAS_CLASSES`:
they add `sublime_types` names, such as `ValueLike`,
that have no reference-side counterpart at all,
so nothing validates them beyond the type checkers.
A name added to either table must also be added to `SUBLIME_TYPES_REEXPORTS`
for every module that re-exports it.

## Validating

```sh
uv sync --group dev
uv run pyright
uv run basedpyright
uv run mypy
uv run ty check --error-on-warning
uv run ruff check
```

Because the real modules cannot be imported,
correctness is validated by strict-checking the sample consumer code
under `tests/typing/` with all four checkers.
There is no `stubtest` run,
which means divergence from the actual runtime API
is not caught automatically.
Extend `tests/typing/` when you touch an API that nothing there exercises.

ruff covers what the checkers cannot see:
its `flake8-pyi` rules judge whether a `.pyi` is *written* the way a stub should be,
which is a question about form rather than about meaning.
A finding under `stubs/` is therefore a bug in the generator.
Fix it in `tools/generate_stubs.py` and regenerate;
never edit a `.pyi` to silence ruff,
and never reach for `--fix` there.

Checker and lint settings, and why each is what it is,
are documented in `pyproject.toml`.

The checker versions are pinned in `uv.lock` and `tools/uv.lock`,
and CI installs exactly those.
Dependabot proposes upgrades once a month;
to upgrade by hand, run `uv lock --upgrade` in the root and in `tools/`,
then rerun all checks.

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
ruff lints the same directory
under its own rule set and its own Python target,
which is why the root ruff run excludes `tools/`.
Both have their own [`Tools`](.github/workflows/tools.yml) workflow.
See `tools/pyproject.toml` for the settings and the reasons behind them.

## Onboarding a new Sublime Text build

A weekly [`Update reference`](.github/workflows/update-reference.yml) workflow
checks for a build newer than `ST_BUILD`
and opens a pull request from a branch `update/st-build-<build>`
with step 2 done and step 3 attempted,
so the onboarding continues from that pull request.
A build that ships a different Python version makes the run fail
until step 1 is done on `main`;
the next run then picks the build up.

1. Only if the build ships a different Python version:
   `git mv` the reference directory to its new name,
   so that the history follows the files,
   and point `REFERENCE_DIR` in `tools/generate_stubs.py` at it.
   The extraction script refuses such a build until then.
2. Run the extraction script as described in `references/README.md`;
   it extracts the build's sources and sets `ST_BUILD`.
3. Run the generator and resolve everything it reports as unresolved,
   including any override it reports as stale.
4. Repoint the `references/...:<line>` citations
   in `tools/` and `pyproject.toml` to the new sources.
5. Audit the overrides:
   keep, reword or remove each one
   depending on whether the new reference makes it redundant.
6. Run all checks listed in `AGENTS.md`
   and commit the regenerated `.pyi` files.

## Releasing

Tag `v${st_build_version}.${patch}` on the branch for that build line.
hatch-vcs derives the distribution version from the tag,
and the `Release` workflow publishes to PyPI via trusted publishing.
Before tagging,
move the changes in `CHANGELOG.md` from `[Unreleased]`
under a `## <version> (<YYYY-MM-DD>)` heading
dated with the release day.
Releases are ordered by date, newest first,
regardless of their build line.
Pre-releases get no section of their own,
so their changes stay under `[Unreleased]`
until the final release.

`main` holds the changelog of every build line.
After releasing from another branch,
add its release section to the changelog on `main`
at the position of its date
and remove the released entries from `[Unreleased]` there.
