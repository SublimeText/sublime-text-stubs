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
    "sublime.Settings.update.other": "Settings | dict[str, Value] | Iterable[tuple[str, Value]]",
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
    "sublime.QuickPanelItem.__init__.details": "str | list[str] | tuple[str]",
    "sublime.ListInputItem.__init__.details": "str | list[str] | tuple[str]",
    "sublime_plugin.CommandInputHandler.next_input.args": "dict[str, Value]",
    "sublime_plugin.Command.input.args": "dict[str, Value]",
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
    "sublime.View.settings_object": "Settings | None",
    "sublime.CompletionList.target": "int | None",
}

# `sublime_types` aliases the generator cannot take verbatim.
TYPE_ALIASES = {
    # JSON is recursive: the reference spells the containers as `List[Any]` /
    # `Dict[str, Any]`, which loses the element types. The self-reference needs no
    # quoting -- in a `.pyi` nothing is evaluated, so a forward reference resolves
    # regardless of where it appears; all four checkers accept it.
    "Value": "bool | str | int | float | list[Value] | dict[str, Value] | None",
}

# `sublime_types` aliases the generator replaces with a class declaration instead of a
# plain `X: TypeAlias = ...` line. The reference spells `Event` as a bare `dict`; the
# "Event Objects" section of the API docs documents its `x`/`y`/`modifier_keys` keys,
# which narrow cleanly to a `TypedDict`. `Event` itself is a real name upstream (bound
# to plain `dict`, so importing it unconditionally still works at runtime), but
# `ModifierKeys` is a stub-only addition with no upstream counterpart at all, hence the
# docstring telling plugin authors to import it under `if TYPE_CHECKING:`.
TYPE_ALIAS_CLASSES = {
    "Event": '''\
class ModifierKeys(TypedDict, total=False):
    """
    The ``modifier_keys`` entry of an `Event`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``ModifierKeys`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    primary: bool
    ctrl: bool
    alt: bool
    altgr: bool
    shift: bool
    super: bool

class Event(TypedDict, total=False):
    """
    Contains information about a user's interaction with a menu, command palette
    selection, quick panel selection or HTML document.
    """
    x: float
    y: float
    modifier_keys: ModifierKeys''',
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
    "on_query_context": "bool | None",
    "on_query_completions": (
        "list[sublime.CompletionValue]"
        " | tuple[list[sublime.CompletionValue], sublime.AutoCompleteFlags]"
        " | sublime.CompletionList | None"
    ),
    "on_text_command": "tuple[str, sublime.CommandArgs] | None",
    "on_window_command": "tuple[str, sublime.CommandArgs] | None",
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
#  2. it makes *every* override an error, not just the one it looks like it fixes. An
#     override may not accept less than its base, and dropping `**kwargs` does exactly
#     that, so with `**kwargs` in the base pyright and mypy both reject all of
#     `def is_enabled(self)` (what the reference itself declares, and what almost every
#     plugin writes), `def is_enabled(self, my_arg: str)` and
#     `def is_enabled(self, my_arg: str = "")`; and
#  3. the spelling is wrong regardless: an annotation on `**kwargs` describes each value,
#     not the dict, so it would have to be `**kwargs: Any`.
#
# With the parameterless declaration, only a *required* parameter is rejected, and that
# rejection is correct: `is_enabled_` catches the `TypeError` from `is_enabled(**args)`
# and retries as `is_enabled()`, which raises `TypeError` again -- from inside the
# `except` block, so it propagates. Any of
#     def is_enabled(self) -> bool
#     def is_enabled(self, my_arg: str = "") -> bool
#     def is_enabled(self, **kwargs: Any) -> bool
# type-checks clean under pyright, mypy and ty, and all three are safe at runtime.
#
# Two spellings would silence the diagnostic outright: `def is_enabled(self, *args: Any,
# **kwargs: Any) -> bool` and `is_enabled: Callable[..., bool]`. Both are the gradual
# `...` signature, which is assignable from anything, so the override check is skipped
# and only the return type stays checked. Neither is used here: they buy the ability to
# write the one spelling that crashes, and cost the signature on hover. Note that the
# escape hatch is specifically `Any` -- `*args: object, **kwargs: object` is an ordinary
# signature and rejects everything. Overloading the base (a parameterless overload
# alongside a `**kwargs` one) does not work either: an override must satisfy every
# overload at once, so that combination rejects both spellings above.
#
# `**kwargs: Value` would describe the call more accurately than `Any` -- command
# arguments come from JSON in a keymap, menu or palette entry -- but only almost:
# `filter_args` keeps the `event` argument when `want_event()` is true, and `Event` is a
# `TypedDict`, which is not assignable to `Value`. It would have to be `Value | Event`,
# and it inherits problem 2 above regardless.
