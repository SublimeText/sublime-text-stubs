"""Sample consumer code exercising the `sublime_plugin` stubs.

Not executed. See the module docstring of `check_sublime.py`.
"""

from typing import Dict, List, Optional, Tuple

import sublime
import sublime_plugin
from typing_extensions import override


class DemoTextCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit) -> None:
        for region in reversed(list(self.view.sel())):
            self.view.replace(edit, region, self.view.substr(region).upper())

    @override
    def is_enabled(self) -> bool:
        return not self.view.is_read_only()


class DemoWindowCommand(sublime_plugin.WindowCommand):
    def run(self) -> None:
        paths: List[str] = self.window.folders()
        self.window.show_quick_panel(paths, self._on_select)

    def _on_select(self, index: int) -> None:
        if index < 0:
            return
        self.window.status_message(self.window.folders()[index])


class DemoApplicationCommand(sublime_plugin.ApplicationCommand):
    @override
    def is_visible(self) -> bool:
        return len(sublime.windows()) > 1


class FolderInputHandler(sublime_plugin.ListInputHandler):
    @override
    def name(self) -> str:
        return "folder"

    @override
    def list_items(self) -> List[str]:
        return sublime.active_window().folders()

    @override
    def next_input(self, args: Dict[str, sublime.Value]) -> Optional[sublime_plugin.CommandInputHandler]:
        return None


class DemoInputCommand(sublime_plugin.WindowCommand):
    @override
    def input(self, args: Dict[str, sublime.Value]) -> Optional[sublime_plugin.CommandInputHandler]:
        if "folder" not in args:
            return FolderInputHandler()
        return None

    def run(self, folder: str) -> None:
        self.window.status_message(folder)


class DemoEventListener(sublime_plugin.EventListener):
    @override
    def on_post_save(self, view: sublime.View) -> None:
        name: Optional[str] = view.file_name()
        if name is not None:
            sublime.status_message(f"saved {name}")

    @override
    def on_hover(
        self, view: sublime.View, point: sublime.Point, hover_zone: sublime.HoverZone
    ) -> None:
        if hover_zone is not sublime.HoverZone.TEXT:
            return
        view.show_popup(view.substr(view.word(point)), location=point)

    @override
    def on_query_context(
        self,
        view: sublime.View,
        key: str,
        operator: sublime.QueryOperator,
        operand: str,
        match_all: bool,
    ) -> Optional[bool]:
        if key != "demo.has_selection":
            return None
        return len(view.sel()) > 0

    @override
    def on_text_command(
        self, view: sublime.View, command_name: str, args: sublime.CommandArgs
    ) -> Optional[Tuple[str, sublime.CommandArgs]]:
        if command_name == "insert_best_completion":
            return ("insert", {"characters": "\t"})
        return None


class DemoViewEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    @override
    def is_applicable(cls, settings: sublime.Settings) -> bool:
        return settings.get("syntax") == "Packages/Python/Python.sublime-syntax"

    # Declared only as a `.. method::` directive in the reference docstring.
    @override
    def on_load(self) -> None:
        self.view.settings().set("demo.loaded", True)


class DemoTextChangeListener(sublime_plugin.TextChangeListener):
    @override
    def on_text_changed(self, changes: List[sublime.TextChange]) -> None:
        for change in changes:
            if change.str:
                self.buffer.primary_view().set_status("demo", change.str)


def event_type_is_reexported(event: sublime_plugin.Event) -> object:
    return event.get("modifier_keys")
