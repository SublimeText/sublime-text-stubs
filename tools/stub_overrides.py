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
    "sublime": [
        "CommandArgs",
        "CommandArgsLike",
        "CompletionValue",
        "DIP",
        "FontOptions",
        "Kind",
        "MacroStep",
        "Point",
        "ScopeStyle",
        "UIInfo",
        "Value",
        "ValueLike",
        "Vector",
        "WindowLayout",
        "WindowVariables",
    ],
    "sublime_plugin": ["Event", "Value", "ValueLike"],
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

# Annotations for module level constants the reference assigns a bare literal, which
# would otherwise leave their type to inference.
CONSTANTS = {
    # A popup flag predating `PopupFlags`, and the only one with no member of that
    # enum to alias; references/python38/sublime.py:260. `Literal` keeps the value in
    # the type, which is what the enum members it sits among carry too.
    "sublime.HTML": "Literal[1]",
}

# Return type overrides, taking precedence over the annotation in the reference.
# Mostly bare generics, which `reportMissingTypeArguments` rejects under strict mode.
RETURNS = {
    # Bare `dict` in the reference; the API docs narrow it no further than
    # `dict[str, Value]`, but `UIInfo` (see `EXTRA_TYPE_ALIAS_CLASSES`) spells out the
    # `system`/`theme`/`color_scheme` keys the docstring already names.
    "sublime.ui_info": "UIInfo",
    # Bare `list[dict]` in the reference, whose docstring
    # (references/python38/sublime.py:1314-1320) names both keys of every entry;
    # see `MacroStep` in `EXTRA_TYPE_ALIAS_CLASSES`.
    "sublime.get_macro": "list[MacroStep]",
    "sublime.Settings.to_dict": "dict[str, Value]",
    # Bare `dict[str, Value]` in the reference for `layout`, and unannotated for the
    # deprecated `get_layout` (references/python38/sublime.py:1679-1695); neither
    # docstring names a key, see `WindowLayout` in `EXTRA_TYPE_ALIAS_CLASSES`.
    "sublime.Window.layout": "WindowLayout",
    "sublime.Window.get_layout": "WindowLayout",
    # Bare `dict[str, Value]` in the reference, whose docstring
    # (references/python38/sublime.py:3057-3080) names every key; see `ScopeStyle` in
    # `EXTRA_TYPE_ALIAS_CLASSES`.
    "sublime.View.style_for_scope": "ScopeStyle",
    # `dict[str, str]` in the reference, whose docstring
    # (references/python38/sublime.py:2017-2038) names every key it may contain; see
    # `WindowVariables` in `EXTRA_TYPE_ALIAS_CLASSES`.
    "sublime.Window.extract_variables": "WindowVariables",
    # Unannotated in the reference.
    "sublime.Window.__eq__": "bool",
    "sublime.Window.get_output_panel": "View",
    "sublime.Window.show_input_panel": "View",
    "sublime.Region.__iter__": "Iterator[Point]",
    # These forward the return value of a void `sublime_api` call.
    "sublime.View.set_read_only": "None",
    "sublime.View.set_scratch": "None",
    "sublime.View.show_popup_menu": "None",
    "sublime.View.export_to_html": "str",
    "sublime.Settings.setdefault": "Value",
    "sublime_plugin.BackInputHandler.name": "str",
    # The reference spells a six-arm union of `list`-only forms
    # (references/python38/sublime_plugin.py:1306-1311), but `setup_` only checks for the
    # `(items, index)` tuple and then iterates, dispatching per item
    # (references/python38/sublime_plugin.py:1343-1372). So any `Iterable` works, and the
    # three item forms may be mixed in one -- hence the union over the *element* type.
    "sublime_plugin.ListInputHandler.list_items": (
        "Iterable[str | tuple[str, _T_Value] | sublime.ListInputItem[_T_Value]]"
        " | tuple[Iterable[str | tuple[str, _T_Value] | sublime.ListInputItem[_T_Value]], int]"
    ),
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
    # The inbound half of the value layer: every parameter from here through
    # `CompletionItem.command_completion.args` accepts the covariant
    # `ValueLike`/`CommandArgsLike` in place of the invariant `Value`/`CommandArgs` a
    # plugin author would otherwise have to satisfy exactly. See `EXTRA_TYPE_ALIASES`
    # for the rationale.
    "sublime.encode_value.value": "ValueLike",
    "sublime.expand_variables.value": "ValueLike",
    "sublime.run_command.args": "CommandArgsLike",
    "sublime.format_command.args": "CommandArgsLike",
    "sublime.html_format_command.args": "CommandArgsLike",
    "sublime.command_url.args": "CommandArgsLike",
    "sublime.Window.run_command.args": "CommandArgsLike",
    "sublime.Window.set_project_data.data": "ValueLike",
    "sublime.View.run_command.args": "CommandArgsLike",
    "sublime.View.begin_edit.args": "CommandArgsLike",
    "sublime.Settings.__setitem__.value": "ValueLike",
    "sublime.Settings.set.value": "ValueLike",
    "sublime.Settings.setdefault.value": "ValueLike",
    "sublime.Settings.get.default": "ValueLike",
    # Not an overshoot like the rest of the group: `Settings.update` is implemented in
    # Python and genuinely iterates any `Mapping`
    # (references/python38/sublime.py:3862-3883).
    "sublime.Settings.update.other": "Settings | Mapping[str, ValueLike] | Iterable[tuple[str, ValueLike]]",
    "sublime.Settings.update.kwargs": "ValueLike",
    "sublime.CompletionItem.command_completion.args": "CommandArgsLike",
    "sublime.CompletionItem.__init__.kind": "Kind",
    "sublime.CompletionItem.snippet_completion.kind": "Kind",
    "sublime.CompletionItem.command_completion.kind": "Kind",
    "sublime.QuickPanelItem.__init__.kind": "Kind",
    "sublime.ListInputItem.__init__.kind": "Kind",
    # `Any` in the reference (references/python38/sublime.py:4327); the class is generic
    # over it instead, so the constructor argument is what fixes the item's value type.
    "sublime.ListInputItem.__init__.value": "_T_Value",
    # Unannotated with a `details=""` default, so the generator infers `str` from
    # the default -- but the attribute assigned three lines below says
    # `self.details: str | list[str] | tuple[str]`, and the runtime joins lists and
    # tuples with "\x1f" (`references/python38/sublime.py:1838`). The attribute wins.
    "sublime.QuickPanelItem.__init__.details": "str | list[str] | tuple[str]",
    "sublime.ListInputItem.__init__.details": "str | list[str] | tuple[str]",
    "sublime_plugin.CommandInputHandler.next_input.args": "dict[str, Value]",
    "sublime_plugin.Command.input.args": "dict[str, Value]",
    # The reference spells all three `text: str`, but for a `ListInputHandler` the host
    # passes the *value* of the selected item, not its row text
    # (references/python38/sublime_plugin.py:1220-1242). See `TYPE_VARS`.
    "sublime_plugin.CommandInputHandler.preview.text": "_T_Value_contra",
    "sublime_plugin.CommandInputHandler.validate.text": "_T_Value_contra",
    "sublime_plugin.CommandInputHandler.confirm.text": "_T_Value_contra",
    # Unannotated in the reference; it is the same value the methods above receive.
    "sublime_plugin.ListInputHandler.description.value": "_T_Value",
    "sublime_plugin.WindowCommand.__init__.window": "sublime.Window",
    "sublime_plugin.TextCommand.__init__.view": "sublime.View",
    # The `.. method::` directives for these two spell `buffer: View`, but their
    # own prose says "buffer will be a Buffer object" and the dispatcher does
    # `buf = sublime.Buffer(buffer_id)` before invoking the callbacks
    # (`references/python38/sublime_plugin.py:829` and `:838`).
    "sublime_plugin.EventListener.on_associate_buffer.buffer": "sublime.Buffer",
    "sublime_plugin.EventListener.on_associate_buffer_async.buffer": "sublime.Buffer",
    # `layout` in the reference is `dict[str, Value]`
    # (references/python38/sublime.py:1691), but a `WindowLayout` is not assignable
    # to that: without this override, `window.set_layout(window.layout())` stops
    # type-checking once `layout()` returns a `WindowLayout` instead.
    "sublime.Window.set_layout.layout": "WindowLayout",
    # `variables` in the reference is `dict[str, str]`
    # (references/python38/sublime.py:1253), and sublime.py:2036 tells the user the
    # result of `extract_variables()` is "suitable for use with `expand_variables()`".
    # A `TypedDict` is assignable to neither `dict[str, str]` nor `Mapping[str, str]`,
    # only to `Mapping[str, object]` -- which would wrongly accept any mapping of
    # arbitrary values -- so the parameter has to name both types.
    "sublime.expand_variables.variables": "dict[str, str] | WindowVariables",
    # The reference spells these as `callback: Callable[[Value], None]` and
    # `default: dict[str, Value]` (references/python38/sublime.py:925); see
    # `FontOptions` in `EXTRA_TYPE_ALIAS_CLASSES`. The `| None` on the callback
    # argument is from the docstring (sublime.py:933-934): it "will be called with
    # ``None`` if the dialog is cancelled". `default` needs no `| None` here -- the
    # generator already emits `FontOptions | None = ...` from the reference's
    # `= None` default.
    "sublime.choose_font_dialog.callback": "Callable[[FontOptions | None], None]",
    "sublime.choose_font_dialog.default": "FontOptions",
}

