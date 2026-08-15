"""Sample consumer code exercising the `sublime` stubs.

Not executed. Its only purpose is to give the type checkers something concrete to
verify the stubs against, since `sublime` cannot be imported outside Sublime Text.
"""

from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import sublime
from sublime_types import Value as ValueFromTypesModule
from typing_extensions import assert_type

if TYPE_CHECKING:
    from sublime_types import FontOptions, UIInfoPalette, ValueLike


def collect_word_regions(view: sublime.View) -> List[sublime.Region]:
    return [view.word(region) for region in view.sel()]


def describe_cursor(view: sublime.View) -> str:
    point: sublime.Point = view.sel()[0].begin()
    row, col = view.rowcol(point)
    return f"{row + 1}:{col + 1}"


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


def accent_color() -> Optional[str]:
    # `UIInfo` and its nested TypedDicts are stub-only, so the fields have to be
    # narrowed with `.get` rather than assumed present.
    palette: Optional[UIInfoPalette] = sublime.ui_info().get("color_scheme", {}).get("palette")
    return palette.get("accent") if palette is not None else None


def scope_colors(view: sublime.View, scope: str) -> Tuple[str, Optional[str]]:
    # A required key needs no `.get` guard; a "(only if set)" one does.
    style = view.style_for_scope(scope)
    return style["foreground"], style.get("background")


def scope_origin(view: sublime.View, scope: str) -> Tuple[str, int]:
    # The reference docstring swaps these two types; the stubs follow the runtime.
    style = view.style_for_scope(scope)
    return style["source_file"], style["source_line"]


def replay_macro(window: sublime.Window) -> None:
    for step in sublime.get_macro():
        window.run_command(step["command"], step["args"])


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
    window.show_quick_panel(items, lambda _index: None, placeholder="Pick a folder")


def list_input_item_value() -> int:
    # `assert_type` rather than an annotated assignment: `Any` satisfies the latter,
    # so it would not catch a regression to the pre-generic stubs.
    item = sublime.ListInputItem("label", 42)
    return assert_type(item.value, int)


def bare_list_input_item_value(item: sublime.ListInputItem) -> sublime.Value:
    # A bare, unparameterized use defaults to `Value` rather than to `Any`, so an
    # author who does not parameterize still has to narrow before using the value.
    return assert_type(item.value, sublime.Value)


def make_list_input_item(value: List[str]) -> "sublime.ListInputItem[List[str]]":
    # The runtime class cannot be subscripted on the Python 3.8 host, so a
    # parameterized annotation has to be quoted. The argument has to satisfy the
    # `ValueLike` bound, whose containers are covariant, so a concrete `List[str]` is
    # a valid value type even though it is not a `Value`.
    return sublime.ListInputItem("label", value)


def is_empty_value(value: "ValueLike") -> bool:
    # `ValueLike` is stub-only, so it is imported under `if TYPE_CHECKING:` and the
    # annotation is quoted.
    return value is None


def value_like_accepts_concrete_containers() -> Tuple[bool, bool]:
    # The point of `ValueLike`: its containers are the covariant `Sequence` and
    # `Mapping`, so these two pass as they are. Against `Value`, whose containers are
    # the invariant `list` and `dict`, neither call type-checks.
    tags: List[str] = ["draft", "review"]
    labels: Dict[str, str] = {"draft": "Draft"}
    return is_empty_value(tags), is_empty_value(labels)


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


def widen_first_column(window: sublime.Window) -> None:
    # `set_layout` has to accept what `layout` returns.
    layout = window.layout()
    cols: List[float] = layout["cols"]
    # The outer entries are the window edges; only the interior ones are dividers.
    if cols[1:-1]:
        cols[1] = 0.6
    window.set_layout(layout)


def expand_in_project(window: sublime.Window, template: str) -> sublime.Value:
    # `extract_variables()` is documented as input to `expand_variables()`.
    variables = window.extract_variables()
    name = variables.get("project_name")
    if name is None:
        return template
    return sublime.expand_variables(template, variables)


def pick_font(on_chosen: Callable[[str], None]) -> None:
    def chosen(options: Optional["FontOptions"]) -> None:
        # The callback receives `None` if the dialog was cancelled.
        if options is not None:
            on_chosen(options.get("font_face", "monospace"))

    sublime.choose_font_dialog(chosen, {"font_face": "monospace"})
