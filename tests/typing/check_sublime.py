"""Sample consumer code exercising the `sublime` stubs.

Not executed. Its only purpose is to give the type checkers something concrete to
verify the stubs against, since `sublime` cannot be imported outside Sublime Text.
"""

from typing import List, Optional, Tuple

import sublime
from sublime_types import Value as ValueFromTypesModule


def collect_word_regions(view: sublime.View) -> List[sublime.Region]:
    regions: List[sublime.Region] = []
    for region in view.sel():
        regions.append(view.word(region))
    return regions


def describe_cursor(view: sublime.View) -> str:
    point: sublime.Point = view.sel()[0].begin()
    row, col = view.rowcol(point)
    return "{}:{}".format(row + 1, col + 1)


def current_file_name() -> Optional[str]:
    view: Optional[sublime.View] = sublime.active_window().active_view()
    if view is None:
        return None
    return view.file_name()


def highlight(view: sublime.View, regions: List[sublime.Region]) -> None:
    view.add_regions(
        "sublime-text-stubs-demo",
        regions,
        scope="region.bluish",
        flags=sublime.RegionFlags.DRAW_NO_FILL | sublime.RegionFlags.PERSISTENT,
    )


def read_setting(name: str) -> sublime.Value:
    return sublime.load_settings("Preferences.sublime-settings").get(name, None)


def read_setting_via_types_module(name: str) -> ValueFromTypesModule:
    # The aliases are importable from `sublime_types` as well as re-exported from
    # `sublime`, mirroring the modules Sublime Text ships.
    return sublime.load_settings("Preferences.sublime-settings")[name]


def project_folder_names(window: sublime.Window) -> List[str]:
    # `Value` is recursive, so the elements of a list or dict `Value` are `Value`s
    # themselves and narrow via `isinstance` instead of arriving as `Any`.
    data = window.project_data()
    if not isinstance(data, dict):
        return []
    folders = data.get("folders")
    if not isinstance(folders, list):
        return []
    names: List[str] = []
    for folder in folders:
        if isinstance(folder, dict):
            name = folder.get("name")
            if isinstance(name, str):
                names.append(name)
    return names


def open_transient(window: sublime.Window, path: str) -> sublime.View:
    return window.open_file(path, sublime.NewFileFlags.TRANSIENT)


def region_arithmetic() -> int:
    a = sublime.Region(0, 10)
    b = sublime.Region(5, 20)
    return a.cover(b).size() - a.intersection(b).size()


def deprecated_aliases_still_resolve() -> sublime.RegionFlags:
    # The module level constants predating the enums are part of the API.
    return sublime.DRAW_NO_FILL | sublime.PERSISTENT


def completions() -> sublime.CompletionList:
    items: List[sublime.CompletionValue] = [
        sublime.CompletionItem(
            "hello",
            annotation="greeting",
            completion="hello, world",
            completion_format=sublime.CompletionFormat.TEXT,
            kind=sublime.KIND_SNIPPET,
            details="Inserts a greeting",
        ),
        sublime.CompletionItem.snippet_completion("loop", "for ${1:x} in ${2:xs}:\n\t$0"),
        sublime.CompletionItem.command_completion(
            "reindent", "reindent", args={"single_line": False}
        ),
    ]
    return sublime.CompletionList(items, sublime.AutoCompleteFlags.INHIBIT_WORD_COMPLETIONS)


def quick_panel(window: sublime.Window) -> None:
    items = [
        sublime.QuickPanelItem(folder, details=folder, kind=sublime.KIND_NAVIGATION)
        for folder in window.folders()
    ]
    window.show_quick_panel(items, lambda index: None, placeholder="Pick a folder")


def phantoms(view: sublime.View) -> sublime.PhantomSet:
    phantom_set = sublime.PhantomSet(view, "sublime-text-stubs-demo")
    phantom_set.update(
        [
            sublime.Phantom(
                region,
                "<b>here</b>",
                sublime.PhantomLayout.BELOW,
            )
            for region in view.sel()
        ]
    )
    return phantom_set


def buffer_of(view: sublime.View) -> Tuple[int, List[sublime.View]]:
    buffer: sublime.Buffer = view.buffer()
    return buffer.id(), buffer.views()


def syntax_of(view: sublime.View) -> Optional[str]:
    syntax: Optional[sublime.Syntax] = view.syntax()
    return None if syntax is None else syntax.scope


def timeouts() -> None:
    sublime.set_timeout(lambda: sublime.status_message("later"), 100)
    sublime.set_timeout_async(lambda: sublime.status_message("later, off thread"))


def platform_is_known() -> bool:
    # `platform()` is annotated with a `Literal`, so this comparison is checked.
    return sublime.platform() in ("osx", "linux", "windows")