# Types for instance attributes assigned without an annotation in `__init__`.
ATTRIBUTES = {
    "sublime.View.settings_object": "Settings | None",
    "sublime.CompletionList.target": "int | None",
    # Annotated `Any` in the reference (references/python38/sublime.py:4330), whose own
    # docstring one line below calls it "A `Value` passed to the command"; see
    # `TYPE_VARS`.
    "sublime.ListInputItem.value": "_T_Value",
}

# Module level `TypeVar` declarations, keyed by module name. The reference has no
# counterpart to key them to, so the value is the complete declaration block, emitted
# at the top of the module body (after the imports, before the first declaration). A
# module declaring more than one TypeVar spells them as one multi-line block.
TYPE_VARS: dict[str, str] = {
    # Bounded by `ValueLike` because the item's value is what gets delivered to the
    # command: "A `Value` passed to the command if the row is selected"
    # (references/python38/sublime.py:4330-4331). The bound is `ValueLike` rather than
    # `Value` because it constrains what an author may parameterize on, and that is an
    # inbound position: `Value`'s containers are invariant, so it would reject
    # `ListInputItem[List[str]]`. See `EXTRA_TYPE_ALIASES` below.
    #
    # The `default=` deliberately stays `Value`, which is not the bound. The default is
    # what a bare, unparameterized use resolves to, and a bare use describes what the
    # host actually delivers -- always a real `list` or `dict` -- so it stays the narrow
    # type. The asymmetry is intentional, not an oversight.
    #
    # Defaulted at all because the runtime class carries no `__class_getitem__` on the
    # Python 3.8 host and therefore cannot be subscripted, so every bare use has to keep
    # working; `default=Value` (rather than `Any`) makes a bare `ListInputItem` an item
    # of an unknown `Value`, which has to be narrowed, instead of one that silently
    # accepts anything.
    #
    # Keep this justification out of the emitted block: `note()` scans the block for
    # identifiers, so prose words like `Any` would add a spurious import to the `.pyi`.
    "sublime": '_T_Value = TypeVar("_T_Value", bound=ValueLike, default=Value)',
    # `_T_Value` is the same declaration as `sublime`'s above, for the same reasons:
    # `ListInputHandler` both produces its value (`list_items`) and consumes it
    # (`description`), so its parameter is invariant, is bounded by `ValueLike` and
    # defaults to `Value`.
    #
    # `CommandInputHandler` only ever *consumes* a value -- the host passes the selected
    # item's value to `preview_`, `validate_` and `confirm_`
    # (references/python38/sublime_plugin.py:1220-1242) -- so it is contravariant.
    # Under contravariance `CommandInputHandler[Never]` is the *top* of the handler
    # lattice: every `CommandInputHandler[X]` is assignable to it. That is what lets
    # `next_input` and `Command.input` keep the reference's own bare
    # `Optional[CommandInputHandler]` return annotation, which `default=Never` resolves
    # to `CommandInputHandler[Never]`, and still accept a `TextInputHandler`
    # (a `CommandInputHandler[str]`) -- with no `Any` and no `RETURNS` override.
    #
    # Keep this justification out of the emitted block: `note()` scans the block for
    # identifiers, so prose words like `Any` would add a spurious import to the `.pyi`.
    "sublime_plugin": (
        '_T_Value = TypeVar("_T_Value", bound=ValueLike, default=Value)\n'
        '_T_Value_contra = TypeVar("_T_Value_contra", bound=ValueLike, default=Never, contravariant=True)'
    ),
}

