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
- `tools/generate_stubs.py`,
  which derives the stubs from `references/`
  and is verified in CI to reproduce the committed files byte for byte.
