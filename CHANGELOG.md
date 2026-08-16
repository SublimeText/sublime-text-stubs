# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow `1.${st_build_version}.${patch}`,
not semantic versioning; see the README.

## [Unreleased]

### Added

- Stub-only `TypedDict`s for the dictionaries the API returns or accepts.
  They have no counterpart at runtime,
  so import them under `if TYPE_CHECKING:`.
  - `UIInfo` for `sublime.ui_info()`,
    including the `color_scheme.palette` colors.
  - `ScopeStyle` for `View.style_for_scope()`,
    with the "(only if set)" keys marked `NotRequired`
    and `source_line`/`source_file` typed as `int`/`str`,
    which is what the runtime returns
    rather than what the upstream docstring claims.
  - `MacroStep` for the entries of `sublime.get_macro()`.
  - `WindowLayout` for `Window.layout()`, `Window.get_layout()` and `Window.set_layout()`.
  - `WindowVariables` for `Window.extract_variables()`, all keys optional.
    `sublime.expand_variables()` now takes `dict[str, str] | WindowVariables`,
    so the round trip its docstring recommends keeps type-checking.
  - `FontOptions` for the default and the callback argument of `choose_font_dialog()`,
    both keys optional.
- `ValueLike` and `CommandArgsLike` in `sublime_types`,
  accepted wherever a plugin passes a value *into* Sublime Text.
  `Value`'s containers, `list[Value]` and `dict[str, Value]`, are invariant,
  so a `List[str]` or `Dict[str, str]` could not be passed where a `Value` was expected;
  `ValueLike` uses the covariant `Sequence` and `Mapping` protocols instead.
  As a consequence it also admits a `Mapping` that is not a `dict`,
  which type-checks but is rejected at runtime,
  and it does not model that whatever is passed in
  comes back as a plain `list` or `dict`.

### Changed

- `ListInputItem` is generic over its `value` type,
  bounded by `ValueLike` and defaulting to `Value`, instead of `Any`.
- `CommandInputHandler` and `ListInputHandler` are generic
  over the value the selected input passes to the command,
  bounded by `ValueLike`,
  and `TextInputHandler` is a `CommandInputHandler[str]`.
  `ListInputHandler`'s parameter defaults to `Value`,
  while `CommandInputHandler`'s is contravariant and defaults to `Never`,
  so bare annotations such as `Optional[CommandInputHandler]`
  keep accepting every kind of handler.
  The runtime classes cannot be subscripted on the Python 3.8 plugin host,
  so parameterize a base class through an `if TYPE_CHECKING:` alias.
- `CommandInputHandler.preview()`, `validate()` and `confirm()` take that value type
  rather than `str`,
  because the host passes them the selected item's value, not its row text.
- `ListInputHandler.list_items()` may return any `Iterable`, not just a `list`,
  and may mix the three item forms within it.
  Note that a bare `tuple` of items type-checks
  but is read at runtime as the `(items, index)` pre-select form.
- Every parameter through which a plugin passes a value into Sublime Text --
  `Settings` mutators, `sublime.encode_value` and `expand_variables`,
  `run_command` and its `format_command`, `html_format_command`
  and `command_url` relatives, `set_project_data`, `begin_edit`
  and `CompletionItem.command_completion` --
  now accepts `ValueLike` or `CommandArgsLike`.
  Return types, and the parameters Sublime Text fills in,
  keep their narrower `Value` or `CommandArgs` types.
- `EventListener.on_query_context()` and `ViewEventListener.on_query_context()`
  type their `operand` parameter as `Value` instead of `str`.
  A `.sublime-keymap` context's `"operand"` may be a JSON string, number or boolean,
  e.g. `"operand": 1` for `num_selections`,
  and the plugin host hands it through unconverted.
- `set_timeout()` and `set_timeout_async()` type their `callback` as
  `Callable[[], object]` instead of `Callable[[], Any]`,
  since the runtime discards whatever the callback returns.
- `sublime.HTML` is annotated as `Literal[1]` rather than left to inference.

### Removed

- The `__repr__` and `__str__` declarations,
  which only restated what `object` already says.

## 1.4200.0b1

Initial version
with stubs generated from upstream files of build 4200
and some overrides.
