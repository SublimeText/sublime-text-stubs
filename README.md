# sublime-text-stubs

[PEP 561](https://peps.python.org/pep-0561/) typing stubs
for the Sublime Text plugin API,
covering the `sublime`, `sublime_plugin` and `sublime_types` modules.

The stubs carry the API documentation as docstrings,
so hovering a symbol in an editor shows the same prose
as the [official API reference](https://www.sublimetext.com/docs/api_reference.html).

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

## Regenerating the stubs

**The `.pyi` files under `stubs/` are generated. Do not edit them.**
Corrections belong in `tools/generate_stubs.py`
or in the declarative override tables in `tools/stub_overrides.py`.

```sh
uv run python tools/generate_stubs.py            # rewrite the .pyi files
uv run python tools/generate_stubs.py --check    # what CI runs; fails on drift
```

The generator reads `references/python38/`,
which holds the annotated `sublime.py`, `sublime_plugin.py` and `sublime_types.py`
shipped with Sublime Text build 4200.
Those sources already carry the full signatures
and the reStructuredText docstrings the official docs are built from,
so the stubs are derived from them mechanically.
The generator runs on the current Python,
not on the Sublime Text one,
so `tools/` is its own project with its own checker configuration.
See [Development](#development).

The generator refuses to guess.
Anything it cannot derive -- an unannotated parameter,
a bare `dict` that strict mode rejects, an unused override entry --
is reported with the exact `stub_overrides` key to add,
and nothing is written until every one is resolved.

`mypy stubgen --include-docstrings` is not used
because it drops attribute docstrings
(every enum member and every documented `self.x`),
it cannot know about the docstring-only event handlers described below,
and it has nowhere to record the strict-mode type corrections.

### Onboarding a new Sublime Text build

1. Copy the build's `sublime.py`, `sublime_plugin.py` and `sublime_types.py`
   into `references/python<version>/`.
2. Point `REFERENCE_DIR` and `ST_BUILD` in `tools/generate_stubs.py` at it.
3. Run the generator and resolve everything it reports as unresolved.
4. Run the four type checkers and commit the regenerated `.pyi` files.

### What the generator has to work around

- **Docstring-only event handlers.**
  `EventListener`, `ViewEventListener` and `TextChangeListener`
  declare no handler methods at all;
  Sublime Text dispatches to them dynamically,
  and each handler exists only as a `.. method::` directive in the class docstring.
  The generator parses those directives into real declarations,
  taking the return type from `EVENT_HANDLER_RETURNS`
  because the directives either omit it
  or spell it in prose-flavoured pseudo-Python (`-> (str, CommandArgs)`).
- **`run` is not declared** on any of the command classes.
  Sublime Text invokes it with command-specific keyword arguments,
  so a base signature would reject every subclass that declares arguments of its own.
  `is_enabled`, `is_visible`, `is_checked` and `description` receive their arguments
  the very same way,
  but they do have a default implementation,
  so they are emitted exactly as the reference declares them: without parameters.
  Adding `**kwargs` to them, as sublimelsp/LSP's stub does,
  would contradict the reference
  and would not buy anything,
  because an override narrowing to named parameters
  stays an incompatible override under Liskov rules
  and both pyright and mypy report it either way.
- **Internal members are dropped**:
  anything underscore-prefixed,
  the trailing-underscore methods the plugin host calls into (`run_`, `is_enabled_`),
  and, in `sublime_plugin`, everything outside the documented public API
  (registries, host callbacks, the `.sublime-package` importer).
- **Implicit optionals are made explicit**:
  the reference writes `on_navigate: Callable[[str], None] = None` in places.
  This applies to parameters only;
  see the deliberate divergence below for why attributes are exempt.
- **Deprecations live in the prose**:
  a superseded member is only marked by a `:deprecated:` field in its docstring,
  so the generator parses that field,
  strips the reStructuredText markup from it
  and emits `@typing_extensions.deprecated` with the remaining message.
- **Shadowed builtins are qualified**:
  `TextChange.str` shadows `str` for the rest of that class body,
  so annotations there are emitted as `builtins.str`.

### Deliberate divergences from other stub sets

- **`TextChangeListener.buffer` is `sublime.Buffer`, not `Buffer | None`.**
  The reference writes `self.buffer: sublime.Buffer = None`,
  and both hand-written third-party stub sets
  (sublimelsp/LSP and SublimeText/sublime_lib)
  declare the attribute optional,
  which is literally what it holds between `__init__` and `attach()`.
  That window is not observable from a listener, though:
  the plugin host instantiates and attaches in a single expression,
  `cls().attach(buf)`,
  in both `attach_buffer` and `check_text_change_listeners`,
  so by the time any handler runs the attribute is a real `Buffer`.
  Declaring it optional would force a narrowing check in every handler
  for a state users never see.
  The exception to be aware of is `detach()`,
  which leaves the attribute pointing at the buffer it was last attached to.

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

`references/` is excluded from all four type checkers.

### The `tools/` sub-project

`tools/` is a separate, standalone uv project
with its own `pyproject.toml`, lockfile and virtualenv.
The stubs target the Python version embedded in Sublime Text,
while the generator runs on the current one;
a single project cannot express both targets,
which is why the split exists rather than `tools/` simply going unchecked.

```sh
uv run --directory tools basedpyright     # or: cd tools && uv run basedpyright
```

basedpyright is the only checker there,
at `typeCheckingMode = "all"` -- every rule at `error`, nothing relaxed.
It is not part of the `CI` workflow;
it has its own [`Tools`](.github/workflows/tools.yml) workflow.

`tools/` is excluded from all four root checkers,
so running them from the repo root never reaches it.

Configuration notes:

- basedpyright's `typeCheckingMode = "all"` is not usable for the stubs
  because it enables `reportDeprecated`,
  which flags `typing.List` and `typing.Optional`
  even though the Python 3.8 target requires them.
  The `tools/` sub-project has no such constraint.
- pyright and basedpyright share the single `[tool.pyright]` section.
  A second `[tool.basedpyright]` section is not an option:
  basedpyright rejects a `pyproject.toml` carrying both
  (`Config file could not be parsed`)
  and then silently falls back to its defaults.
  basedpyright does honour its own extra rules from `[tool.pyright]`,
  so the two settings plain pyright does not know
  -- `reportPrivateLocalImportUsage` and `reportImplicitRelativeImport` --
  live there too.
  pyright logs `Config contains unrecognized setting` for them and carries on.
  There is no `basedpyrightconfig.json`;
  basedpyright never reads such a file,
  so settings placed in one are silently ignored.
  `tools/` can use `[tool.basedpyright]`
  only because its `pyproject.toml` has no `[tool.pyright]` section.
- mypy 2.x refuses to target anything below Python 3.10,
  so `python_version` is set to `3.10` there.
  pyright, basedpyright and ty still enforce 3.8,
  which is what actually guards against newer syntax entering the stubs.

## License

Not yet chosen. See [LICENSE](LICENSE).
