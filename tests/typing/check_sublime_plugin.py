"""Sample consumer code exercising the `sublime_plugin` stubs.

Not executed. See the module docstring of `check_sublime.py`.
"""

from typing import Dict, Iterable, Iterator, List, Optional, Tuple, TYPE_CHECKING

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


# The runtime classes carry no `__class_getitem__` on the Python 3.8 plugin host, so a
# parameterized base has to be built under `if TYPE_CHECKING:` and the runtime has to
# see the bare class.
if TYPE_CHECKING:
    _StrCommandInputHandler = sublime_plugin.CommandInputHandler[str]
    _StrListInputHandler = sublime_plugin.ListInputHandler[str]
    _TagsListInputHandler = sublime_plugin.ListInputHandler[List[sublime.Value]]
else:
    _StrCommandInputHandler = sublime_plugin.CommandInputHandler
    _StrListInputHandler = sublime_plugin.ListInputHandler
    _TagsListInputHandler = sublime_plugin.ListInputHandler


class NameInputHandler(_StrListInputHandler):
    @override
    def list_items(self) -> Iterator[str]:
        # Any `Iterable` is accepted, not just a `list`.
        for window in sublime.windows():
            yield str(window.id())

    @override
    def description(self, value: str, text: str) -> str:
        return f"{text} ({value})"

    @override
    def preview(self, text: str) -> str:
        return text

    @override
    def validate(self, text: str, event: Optional[sublime_plugin.Event] = None) -> bool:
        return text != ""

    @override
    def confirm(self, text: str, event: Optional[sublime_plugin.Event] = None) -> None:
        sublime.status_message(text)


class TagsInputHandler(_TagsListInputHandler):
    # A container value type has to have `Value` elements: `list` is invariant, so
    # `List[str]` is not a `Value`.
    def _items(self) -> "List[sublime.ListInputItem[List[sublime.Value]]]":
        values: List[List[sublime.Value]] = [["red", "green"], ["blue"]]
        return [sublime.ListInputItem(", ".join(str(tag) for tag in v), v) for v in values]

    @override
    def list_items(self) -> "Tuple[Iterable[sublime.ListInputItem[List[sublime.Value]]], int]":
        # The pre-select form accepts any `Iterable` too, not just a `list`.
        return (self._items(), 0)

    @override
    def description(self, value: List[sublime.Value], text: str) -> str:
        return f"{text} ({len(value)})"

    # These three receive the *value* of the selected item, not its row text, so they
    # are typed by the handler's own value type rather than by `str`.
    @override
    def preview(self, text: List[sublime.Value]) -> str:
        return ", ".join(str(tag) for tag in text)

    @override
    def validate(
        self, text: List[sublime.Value], event: Optional[sublime_plugin.Event] = None
    ) -> bool:
        return len(text) > 0

    @override
    def confirm(
        self, text: List[sublime.Value], event: Optional[sublime_plugin.Event] = None
    ) -> None:
        sublime.status_message(str(len(text)))


class MessageInputHandler(sublime_plugin.TextInputHandler):
    # `TextInputHandler` is a `CommandInputHandler[str]`, so `text` is `str` here.
    @override
    def preview(self, text: str) -> str:
        return text.upper()

    @override
    def validate(self, text: str, event: Optional[sublime_plugin.Event] = None) -> bool:
        return text != ""


def preview_of(handler: "_StrCommandInputHandler", text: str) -> str:
    # A `TextInputHandler` has to *be* a `CommandInputHandler[str]`: under
    # contravariance the bare `CommandInputHandler[Never]` is not assignable here.
    result = handler.preview(text)
    return result.data if isinstance(result, sublime.Html) else result


def message_preview() -> str:
    return preview_of(MessageInputHandler(), "hello")


class DemoGenericInputCommand(sublime_plugin.WindowCommand):
    @override
    def input(self, args: Dict[str, sublime.Value]) -> Optional[sublime_plugin.CommandInputHandler]:
        # The bare annotation means `CommandInputHandler[Never]`, the top of the handler
        # lattice, so every handler kind is assignable to it.
        if "message" not in args:
            return MessageInputHandler()
        if "name" not in args:
            return NameInputHandler()
        return TagsInputHandler()

    def run(self, message: str, name: str, tags: List[sublime.Value]) -> None:
        self.window.status_message(f"{message} {name} {len(tags)}")


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
