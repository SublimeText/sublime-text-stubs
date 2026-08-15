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
- **`ValueLike` is the covariant companion to `Value`.**
  `Value` describes what Sublime Text hands back,
  and its containers, `list[Value]` and `dict[str, Value]`,
  are invariant,
  so a `List[str]` variable cannot be passed anywhere a `Value` is expected.
  `ValueLike` describes what Sublime Text accepts on the way in instead,
  using the covariant `Sequence` and `Mapping` protocols,
  so the same variable can be passed directly:

  ```python
  tags: List[str] = ["fix", "feature"]
  settings.set("tags", tags)
  sublime.encode_value(tags)
  ```

  Two things it does not model.
  A `collections.abc.Mapping` that is not a `dict` type-checks as `ValueLike`,
  but is rejected at runtime everywhere except `Settings.update`,
  which genuinely accepts any mapping.
  And a value that makes the round trip through Sublime Text
  comes back as a plain `list` or `dict`,
  not as the type that was passed:
  a handler parameterized on a custom sequence type
  is handed a plain `list` in `description()`, `preview()`,
  `validate()` and `confirm()`,
  and `bytes` in particular is accepted and arrives back as `list[int]`.

  `sublime.Region` is rejected by both the checkers and the runtime.
- **The input handlers are generic.**
  `ListInputHandler` and `sublime.ListInputItem` take a type parameter
  for the value the selected row passes to the command,
  bounded by `ValueLike` and defaulting to `Value`,
  and that value type is what `list_items()`, `description()`,
  `preview()`, `validate()` and `confirm()` traffic in.
  The bound is what you may parameterize on,
  so `ListInputHandler[List[str]]` type-checks,
  while the default is what a bare, unparameterized annotation resolves to,
  and it stays `Value` because that is what the runtime actually delivers.
  `TextInputHandler` is a `CommandInputHandler[str]`.
  A bare `CommandInputHandler` annotation,
  as in the return types of `Command.input()` and `next_input()`,
  accepts every kind of handler,
  because the class is contravariant in its value type
  and defaults to `Never`,
  so nothing has to change
  for authors who keep writing `Optional[sublime_plugin.CommandInputHandler]`.
  The real classes cannot be subscripted on the Python 3.8 plugin host,
  so parameterize a base class through an `if TYPE_CHECKING:` alias
  and quote subscripted annotations:

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