# Replacements for a class's rendered base list, keyed by `module.Class`. The value is
# used verbatim in place of everything the reference declares between the parentheses,
# which is how a reference class is made generic (`Generic[_T]`) or is given an already
# parameterized base (`CommandInputHandler[str]`). The `@override` and inheritance
# bookkeeping keeps following the reference's own bases.
CLASS_BASES: dict[str, str] = {
    # The reference class has no bases; `Generic[_T_Value]` is what makes its `value`
    # generic. See `TYPE_VARS` above.
    "sublime.ListInputItem": "Generic[_T_Value]",
    # The reference class has no bases; the value it consumes is what parameterizes it.
    "sublime_plugin.CommandInputHandler": "Generic[_T_Value_contra]",
    # Both derive from a bare `CommandInputHandler` in the reference. A text input hands
    # the command the entered string, so its value type is fixed; a list input's is the
    # selected item's value. `BackInputHandler` deliberately keeps the reference's bare
    # base: it consumes nothing, and bare resolves to `CommandInputHandler[Never]`.
    "sublime_plugin.TextInputHandler": "CommandInputHandler[str]",
    "sublime_plugin.ListInputHandler": "CommandInputHandler[_T_Value]",
}

# `sublime_types` aliases the generator cannot take verbatim.
TYPE_ALIASES = {
    # JSON is recursive: the reference spells the containers as `List[Any]` /
    # `Dict[str, Any]`, which loses the element types. The self-reference needs no
    # quoting -- in a `.pyi` nothing is evaluated, so a forward reference resolves
    # regardless of where it appears; all four checkers accept it.
    "Value": "bool | str | int | float | list[Value] | dict[str, Value] | None",
}

