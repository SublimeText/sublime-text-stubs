"""Sample consumer code exercising the `sublime_plugin` stubs.

Not executed. See the module docstring of `check_sublime.py`.
"""

from typing import List, Optional

import sublime
import sublime_plugin


class DemoTextCommand(sublime_plugin.TextCommand):
    def run(self, edit: sublime.Edit) -> None:
        for region in reversed(list(self.view.sel())):
            self.view.replace(edit, region, self.view.substr(region).upper())

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


class DemoEventListener(sublime_plugin.EventListener):
    def on_post_save(self, view: sublime.View) -> None:
        name: Optional[str] = view.file_name()
        if name is not None:
            sublime.status_message("saved {}".format(name))

    def on_hover(
        self, view: sublime.View, point: sublime.Point, hover_zone: sublime.HoverZone
    ) -> None:
        if hover_zone is not sublime.HoverZone.TEXT:
            return
        view.show_popup(view.substr(view.word(point)), location=point)


class DemoViewEventListener(sublime_plugin.ViewEventListener):
    @classmethod
    def is_applicable(cls, settings: sublime.Settings) -> bool:
        return settings.get("syntax") == "Packages/Python/Python.sublime-syntax"
