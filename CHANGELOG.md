# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow `1.${st_build_version}.${patch}`,
not semantic versioning; see the README.

## [Unreleased]

### Changed

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
