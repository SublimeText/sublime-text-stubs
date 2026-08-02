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
- `tools/generate_stubs.py`,
  which derives the stubs from `references/`
  and is verified in CI to reproduce the committed files byte for byte.
