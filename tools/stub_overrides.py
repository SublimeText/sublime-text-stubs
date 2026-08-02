"""Declarative corrections applied by ``generate_stubs.py``.

Everything the generator cannot derive from the reference sources lives here,
so that the ``.pyi`` files themselves never need to be hand-edited.

Keys are dotted names rooted at the module: ``sublime.Settings.to_dict`` for a
method, ``sublime.CompletionItem.__init__.kind`` for a single parameter.
"""

from __future__ import annotations

# Modules to generate, in the order they are written.
# Maps the module name to the stub package directory under ``stubs/``.
MODULES = {
    "sublime": "sublime-stubs",
    "sublime_plugin": "sublime_plugin-stubs",
    "sublime_types": "sublime_types-stubs",
}

# Names each module pulls in from ``sublime_types``.
# The reference imports these under ``if TYPE_CHECKING``; the stubs import them
# unconditionally and re-export them (``X as X``), because plugin authors refer
# to them as ``sublime.Point`` and the like.
SUBLIME_TYPES_REEXPORTS = {
    "sublime": ["CommandArgs", "CompletionValue", "DIP", "Kind", "Point", "Value", "Vector"],
    "sublime_plugin": ["Event", "Value"],
}

# `sublime_plugin` is mostly plugin-host machinery: module level registries, the
# `on_*(view_id)` callbacks the host invokes, and the importlib finder/loader for
# `.sublime-package` archives. Only the documented plugin-facing API is stubbed.
SUBLIME_PLUGIN_PUBLIC_API = [
    "CommandInputHandler",
    "BackInputHandler",
    "TextInputHandler",
    "ListInputHandler",
    "Command",
    "ApplicationCommand",
    "WindowCommand",
    "TextCommand",
    "EventListener",
    "ViewEventListener",
    "TextChangeListener",
]

# Internal members that are neither underscore-prefixed nor underscore-suffixed,
# so the naming conventions do not catch them. None of these are documented API.
SKIP_MEMBERS = [
    "sublime.make_sheet",  # factory the plugin host calls to wrap a sheet id
    "sublime_plugin.Command.filter_args",  # argument munging done by the host
    # See COMMAND_RUN_NOTE.
    "sublime_plugin.Command.run",
    "sublime_plugin.ApplicationCommand.run",
    "sublime_plugin.WindowCommand.run",
    "sublime_plugin.TextCommand.run",
]

# Return type overrides, taking precedence over the annotation in the reference.
# Mostly bare generics, which `reportMissingTypeArguments` rejects under strict mode.
RETURNS = {
    # Bare `dict` in the reference; strict mode needs type arguments.
    "sublime.ui_info": "dict[str, Value]",
    # Each entry has a "command" and an "args" key.
    "sublime.get_macro": "list[dict[str, Value]]",
    "sublime.Settings.to_dict": "dict[str, Value]",
    "sublime.Window.get_layout": "dict[str, Value]",
    # Unannotated in the reference.
    "sublime.Window.__eq__": "bool",
    "sublime.Window.get_output_panel": "View",
    "sublime.Window.show_input_panel": "View",
    "sublime.Region.__iter__": "Iterator[Point]",
    "sublime.HistoricPosition.__repr__": "str",
    "sublime.TextChange.__repr__": "str",
    "sublime.TextSheet.__repr__": "str",
    "sublime.ImageSheet.__repr__": "str",
    "sublime.HtmlSheet.__repr__": "str",
    # These forward the return value of a void `sublime_api` call.
    "sublime.View.set_read_only": "None",
    "sublime.View.set_scratch": "None",
    "sublime.View.show_popup_menu": "None",
    "sublime.View.export_to_html": "str",
    "sublime.Settings.setdefault": "Value",
    "sublime_plugin.BackInputHandler.name": "str",
    "sublime_plugin.TextChangeListener.is_applicable": "bool",
}

