# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow `1.${st_build_version}.${patch}`,
not semantic versioning; see the README.

## [Unreleased]

### Changed

- `EventListener.on_query_context()` and `ViewEventListener.on_query_context()` type
  their `operand` parameter as `Value` instead of `str`.
  A `.sublime-keymap` context's `"operand"` may be a JSON string, number, or boolean,
  e.g. `"operand": 1` for `num_selections` or `"operand": true` for a boolean setting,
  and the plugin host hands it through unconverted.
- `set_timeout()` and `set_timeout_async()` type their `callback` as
  `Callable[[], object]` instead of `Callable[[], Any]`.
  The runtime discards whatever the callback returns,
  so `object` describes that without resorting to `Any`.
  With no remaining `Any` in the stubs,
  `reportAny` and `reportExplicitAny` (basedpyright only) are now enabled.

### Added

- `sublime.ui_info()` returns `UIInfo`,
  a stub-only `TypedDict` describing its `system`, `theme` and `color_scheme` keys,
  including the `color_scheme.palette` colors.
  These types have no counterpart at runtime,
  so import them under `if TYPE_CHECKING:`.
- `View.style_for_scope()` returns `ScopeStyle`,
  a stub-only `TypedDict` naming every key its docstring documents,
  with the "(only if set)" ones marked `NotRequired`.
  Its `source_line` is `int` and its `source_file` is `str`,
  which is what the runtime returns
  rather than what the upstream docstring claims.
- `sublime.get_macro()` returns `list[MacroStep]`,
  a stub-only `TypedDict` with the `command` and `args` keys
  its docstring says every entry always carries.
- `Window.layout()` and `Window.get_layout()` return `WindowLayout`,
  and `Window.set_layout()` accepts one,
  a stub-only `TypedDict` with the `cols`, `rows` and `cells` keys
  a live call was observed to always carry.
- `Window.extract_variables()` returns `WindowVariables`,
  a stub-only `TypedDict` with the keys its docstring says the result may contain,
  all of them optional.
  `sublime.expand_variables()` now takes `dict[str, str] | WindowVariables`,
  so the round trip its docstring recommends keeps type-checking.
- `choose_font_dialog()` takes a `FontOptions` default
  and calls its callback with `FontOptions | None`,
  a stub-only `TypedDict` with the `font_face` and `font_size` keys
  a live call was observed to pass, both optional.
- `ValueLike` and `CommandArgsLike`,
  stub-only `sublime_types` aliases accepted wherever a plugin
  passes a value into Sublime Text.
  `Value`'s containers, `list[Value]` and `dict[str, Value]`, are invariant,
  so a `List[str]` or `Dict[str, str]` could not be passed
  anywhere a `Value` was expected.
  `ValueLike` uses the covariant `Sequence` and `Mapping` protocols instead,
  so it admits a `collections.abc.Mapping` that is not a `dict`,
  which type-checks but is rejected at runtime,
  and it does not model that whatever is passed in
  comes back as a plain `list` or `dict`.

### Changed

- `ListInputItem` is generic over its `value` type,
  bounded by `ValueLike` and defaulting to `Value`,
  rather than typing the value as `Any`.
- `CommandInputHandler` and `ListInputHandler` are generic
  over the value the selected input passes to the command,
  bounded by `ValueLike`,
  and `TextInputHandler` is a `CommandInputHandler[str]`.
  `ListInputHandler`'s parameter defaults to `Value`,
  while `CommandInputHandler`'s is contravariant and defaults to `Never`,
  which is what keeps bare annotations
  such as `Optional[CommandInputHandler]` accepting every kind of handler.
  The runtime classes cannot be subscripted on the Python 3.8 plugin host,
  so parameterize a base class through an `if TYPE_CHECKING:` alias.
- `CommandInputHandler.preview()`, `validate()` and `confirm()`
  take that value type rather than `str`,
  because the host passes them the selected item's value, not its row text.
- `ListInputHandler.list_items()` may return any `Iterable`, not just a `list`,
  and may mix the three item forms within one iterable.
  Note that a bare `tuple` of items type-checks
  but is read at runtime as the `(items, index)` pre-select form.
- Every parameter through which a plugin passes a value *into* Sublime Text --
  `Settings` mutators, `sublime.encode_value` and `expand_variables`,
  `run_command` and its `format_command`, `html_format_command`
  and `command_url` relatives, `set_project_data`, `begin_edit`
  and `CompletionItem.command_completion` --
  now accepts `ValueLike` or `CommandArgsLike`
  instead of `Value` or `CommandArgs`,
  so a `List[str]` or `Dict[str, str]` can be passed directly.
  Return types, and the parameters Sublime Text fills in,
  keep their narrower `Value` or `CommandArgs` types.
- `sublime.HTML` is annotated as `Literal[1]` rather than left to inference.
- Signatures longer than 100 characters are wrapped one parameter per line.
- Annotations no longer carry the quotes the reference needs at runtime,
  so `CompletionItem.snippet_completion` returns `CompletionItem`, not `'CompletionItem'`.

### Removed

- The `__repr__` and `__str__` declarations,
  which only restated what `object` already says.

## 1.4200.0b1

Initial version
with stubs generated from upstream files of build 4200
and some overrides.
