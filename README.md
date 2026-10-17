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

The package requires Python 3.13 or newer to install,
and your type checker has to target Python 3.13 or newer.
Python 3.14 matches the plugin host.

## Versioning

Versions follow the scheme `1.${st_build_version}.${patch}`:

| Version     | Sublime Text build | Embedded Python |
| ----------- | ------------------ | --------------- |
| `1.4213.*`  | 4213 (stable)      | 3.14            |
| `1.4200.*`  | 4200 (stable)      | 3.8             |

The leading `1` is the schema version of this package itself,
the middle segment is the Sublime Text build the stubs describe,
and the trailing segment is the patch level within that build.
This is deliberately not semantic versioning.

Pin the build you target:

```toml
sublime-text-stubs = "==1.4213.*"
```

Sublime Text also ships a disabled, deprecated Python 3.3 plugin host.
This package does not target it.

## Notes for plugin authors

- **Commands do not declare `run`.**
  Sublime Text invokes it with command-specific keyword arguments,
  so the stubs leave the signature to your subclass.
  Write `def run(self, **kwargs)`,
  or `def run(self, edit, **kwargs)` for a `TextCommand`.
- **`is_enabled`, `is_visible`, `is_checked` and `description`**
  receive their command arguments the same dynamic way,
  but are declared without parameters.
  `def is_enabled(self)`, `def is_enabled(self, my_arg="")`
  and `def is_enabled(self, **kwargs)` all type-check.
  A *required* parameter is rejected,
  and correctly so:
  such an override also raises `TypeError` at runtime
  when the command is invoked without that argument.
- **`TextChangeListener.buffer` is `sublime.Buffer`, never `None`.**
- **`ValueLike` is what you pass in, `Value` is what you get back.**
  Parameters a plugin hands a value to are annotated `ValueLike`,
  which accepts arbitrary sequences and mappings,
  except where a specific shape is required:
  `Window.set_project_data()` takes a mapping,
  and `Settings.update()` takes a mapping or an iterable of key/value pairs.
  A `list[str]` variable can be passed directly
  even though the invariant `list[Value]` would reject it:

  ```python
  tags: list[str] = ["fix", "feature"]
  settings.set("tags", tags)
  sublime.encode_value(tags)
  ```

  Two things it does not model.
  A `collections.abc.Mapping` that is not a `dict` type-checks as `ValueLike`,
  but is rejected at runtime everywhere except `Settings.update`,
  which genuinely accepts any mapping.
  And a value that makes the round trip through Sublime Text
  comes back as a plain `list` or `dict`,
  not as the type that was passed;
  `bytes` in particular is accepted and arrives back as `list[int]`.

  `sublime.Region` is rejected by both the checkers and the runtime.

  A `TypedDict` is only a `ValueLike` when it is declared with `closed=True`
  ([PEP 728](https://peps.python.org/pep-0728/)),
  because an open one may carry further keys of any type.
  This applies to the type parameter of the input handlers as well.
  `typing.TypedDict` accepts `closed` only from Python 3.15 on,
  so import `TypedDict` from `typing_extensions` instead.
  Define the class inside the `if TYPE_CHECKING:` block
  unless `typing_extensions` is available at runtime;
  its values are plain `dict` literals either way:

  ```python
  if TYPE_CHECKING:
      from typing_extensions import TypedDict

      class Entry(TypedDict, closed=True):
          name: str
          tags: list[str]


  def store_entry(settings: sublime.Settings, entry: Entry) -> None:
      settings.set("entry", entry)
  ```

  pyright, basedpyright and ty accept this.
  mypy, as of version 2.4.0, does not implement PEP 728
  and rejects every `TypedDict` as a `ValueLike`.
- **The input handlers are generic.**
  `ListInputHandler` and `sublime.ListInputItem` take a type parameter
  for the value the selected row passes to the command,
  and that value type is what `list_items()`, `description()`,
  `preview()`, `validate()` and `confirm()` traffic in.
  You may parameterize on anything a `ValueLike` allows,
  so `ListInputHandler[list[str]]` type-checks,
  while a bare annotation resolves to `Value`,
  which is what the runtime actually delivers.
  `TextInputHandler` is a `CommandInputHandler[str]`.
  A bare `CommandInputHandler`,
  as in the return types of `Command.input()` and `next_input()`,
  still accepts every kind of handler,
  so `sublime_plugin.CommandInputHandler | None` keeps working unchanged.
  The real classes cannot be subscripted at runtime,
  so parameterize a base class through an `if TYPE_CHECKING:` alias:

  ```python
  if TYPE_CHECKING:
      _StrListInputHandler = sublime_plugin.ListInputHandler[str]
  else:
      _StrListInputHandler = sublime_plugin.ListInputHandler


  class NameInputHandler(_StrListInputHandler):
      ...
  ```

- **Several `sublime_types` names exist only in these stubs**,
  not in the real module at runtime,
  so each must be imported inside an `if TYPE_CHECKING:` block:
  - `ModifierKeys`, the type of the `modifier_keys` entry of an `Event`.
  - `UIInfo` and its parts `UIInfoSystem`, `UIInfoTheme`,
    `UIInfoColorScheme` and `UIInfoPalette`,
    describing the return value of `sublime.ui_info()`.
  - `ScopeStyle`, the return value of `View.style_for_scope()`.
  - `MacroStep`, the entries of the list `sublime.get_macro()` returns.
  - `WindowLayout`, used by `Window.layout()`, `Window.get_layout()`
    and `Window.set_layout()`.
  - `WindowVariables`, the return value of `Window.extract_variables()`.
  - `FontOptions`, the default and callback argument types
    of `choose_font_dialog()`.
  - `ValueLike`, the covariant companion to `Value`,
    accepted wherever a plugin passes a value into Sublime Text.
  - `CommandArgsLike`, the same widening applied to command `args`,
    mirroring `CommandArgs`.

The stubs are not validated against the running editor,
so divergences from the actual runtime API are possible.
Please [report](https://github.com/SublimeText/sublime-text-stubs/issues) any you find.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)
for the project structure,
how the stubs are generated and validated,
and how to correct them.

## License

MIT. See [LICENSE](LICENSE).
The stubs are derived from the API sources shipped with Sublime Text,
(c) Sublime HQ Pty Ltd,
and used with permission under the same license.