# `sublime_types` aliases with no reference-side counterpart at all: like
# `EXTRA_TYPE_ALIAS_CLASSES` below, nothing keys them to the reference, so they are
# not matched against it and cannot be flagged stale. A name added here must also be
# added to `SUBLIME_TYPES_REEXPORTS` for every module that uses it. The value is the
# complete emitted block, so an entry can carry a leading comment.
#
# `Value` spells its containers `list[Value]` and `dict[str, Value]`, and both are
# invariant, so a plugin author holding a `List[str]` cannot pass it anywhere a
# `Value` is expected -- not to `Settings.set`, not to `encode_value`, and not as a
# type argument to the generic input handlers. `ValueLike` is the covariant
# companion, spelled with `Sequence` and `Mapping`, and is used for every parameter
# through which a value enters Sublime Text. Return types keep describing what comes
# back, which is always a real `list` or `dict`, so they stay `Value`.
#
# Two deliberate inaccuracies, both documented in README.md as well:
#
# 1. `Mapping` overshoots the runtime, which gates mappings on
#    `isinstance(x, dict)`: a `collections.abc.Mapping` that is not a `dict` is
#    rejected. Spelling it `dict[str, ValueLike]` would be accurate but useless,
#    since `dict` is invariant in its value parameter and `Dict[str, str]` would
#    keep failing -- which is the whole problem this alias exists to solve.
#    `Settings.update` is the one place where any `Mapping` really is accepted: it
#    is implemented in Python and iterates the mapping itself
#    (references/python38/sublime.py:3862-3883).
# 2. Whatever is passed in is delivered back as a plain `list` or `dict`, so a
#    handler parameterized on a custom sequence type type-checks and then receives
#    a `list`. That needs two type parameters to express and is documented instead.
#
# `Sequence` matches the runtime closely: sequences are duck-typed through
# `__getitem__`, so a hand-rolled `collections.abc.Sequence` is accepted, and so is
# `bytes`, which arrives back as a `list[int]`. `Region` has `__iter__`, `__len__`
# and `__contains__` but no `__getitem__` (references/python38/sublime.py:2091-2130,
# the run of dunders in a `class Region` that starts at :2061), so it fails
# `PySequence_Check` at runtime and is not a nominal `Sequence` for the checkers
# either.
#
# Keep the *emitted* comment free of the bare word `sublime` and of any name in the
# generator's import tables, for the reason `EXTRA_TYPE_ALIAS_CLASSES` records below.
EXTRA_TYPE_ALIASES = {
    "ValueLike": (
        "# What the value layer accepts on the way *in*, where `Value` describes\n"
        "# what it hands back. The containers are the covariant protocols, so a\n"
        "# `list[str]` or a `dict[str, str]` can be passed as it is.\n"
        "ValueLike: TypeAlias ="
        " bool | str | int | float | Sequence[ValueLike] | Mapping[str, ValueLike] | None"
    ),
    "CommandArgsLike": "CommandArgsLike: TypeAlias = Mapping[str, ValueLike] | None",
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

# `sublime_types` classes with no reference-side counterpart at all: nothing to key
# them to, so -- unlike every table above -- they are not matched against the
# reference and cannot be flagged stale. `generate_stubs.py` appends them, in
# order, after the reference-derived aliases in `sublime_types`.
#
# `sublime.ui_info` (references/python38/sublime.py:1170) returns a bare `dict`
# documented only as "top-level keys `system`, `theme` and `color_scheme`"; the
# official API reference and the community docs go no further than that sentence.
# The shapes below are reverse engineered from a live `sublime.ui_info()` call
# (ST build 4200, palette keys matching the ``--accent``/``--redish``/etc. color
# scheme variables), not from any documented schema, so every field is optional
# and the whole thing is a stub-only addition -- import it under
# `if TYPE_CHECKING:`.
EXTRA_TYPE_ALIAS_CLASSES = {
    "UIInfo": '''\
class UIInfoSystem(TypedDict, total=False):
    """
    The ``system`` entry of `UIInfo`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``UIInfoSystem`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    style: str
    """ ``"dark"`` or ``"light"``, mirroring the OS appearance. """

class UIInfoTheme(TypedDict, total=False):
    """
    The ``theme`` entry of `UIInfo`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``UIInfoTheme`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    value: str
    """ The configured ``theme`` setting. """
    resolved_value: str
    """ The theme file actually in effect, after auto light/dark switching. """
    style: str
    """ ``"system"`` when the theme follows the OS appearance, else unset. """

class UIInfoPalette(TypedDict, total=False):
    """
    The ``palette`` entry of `UIInfoColorScheme`: the current color scheme's
    ``--accent``/``--redish``/etc. variables, as hex color strings.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``UIInfoPalette`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    accent: str
    background: str
    foreground: str
    bluish: str
    cyanish: str
    greenish: str
    orangish: str
    pinkish: str
    purplish: str
    redish: str
    yellowish: str

class UIInfoColorScheme(TypedDict, total=False):
    """
    The ``color_scheme`` entry of `UIInfo`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``UIInfoColorScheme`` name at runtime, so it
    must be imported inside an ``if TYPE_CHECKING:`` block.
    """
    value: str
    """ The configured ``color_scheme`` setting. """
    resolved_value: str
    """ The color scheme file actually in effect, after auto light/dark switching. """
    palette: UIInfoPalette

class UIInfo(TypedDict, total=False):
    """
    The return value of `ui_info`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``UIInfo`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    system: UIInfoSystem
    theme: UIInfoTheme
    color_scheme: UIInfoColorScheme''',
    # `View.style_for_scope` (references/python38/sublime.py:3056) returns a bare
    # `dict[str, Value]`, but its docstring lists every key it can carry, in the order
    # below. `NotRequired` marks exactly the keys it flags "(only if set)".
    #
    # Two of those keys are documented with the wrong type: sublime.py:3074-3076 says
    # `"source_line": str` and `"source_file": int`, but a live
    # `view.style_for_scope(...)` call returns `'source_line': -1` and
    # `'source_file': 'Packages/Theme - Nil/Tubnil_mod.tmTheme'`. The runtime wins, as
    # it does for `QuickPanelItem.details` above.
    #
    # Keep prose in the emitted block free of the bare word `sublime`: the import
    # builder scans the generated body for module names, and a stray mention would add
    # an unused `import sublime` to `sublime_types`.
    "ScopeStyle": '''\
class ScopeStyle(TypedDict):
    """
    The return value of `View.style_for_scope`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``ScopeStyle`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    foreground: str
    """ Normalized to the six character hex form with a leading hash, e.g. ``#ff0000``. """
    selection_foreground: NotRequired[str]
    background: NotRequired[str]
    """ Normalized the same way as `foreground`. """
    bold: bool
    italic: bool
    glow: NotRequired[bool]
    underline: NotRequired[bool]
    stippled_underline: NotRequired[bool]
    squiggly_underline: NotRequired[bool]
    # The docstring swaps these two: it says `source_line: str` and `source_file: int`.
    # These are the types the runtime actually returns.
    source_line: int
    source_column: int
    source_file: str''',
    # `get_macro` (references/python38/sublime.py:1314-1320) returns a bare
    # `list[dict]`, but its docstring says each entry "will contain the keys
    # ``"command"`` and ``"args"``", so both fields are required. `CommandArgs` is
    # `dict[str, Value] | None`, so a command with no arguments is already covered
    # by its `None` arm.
    "MacroStep": '''\
class MacroStep(TypedDict):
    """
    An entry of `get_macro`'s result.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``MacroStep`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    command: str
    args: CommandArgs''',
    # `Window.layout` (references/python38/sublime.py:1679-1695) documents no keys at
    # all, only "Get/Set the group layout of the window". The shape below comes from a
    # live `window.layout()` call, which returned
    # `{'cells': [[0, 0, 1, 1]], 'cols': [0.0, 1.0], 'rows': [0.0, 1.0]}`. All three
    # keys were present in that call, so the class is total.
    "WindowLayout": '''\
class WindowLayout(TypedDict):
    """
    The return value of `Window.layout`, and the argument to `Window.set_layout`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``WindowLayout`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    cols: list[float]
    """ Normalized 0.0-1.0 division positions along the x axis. """
    rows: list[float]
    """ Normalized 0.0-1.0 division positions along the y axis. """
    cells: list[list[int]]
    """
    Each entry is a ``[col_start, row_start, col_end, row_end]`` index quadruple
    into `cols` and `rows`, describing one group's rectangle.
    """''',
    # `Window.extract_variables` (references/python38/sublime.py:2017-2038) returns
    # `dict[str, str]` and introduces its key list with "May contain:", so not one of
    # them is guaranteed and the class is uniformly `total=False` rather than marking
    # every field `NotRequired`. The key order below is the docstring's
    # (references/python38/sublime.py:2022-2034).
    "WindowVariables": '''\
class WindowVariables(TypedDict, total=False):
    """
    The return value of `Window.extract_variables`.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``WindowVariables`` name at runtime, so it must
    be imported inside an ``if TYPE_CHECKING:`` block.
    """
    packages: str
    platform: str
    file: str
    file_path: str
    file_name: str
    file_base_name: str
    file_extension: str
    folder: str
    project: str
    project_path: str
    project_name: str
    project_base_name: str
    project_extension: str''',
    # `choose_font_dialog` (references/python38/sublime.py:925-947) documents no
    # types at all, only the example `{ "font_face": "monospace" }` at
    # sublime.py:932. A live `choose_font_dialog(print)` call passed
    # `{'font_face': 'Sans', 'font_size': 10}` to the callback, which is where
    # `font_size: int` comes from. `total=False` because the same type describes
    # both directions and the input side reads both keys through `.get`
    # (sublime.py:941-943: `default.get("font_face")` and
    # `default.get("font_size")`).
    "FontOptions": '''\
class FontOptions(TypedDict, total=False):
    """
    The ``default`` argument of `choose_font_dialog`, and the value it passes to
    its callback.

    This class exists only in the stubs, for type checking: the real
    ``sublime_types`` module has no ``FontOptions`` name at runtime, so it must be
    imported inside an ``if TYPE_CHECKING:`` block.
    """
    font_face: str
    font_size: int''',
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
