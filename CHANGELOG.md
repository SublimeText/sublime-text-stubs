# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow `1.${st_build_version}.${patch}`,
not semantic versioning; see the README.

## [Unreleased]

### Added

- Initial project skeleton
  with placeholder stubs for `sublime` and `sublime_plugin`
  targeting Sublime Text build 4200 (Python 3.8).
- Full coverage of `sublime` and `sublime_plugin`,
  generated from the reference sources shipped with build 4200,
  including the API documentation as docstrings
  on classes, functions, enum members and attributes.
- Stubs for the `sublime_types` module,
  whose aliases are re-exported from `sublime` and `sublime_plugin`.
- `sublime_types.Value` is defined recursively,
  so the elements of a list or dict `Value` are `Value`s themselves
  instead of `Any`.
- The `buffer` parameter of `EventListener.on_associate_buffer`
  and `on_associate_buffer_async` is typed as `sublime.Buffer`,
  which is what the plugin host passes,
  and not as `sublime.View` as the reference documentation claims.
- The `details` parameter of `QuickPanelItem` and `ListInputItem`
  accepts a list or tuple of strings besides a plain string,
  matching the `details` attribute of those classes
  and what the runtime actually handles.
- Members whose reference docstring carries a `:deprecated:` marker
  are decorated with `typing_extensions.deprecated`,
  carrying the marker's prose as the message,
  so checkers and editors flag their use
  and point at the replacement.
- `tools/generate_stubs.py`,
  which derives the stubs from `references/`
  and is verified in CI to reproduce the committed files byte for byte.

### Changed

- The stubs are written in modern typing syntax:
  PEP 604 unions (`str | None`)
  and PEP 585 builtin generics (`list[str]`, `dict[str, Value]`)
  instead of `typing.Optional`, `typing.Union`, `typing.List` and friends,
  with `Callable`, `Iterable` and `Iterator` taken from `collections.abc`.
  Stub files are never executed,
  so this is independent of the Python 3.8 runtime they describe;
  no type changed meaning.
  Each file now also opens with `from __future__ import annotations`.
- pyright and basedpyright run every rule
  basedpyright's `typeCheckingMode = "all"` enables,
  spelled out individually
  because plain pyright does not accept that mode name.
  Only `reportAny` and `reportExplicitAny` remain off,
  the API genuinely traffics in `Any`;
  `reportDeprecated`, previously disabled for the sake of the `typing` aliases, is on.