# Parameter type overrides / annotations the generator cannot infer.
PARAMS = {
    "sublime.load_binary_resource.name": "str",
    "sublime.find_syntax_for_file.path": "str",
    "sublime.set_timeout.callback": "Callable[[], Any]",
    "sublime.set_timeout_async.callback": "Callable[[], Any]",
    "sublime.Window.__eq__.other": "object",
    # Every wrapper object is constructed from the id of its native counterpart.
    "sublime.Selection.__init__.id": "int",
    "sublime.Sheet.__init__.id": "int",
    "sublime.View.__init__.id": "int",
    "sublime.Buffer.__init__.id": "int",
    "sublime.Settings.__init__.id": "int",
    "sublime.Sheet.close.on_close": "Callable[[bool], None]",
    "sublime.View.close.on_close": "Callable[[bool], None]",
    "sublime.View.show_popup_menu.flags": "int",
    "sublime.Settings.update.other": "Union[Settings, Dict[str, Value], Iterable[Tuple[str, Value]]]",
    "sublime.Settings.update.kwargs": "Value",
    "sublime.CompletionItem.__init__.kind": "Kind",
    "sublime.CompletionItem.snippet_completion.kind": "Kind",
    "sublime.CompletionItem.command_completion.kind": "Kind",
    "sublime.CompletionItem.command_completion.args": "CommandArgs",
    "sublime.QuickPanelItem.__init__.kind": "Kind",
    "sublime.ListInputItem.__init__.kind": "Kind",
    # Unannotated with a `details=""` default, so the generator infers `str` from
    # the default -- but the attribute assigned three lines below says
    # `self.details: str | list[str] | tuple[str]`, and the runtime joins lists and
    # tuples with "\x1f" (`references/python38/sublime.py:1838`). The attribute wins.
    "sublime.QuickPanelItem.__init__.details": "Union[str, List[str], Tuple[str]]",
    "sublime.ListInputItem.__init__.details": "Union[str, List[str], Tuple[str]]",
    "sublime_plugin.CommandInputHandler.next_input.args": "Dict[str, Value]",
    "sublime_plugin.Command.input.args": "Dict[str, Value]",
    "sublime_plugin.ListInputHandler.description.value": "Value",
    "sublime_plugin.WindowCommand.__init__.window": "sublime.Window",
    "sublime_plugin.TextCommand.__init__.view": "sublime.View",
    # The `.. method::` directives for these two spell `buffer: View`, but their
    # own prose says "buffer will be a Buffer object" and the dispatcher does
    # `buf = sublime.Buffer(buffer_id)` before invoking the callbacks
    # (`references/python38/sublime_plugin.py:829` and `:838`).
    "sublime_plugin.EventListener.on_associate_buffer.buffer": "sublime.Buffer",
    "sublime_plugin.EventListener.on_associate_buffer_async.buffer": "sublime.Buffer",
}

# Types for instance attributes assigned without an annotation in `__init__`.
ATTRIBUTES = {
    "sublime.View.settings_object": "Optional[Settings]",
    "sublime.CompletionList.target": "Optional[int]",
}

# `sublime_types` aliases the generator cannot take verbatim.
TYPE_ALIASES = {
    # The reference says `dict`; an untyped dict is rejected under strict mode.
    # An event is a mapping of `x`/`y`/`modifier_keys` style entries.
    "Event": "Dict[str, Any]",
    # JSON is recursive: the reference spells the containers as `List[Any]` /
    # `Dict[str, Any]`, which loses the element types. Quoting the self-reference
    # is what makes the recursive alias legal.
    "Value": 'Union[bool, str, int, float, List["Value"], Dict[str, "Value"], None]',
}

# --- docstring-only event handlers -------------------------------------------
# `EventListener`, `ViewEventListener` and `TextChangeListener` declare no handler
# methods at all: Sublime Text dispatches to them dynamically, and each handler
# exists only as a `.. method::` directive in the class docstring. The generator
# turns those directives into real declarations; the return type comes from here,
# since the directives either omit it or spell it in prose-flavoured pseudo-Python.

EVENT_HANDLER_CLASSES = ["EventListener", "ViewEventListener", "TextChangeListener"]

EVENT_HANDLER_DEFAULT_RETURN = "None"

EVENT_HANDLER_RETURNS = {
    "on_query_context": "Optional[bool]",
    "on_query_completions": (
        "Union[None, List[sublime.CompletionValue],"
        " Tuple[List[sublime.CompletionValue], sublime.AutoCompleteFlags],"
        " sublime.CompletionList]"
    ),
    "on_text_command": "Optional[Tuple[str, sublime.CommandArgs]]",
    "on_window_command": "Optional[Tuple[str, sublime.CommandArgs]]",
}

COMMAND_RUN_NOTE = """\
# `run` is deliberately not declared on any of the command classes below. Sublime Text
# invokes it dynamically with command-specific keyword arguments, so a base signature
# would reject every subclass that declares arguments of its own. Write it as
# `def run(self, **kwargs)` -- or, for a TextCommand, `def run(self, edit, **kwargs)`."""

# `Command.is_enabled`, `is_visible`, `is_checked` and `description` receive command
# arguments the same dynamic way as `run`: the host-facing `is_enabled_` and friends call
# `self.is_enabled(**self.filter_args(args))` and fall back to a no-argument call on
# `TypeError` (reference `sublime_plugin.py` lines 1414-1493). Unlike `run` they do have a
# meaningful default implementation, so they are kept -- and emitted exactly as the
# reference declares them, without parameters. sublimelsp/LSP's hand-written stub instead
# adds `**kwargs: dict[str, Any]` to all four; we deliberately do not, because
#  1. it contradicts the reference declaration;
#  2. it does not solve what it looks like it solves: a subclass narrowing to
#     `def is_enabled(self, my_arg: str) -> bool` is an incompatible override under Liskov
#     rules either way, and pyright and mypy both report it whether the base declares
#     `**kwargs` or nothing at all; and
#  3. the spelling is wrong regardless: an annotation on `**kwargs` describes each value,
#     not the dict, so it would have to be `**kwargs: Any`.
