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

## Notes for plugin authors

- **Commands do not declare `run`.**
  Sublime Text invokes it with command-specific keyword arguments,
  so the stubs leave the signature to your subclass.
  Write `def run(self, **kwargs)`,
  or `def run(self, edit, **kwargs)` for a `TextCommand`.
- **`is_enabled`, `is_visible`, `is_checked` and `description`**
  receive their command arguments the same dynamic way,
  but they are declared without parameters,
  exactly as Sublime Text declares them.
  `def is_enabled(self)`, `def is_enabled(self, my_arg="")`
  and `def is_enabled(self, **kwargs)` all type-check.
  A *required* parameter is rejected,
  and that rejection is correct:
  such an override also raises `TypeError` at runtime
  when the command is invoked without that argument.
- **`TextChangeListener.buffer` is `sublime.Buffer`, not `Buffer | None`.**
  The plugin host attaches the listener immediately after constructing it,
  so no handler can observe the unattached state.
- **`sublime_types.ModifierKeys`** exists only in these stubs,
  as the type of the `modifier_keys` entry of an `Event`.
  Import it inside an `if TYPE_CHECKING:` block,
  since the real module has no such name at runtime.

The stubs are validated by type-checking sample consumer code,
not against the running editor,
so divergences from the actual runtime API are possible.
Please [report](https://github.com/SublimeText/sublime-text-stubs/issues) any you find.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
for the project structure,
how the stubs are generated and validated,
and how to correct them.

## License

Not yet chosen. See [LICENSE](LICENSE).
