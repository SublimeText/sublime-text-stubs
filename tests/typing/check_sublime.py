"""Sample consumer code exercising the `sublime` stubs.

Not executed. Its only purpose is to give the type checkers something concrete to
verify the stubs against, since `sublime` cannot be imported outside Sublime Text.
"""

from typing import List, Optional

import sublime


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
        "sublime-types-demo",
        regions,
        scope="region.bluish",
        flags=sublime.RegionFlags.DRAW_NO_FILL | sublime.RegionFlags.PERSISTENT,
    )


def read_setting(name: str) -> sublime.Value:
    return sublime.load_settings("Preferences.sublime-settings").get(name, None)


def open_transient(window: sublime.Window, path: str) -> sublime.View:
    return window.open_file(path, sublime.NewFileFlags.TRANSIENT)


def region_arithmetic() -> int:
    a = sublime.Region(0, 10)
    b = sublime.Region(5, 20)
    return a.cover(b).size() - a.intersection(b).size()
