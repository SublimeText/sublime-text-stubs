# sublime-text-stubs

[PEP 561](https://peps.python.org/pep-0561/) typing stubs
for the Sublime Text plugin API,
covering the `sublime` and `sublime_plugin` modules.

Sublime Text exposes these modules only inside its own embedded interpreter,
so they cannot be imported or introspected from a normal Python environment.
Installing this package as a dev dependency
gives type checkers and editors something to resolve them against.

## Installation

```sh
uv add --dev sublime-text-stubs
# or
pip install --upgrade sublime-text-stubs
```

## Versioning

Versions follow the scheme `1.${st_build_version}.${patch}`:

| Version     | Sublime Text build | Embedded Python |
| ----------- | ------------------ | --------------- |
| `1.4200.*`  | 4200 (stable)      | 3.8             |
| `1.4206.*`  | 4206 (dev)         | 3.14            |

The leading `1` is the schema version of this package itself,
the middle segment is the Sublime Text build the stubs describe,
and the trailing segment is the patch level within that build.
This is deliberately not semantic versioning.

Pin the build you target:

```toml
sublime-text-stubs = "==1.4200.*"
```

Sublime Text 4 also still ships a legacy Python 3.3 runtime.
It is scheduled for removal and is not targeted by this package.

## Repository layout

Each supported Sublime Text build line lives on its own branch,
because the build lines target different Python versions
and therefore need different stub syntax and type checker settings:

- `main` -- ST build 4200, Python 3.8, tagged `v1.4200.x`
- (planned) `st-4206` -- ST build 4206, Python 3.14, tagged `v1.4206.x`

Fixes that apply to more than one build line
are cherry-picked between branches,
so keep such commits small and self-contained.

## Development

```sh
uv sync --group dev
uv run pyright
uv run basedpyright
uv run mypy
uv run ty check --error-on-warning
```

Because the real modules cannot be imported,
correctness is validated by strict-checking sample consumer code
under `tests/typing/` with all four checkers.
There is no `stubtest` run,
which means divergence from the actual runtime API
is not caught automatically.

`references/python38/` holds the annotated `sublime.py`, `sublime_plugin.py`
and `sublime_types.py` shipped with Sublime Text build 4200,
kept as the reference the stubs are written against.
It is excluded from all four type checkers.

Configuration notes:

- basedpyright refuses to start
  if a `pyproject.toml` contains both `[tool.pyright]` and `[tool.basedpyright]`,
  so its settings live in `basedpyrightconfig.json`.
- basedpyright's `typeCheckingMode = "all"` is not usable on this branch
  because it enables `reportDeprecated`,
  which flags `typing.List` and `typing.Optional`
  even though the Python 3.8 target requires them.
- mypy 2.x refuses to target anything below Python 3.10,
  so `python_version` is set to `3.10` there.
  pyright, basedpyright and ty still enforce 3.8,
  which is what actually guards against newer syntax entering the stubs.

## License

Not yet chosen. See [LICENSE](LICENSE).
