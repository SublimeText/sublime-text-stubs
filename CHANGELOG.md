# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow `1.${st_build_version}.${patch}`,
not semantic versioning; see the README.

## [Unreleased]

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

### Changed

- `ListInputItem` is generic over its `value` type,
  bounded by and defaulting to `Value`,
  rather than typing the value as `Any`.
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
