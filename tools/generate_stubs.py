#!/usr/bin/env python3
"""Generate the PEP 561 stubs from the Sublime Text reference sources.

The reference sources under ``references/<python_dir>/`` are the annotated
``sublime.py``, ``sublime_plugin.py`` and ``sublime_types.py`` that ship with
Sublime Text. They already carry the complete signatures and the reStructuredText
docstrings the official API docs are built from, so the stubs are derived from
them mechanically instead of being transcribed by hand.

    python tools/generate_stubs.py            # rewrite the .pyi files
    python tools/generate_stubs.py --check    # fail if the .pyi files are stale

The ``.pyi`` files are generated artifacts and must not be edited: corrections go
into this script or into ``stub_overrides.py``.

Why not ``mypy stubgen --include-docstrings``? It drops attribute docstrings
(every enum member and every ``self.x`` documented in the reference), it cannot
know about the docstring-only event handlers, and it has no place to record the
strict-mode type corrections. All three are handled here.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import inspect
import re
import sys
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import cast, override

import stub_overrides as ov

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = REPO_ROOT / "references" / "python38"
ST_BUILD = "4200"

INDENT = "    "

# Width the generated `.pyi` files are kept within: a docstring that would exceed it
# on a single line is emitted as a block instead.
STUB_LINE_WIDTH = 100

# What a one-line docstring adds around the prose: `""" ` and ` """`.
DOCSTRING_QUOTES = 8

# Decorators kept on generated declarations. Anything else is a bug in the
# generator's understanding of the reference and is reported as unresolved.
KEPT_DECORATORS = {"classmethod", "staticmethod", "property"}

# Names that must never appear bare in an annotation: strict mode's
# `reportMissingTypeArguments` rejects them.
BARE_GENERICS = {
    "dict", "list", "set", "frozenset", "tuple", "type",
    "Dict", "List", "Set", "FrozenSet", "Tuple", "Type", "Callable", "Iterator", "Iterable",
}

# Methods `object` defines, so redeclaring one is an override even for a class with
# no base of its own; `reportImplicitOverride` wants `@override` on those too.
# `__init__` and `__new__` are left out: the rule exempts constructors.
OBJECT_METHODS = {
    "__delattr__", "__dir__", "__eq__", "__format__", "__getattribute__", "__hash__",
    "__ne__", "__reduce__", "__reduce_ex__", "__repr__", "__setattr__", "__sizeof__",
    "__str__",
}

# Methods dropped from the stubs even though the reference defines them: `object`
# already declares both as returning `str`, so a redeclaration tells a type checker
# nothing it did not know, and the reference gives them no docstring worth keeping.
REDUNDANT_OBJECT_METHODS = {"__repr__", "__str__"}

# Modules imported plainly when the generated body refers to them, split by the
# isort section they belong to. `sublime` is a third-party module here: the stubs
# describe it, they are not part of it.
STDLIB_MODULE_IMPORTS = ["builtins", "enum"]
THIRD_PARTY_MODULE_IMPORTS = ["sublime"]

# Builtins that an attribute name can shadow inside a class body, in which case
# annotations in that class have to spell them `builtins.x` (`TextChange.str`).
SHADOWABLE_BUILTINS = {
    "bool", "bytes", "complex", "dict", "float", "frozenset", "id", "int", "list",
    "object", "property", "range", "set", "slice", "str", "tuple", "type",
}

# Names still worth importing from `typing`: they have no builtin equivalent.
TYPING_NAMES = ["Any", "Literal", "TypedDict"]

# The modern home of the abstract collection types; `typing.Callable` and friends
# are deprecated aliases of these.
COLLECTIONS_ABC_NAMES = ["Callable", "Iterable", "Iterator", "Sequence"]

TYPING_EXTENSIONS_NAMES = ["TypeAlias", "deprecated", "override"]

# PEP 585: the `typing` aliases superseded by the builtin generics.
BUILTIN_GENERICS = {
    "Dict": "dict", "FrozenSet": "frozenset", "List": "list",
    "Set": "set", "Tuple": "tuple", "Type": "type",
}

# The `stub_overrides` tables that are keyed by a name from the reference, split by
# what a lookup yields. Every lookup goes through `ModuleGenerator.override` or
# `ModuleGenerator.listed`, which record the key as matched, so that `main` can
# report entries no module matched. Without that a table rots silently as the
# reference changes: an entry naming a member that has since been renamed or
# removed simply stops doing anything.
VALUE_TABLES: dict[str, dict[str, str]] = {
    "CONSTANTS": ov.CONSTANTS,
    "RETURNS": ov.RETURNS,
    "PARAMS": ov.PARAMS,
    "ATTRIBUTES": ov.ATTRIBUTES,
    "TYPE_ALIASES": ov.TYPE_ALIASES,
    "TYPE_ALIAS_CLASSES": ov.TYPE_ALIAS_CLASSES,
    "EVENT_HANDLER_RETURNS": ov.EVENT_HANDLER_RETURNS,
}
MEMBER_TABLES: dict[str, list[str]] = {
    "SKIP_MEMBERS": ov.SKIP_MEMBERS,
    "EVENT_HANDLER_CLASSES": ov.EVENT_HANDLER_CLASSES,
    "SUBLIME_PLUGIN_PUBLIC_API": ov.SUBLIME_PLUGIN_PUBLIC_API,
}


class UnresolvedError(Exception):
    """Raised for anything the generator refuses to guess at."""


class Problems:
    """Collects every unresolved name so one run reports all of them."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def add(self, where: str, what: str, hint: str) -> None:
        self.messages.append(f"{where}: {what}\n    add to stub_overrides.{hint}")

    def stale(self, where: str) -> None:
        self.messages.append(
            f"{where}: matches nothing in the reference\n    remove it from stub_overrides"
        )

    def __bool__(self) -> bool:
        return bool(self.messages)


# --- docstrings --------------------------------------------------------------


def render_docstring(doc: str | None, indent: str) -> list[str]:
    """Render a docstring at the given indentation, or nothing if it is empty."""
    if not doc or not doc.strip():
        return []
    doc = doc.strip("\n").rstrip()
    if '"""' in doc:
        raise UnresolvedError("docstring contains a triple quote")
    prefix = "r" if "\\" in doc else ""
    if prefix and doc.endswith("\\"):
        raise UnresolvedError("docstring ends with a backslash")
    if "\n" not in doc and len(indent) + len(doc) + DOCSTRING_QUOTES <= STUB_LINE_WIDTH:
        return [f'{indent}{prefix}""" {doc} """']
    lines = [f'{indent}{prefix}"""']
    lines.extend(f"{indent}{line}".rstrip() for line in doc.split("\n"))
    lines.append(f'{indent}"""')
    return lines


def attribute_docstring(body: Sequence[ast.stmt], index: int) -> str | None:
    """The bare string literal following ``body[index]``, if there is one."""
    if index + 1 >= len(body):
        return None
    node = body[index + 1]
    if (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ):
        return inspect.cleandoc(node.value.value)
    return None


# The reference marks superseded members with a `:deprecated:` field in the
# docstring, e.g. ``:deprecated: Use `get_clipboard_async` instead. :since:`4075```.
# It is always a single line; a trailing `:since:` role may share it.
DEPRECATION_MARKER = re.compile(r"^:deprecated:[^\S\n]*(.*)$", re.MULTILINE)
RST_ROLE = re.compile(r":[a-z]+:`[^`]*`")
RST_LITERAL = re.compile(r"`([^`]+)`")


def deprecation_message(doc: str | None, is_callable: Callable[[str], bool]) -> str | None:
    """The prose of the docstring's ``:deprecated:`` marker, or ``None`` if it has none.

    The reStructuredText markup is stripped so the message reads as plain prose in
    a type checker's diagnostic. A ```name``` reference is spelled ``name()`` when
    the reference knows it as a function or method, since that is what these
    messages point at.
    """
    match = DEPRECATION_MARKER.search(doc or "")
    if match is None:
        return None
    text = RST_ROLE.sub("", match.group(1))

    def literal(reference: re.Match[str]) -> str:
        name = reference.group(1)
        return f"{name}()" if is_callable(name) else name

    text = RST_LITERAL.sub(literal, text)
    return text.strip().rstrip(".").strip()


# --- reference model ---------------------------------------------------------


class Reference:
    """The parsed reference sources and the symbol tables derived from them."""

    def __init__(self, directory: Path) -> None:
        self.trees: dict[str, ast.Module] = {}
        for name in ov.MODULES:
            self.trees[name] = ast.parse((directory / f"{name}.py").read_text())

        self.enum_members: dict[str, str] = {}  # "HoverZone.TEXT" -> "HoverZone"
        self.classes: dict[str, set[str]] = {}  # module -> class names
        self.bases: dict[tuple[str, str], list[str]] = {}
        self.methods: dict[tuple[str, str], set[str]] = {}
        self.functions: dict[str, set[str]] = {}  # module -> top level function names
        self.aliases: dict[str, set[str]] = {}  # module -> annotated top level names

        for module, tree in self.trees.items():
            names: set[str] = set()
            self.functions[module] = {
                n.name for n in tree.body if isinstance(n, ast.FunctionDef)
            }
            self.aliases[module] = {
                n.target.id for n in tree.body
                if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
            }
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                names.add(node.name)
                self.bases[(module, node.name)] = [
                    b.id for b in node.bases if isinstance(b, ast.Name)
                ]
                self.methods[(module, node.name)] = {
                    m.name for m in node.body if isinstance(m, ast.FunctionDef)
                }
                if is_enum(node):
                    for member in node.body:
                        if isinstance(member, ast.Assign):
                            for target in member.targets:
                                if isinstance(target, ast.Name):
                                    self.enum_members[f"{node.name}.{target.id}"] = node.name
            self.classes[module] = names

        # Names that resolve as `sublime.X` for the synthesized event handlers.
        self.sublime_names: set[str] = set(self.classes["sublime"])
        self.sublime_names |= set(ov.SUBLIME_TYPES_REEXPORTS["sublime"])
        for node in self.trees["sublime"].body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                self.sublime_names.add(node.name)


    def knows_callable(self, module: str, class_name: str | None, name: str) -> bool:
        """Whether the reference knows ``name`` as a module function or as a method."""
        if class_name is not None and name in self.methods.get((module, class_name), set()):
            return True
        return name in self.functions.get(module, set())


def attribute_names(cls: ast.ClassDef) -> set[str]:
    """Every name the class binds as an attribute, class level or in ``__init__``."""
    names: set[str] = set()
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for statement in node.body:
                targets: list[ast.expr] = []
                if isinstance(statement, ast.AnnAssign):
                    targets = [statement.target]
                elif isinstance(statement, ast.Assign):
                    targets = list(statement.targets)
                for target in targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        names.add(target.attr)
    return names


def is_none(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def accepts_none(annotation: str) -> bool:
    """Whether ``None`` is a valid value for the annotation.

    Parsed rather than matched textually: the ``None`` in ``Callable[[str], None]``
    is a return type, not a member of the union.
    """
    try:
        node: ast.expr = ast.parse(annotation, mode="eval").body
    except SyntaxError:
        return True  # not something we can reason about; leave it alone

    def check(expr: ast.expr) -> bool:
        if isinstance(expr, ast.Constant) and expr.value is None:
            return True
        if isinstance(expr, ast.Name) and expr.id in ("Any", "object"):
            return True
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.BitOr):
            return check(expr.left) or check(expr.right)
        if isinstance(expr, ast.Subscript):
            base = ast.unparse(expr.value).rsplit(".", 1)[-1]
            if base == "Optional":
                return True
            if base == "Union":
                elements = (
                    expr.slice.elts if isinstance(expr.slice, ast.Tuple) else [expr.slice]
                )
                return any(check(element) for element in elements)
        return False

    return check(node)


class _Modernizer(ast.NodeTransformer):
    """Rewrites the `typing` aliases to PEP 604 / PEP 585 spelling."""

    @override
    def visit_Subscript(self, node: ast.Subscript) -> ast.expr:
        visited = self.generic_visit(node)
        assert isinstance(visited, ast.Subscript)
        node = visited
        base = ast.unparse(node.value).rsplit(".", 1)[-1]
        if base == "Optional":
            return union([node.slice, ast.Constant(value=None)])
        if base == "Union":
            elements = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            return union(list(elements))
        if base in BUILTIN_GENERICS and isinstance(node.value, ast.Name):
            return ast.Subscript(
                value=ast.Name(id=BUILTIN_GENERICS[base]), slice=node.slice, ctx=node.ctx
            )
        return node


def union(elements: Sequence[ast.expr]) -> ast.expr:
    """Fold the elements into a single `A | B | ...` expression."""
    result = elements[0]
    for element in elements[1:]:
        result = ast.BinOp(left=result, op=ast.BitOr(), right=element)
    return result


def modernize(annotation: str) -> str:
    """`Optional[X]` -> `X | None`, `List[X]` -> `list[X]`, and so on.

    Stub files are never executed, so they may use PEP 604 and PEP 585 syntax
    regardless of the Python version the stubs describe. All four checkers accept
    it in a `.pyi`; this is what typeshed and the hand-written third-party stub
    sets do as well.

    The original text is returned unchanged when nothing needs rewriting, so that
    annotations taken verbatim from the reference keep their own formatting.
    """
    try:
        tree: ast.expr = ast.parse(annotation, mode="eval").body
    except SyntaxError:
        return annotation
    if isinstance(tree, ast.Constant) and isinstance(tree.value, str):
        # The reference quotes forward references, and every `sublime_types` alias,
        # so that they stay lazily evaluated at runtime. A stub is never evaluated,
        # so there the quotes only get in the way (`PYI020`, `UP037`).
        return modernize(tree.value)
    original = ast.unparse(tree)  # before the transformer mutates the tree in place
    # `NodeTransformer.visit` is typed as returning `Any`.
    transformed = cast("ast.expr", _Modernizer().visit(tree))
    rewritten = ast.unparse(ast.fix_missing_locations(transformed))
    return annotation if rewritten == original else rewritten


def is_enum(node: ast.ClassDef) -> bool:
    return any("enum." in ast.unparse(base) for base in node.bases)


def is_private(name: str) -> bool:
    if name.startswith("__") and name.endswith("__"):
        return False  # dunder
    # Sublime Text marks the methods its plugin host calls into with a trailing
    # underscore (`run_`, `is_enabled_`, `description_`); they are not plugin API.
    return name.startswith("_") or name.endswith("_")


def returns_a_value(fn: ast.FunctionDef) -> bool:
    """Whether the function body ever returns or yields a value of its own.

    Nested functions are not descended into: their returns belong to them.
    """

    def scan(nodes: Sequence[ast.AST]) -> bool:
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                continue
            if isinstance(node, ast.Return) and node.value is not None:
                return True
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                return True
            if scan(list(ast.iter_child_nodes(node))):
                return True
        return False

    return scan(fn.body)


def self_assignment(node: ast.stmt) -> tuple[str, ast.expr | None, str | None] | None:
    """``(name, value, annotation)`` of a public ``self.x = ...``, or ``None`` for anything else.

    The annotation is taken verbatim; unlike for parameters (see `resolve_arg`), an
    implicit ``= None`` default does NOT make the attribute Optional. The one case
    where that matters is `TextChangeListener.buffer`, written as
    ``self.buffer: sublime.Buffer = None``
    (``references/python38/sublime_plugin.py:2249``). Both hand-written third-party
    stub sets (sublimelsp/LSP, SublimeText/sublime_lib) spell it ``Buffer | None``,
    but the plugin host only ever hands out attached instances: ``attach_buffer`` and
    ``check_text_change_listeners`` both instantiate and attach in a single
    expression, ``cls().attach(buf)`` (``references/python38/sublime_plugin.py:679``
    and ``:701``), so no listener body can observe the None. Declaring it Optional
    would force a narrowing check in every handler for a state users never see.
    ``detach()`` does not reset it either, so the attribute keeps pointing at the
    buffer it was last attached to.
    """
    if isinstance(node, ast.AnnAssign):
        target, value, annotation = node.target, node.value, ast.unparse(node.annotation)
    elif isinstance(node, ast.Assign) and len(node.targets) == 1:
        target, value, annotation = node.targets[0], node.value, None
    else:
        return None
    if not isinstance(target, ast.Attribute):
        return None
    if not (isinstance(target.value, ast.Name) and target.value.id == "self"):
        return None
    if target.attr.startswith("_"):
        return None
    return target.attr, value, annotation


def class_of(qualname: str) -> str | None:
    """The class in a ``module.Class.member`` qualname; ``None`` for a module level one."""
    _, _, rest = qualname.partition(".")
    class_name, _, _ = rest.rpartition(".")
    return class_name or None


# --- the generator -----------------------------------------------------------


class ModuleGenerator:
    def __init__(self, module: str, reference: Reference, problems: Problems) -> None:
        self.module: str = module
        self.ref: Reference = reference
        self.problems: Problems = problems
        self.tree: ast.Module = reference.trees[module]
        self.matched: set[tuple[str, str]] = set()  # (table name, key)
        self.referenced: set[str] = set()
        self.emitted_methods: dict[str, set[str]] = {}
        self.shadowed: set[str] = set()
        self.lines: list[str] = []

    # -- helpers

    def blank(self) -> None:
        """A separating blank line, never two in a row and never a leading one."""
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    def note(self, code: str) -> None:
        """Record the identifiers of an emitted expression, to derive imports."""
        self.referenced.update(re.findall(r"\b[A-Za-z_][A-Za-z_0-9]*\b", code))

    def key(self, *parts: str) -> str:
        return ".".join((self.module, *parts))

    def override(self, table: str, key: str) -> str | None:
        """The entry `key` has in `VALUE_TABLES[table]`, recorded as matched."""
        value = VALUE_TABLES[table].get(key)
        if value is not None:
            self.matched.add((table, key))
        return value

    def listed(self, table: str, key: str) -> bool:
        """Whether `MEMBER_TABLES[table]` names `key`, recorded as matched."""
        if key not in MEMBER_TABLES[table]:
            return False
        self.matched.add((table, key))
        return True

    def check_annotation(self, annotation: str, where: str) -> str:
        annotation = modernize(annotation)
        for name in self.shadowed:
            annotation = re.sub(rf"(?<!\.)\b{name}\b", f"builtins.{name}", annotation)
        self.note(annotation)
        for name in BARE_GENERICS:
            if re.search(rf"\b{name}\b(?!\s*\[)", annotation):
                self.problems.add(
                    where,
                    f"bare generic {name!r} in {annotation!r}",
                    "RETURNS / PARAMS with type arguments",
                )
        return annotation

    def infer_from_default(self, default: ast.expr) -> str | None:
        """The type of a parameter that is only described by its default value."""
        if isinstance(default, ast.Constant):
            value = default.value
            if value is None:
                return None  # `= None` alone says nothing about the type
            return type(value).__name__
        if (
            isinstance(default, ast.UnaryOp)
            and isinstance(default.operand, ast.Constant)
            and isinstance(default.operand.value, (int, float))
        ):
            return type(default.operand.value).__name__
        if isinstance(default, ast.Attribute):
            return self.ref.enum_members.get(ast.unparse(default))
        return None

    # -- signatures

    def render_signature(self, fn: ast.FunctionDef, qualname: str, in_class: bool) -> list[str]:
        """The rendered parameters, one per element, for `emit_def` to lay out."""
        args = fn.args
        positional = list(args.posonlyargs) + list(args.args)
        defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults))
        defaults += list(args.defaults)

        rendered: list[str] = []
        for index, (arg, default) in enumerate(zip(positional, defaults, strict=True)):
            if index == 0 and in_class and arg.arg in ("self", "cls"):
                rendered.append(arg.arg)
                continue
            rendered.append(self.render_arg(qualname, arg, default))
            if index + 1 == len(args.posonlyargs):
                rendered.append("/")

        if args.vararg is not None:
            rendered.append("*" + self.render_arg(qualname, args.vararg, None))
        elif args.kwonlyargs:
            rendered.append("*")
        for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            rendered.append(self.render_arg(qualname, arg, kw_default))
        if args.kwarg is not None:
            rendered.append("**" + self.render_arg(qualname, args.kwarg, None))

        return rendered

    def resolve_arg(
        self, qualname: str, arg: ast.arg, default: ast.expr | None
    ) -> str | None:
        annotation = self.override("PARAMS", f"{qualname}.{arg.arg}")
        if annotation is None and arg.annotation is not None:
            annotation = ast.unparse(arg.annotation)
        if annotation is None and default is not None:
            annotation = self.infer_from_default(default)
        if annotation is not None and is_none(default) and not accepts_none(annotation):
            # The reference writes `on_navigate: Callable[[str], None] = None`
            # in a few places; under strict checking that has to be Optional.
            # This applies to parameters only -- annotated `self.x: T = None`
            # attributes keep their annotation verbatim, see
            # `emit_instance_attributes`.
            annotation = f"Optional[{annotation}]"
        return annotation

    def render_arg(self, qualname: str, arg: ast.arg, default: ast.expr | None) -> str:
        where = f"{qualname}({arg.arg})"
        annotation = self.resolve_arg(qualname, arg, default)
        if annotation is None:
            self.problems.add(where, "parameter type cannot be inferred", "PARAMS")
            annotation = "Any"
        annotation = self.check_annotation(annotation, where)
        suffix = " = ..." if default is not None else ""
        return f"{arg.arg}: {annotation}{suffix}"

    def render_return(self, fn: ast.FunctionDef, qualname: str) -> str:
        annotation = self.override("RETURNS", qualname)
        if annotation is None and fn.returns is not None:
            annotation = ast.unparse(fn.returns)
        if annotation is None:
            if returns_a_value(fn):
                self.problems.add(qualname, "return type cannot be inferred", "RETURNS")
                annotation = "Any"
            else:
                annotation = "None"
        return self.check_annotation(annotation, qualname)

    # -- emission

    def emit_function(
        self,
        fn: ast.FunctionDef,
        indent: str,
        qualname: str,
        in_class: bool,
        needs_override: bool = False,
    ) -> None:
        for decorator in fn.decorator_list:
            name = ast.unparse(decorator)
            if name not in KEPT_DECORATORS:
                self.problems.add(qualname, f"unsupported decorator @{name}", "the generator")
                continue
            self.lines.append(f"{indent}@{name}")
        # typeshed's convention: below `@classmethod` / `@staticmethod` / `@property`,
        # above `@override`.
        self.emit_deprecation(fn, indent, qualname)
        if needs_override:
            self.note("override")
            self.lines.append(f"{indent}@override")

        self.emit_def(
            indent,
            fn.name,
            self.render_signature(fn, qualname, in_class),
            self.render_return(fn, qualname),
            render_docstring(ast.get_docstring(fn, clean=True), indent + INDENT),
        )

    def emit_def(
        self, indent: str, name: str, params: list[str], returns: str, doc: list[str]
    ) -> None:
        """Emit a `def` and its body, wrapping the signature if it does not fit."""
        header = f"{indent}def {name}({', '.join(params)}) -> {returns}:"
        closing = f"{indent}) -> {returns}:"
        # A long return annotation cannot be broken up, so when it overflows on its
        # own, wrapping a lone `self` onto a line of its own only adds noise.
        wrapped = len(header) > STUB_LINE_WIDTH and (
            len(closing) <= STUB_LINE_WIDTH or len(params) > 1
        )
        if wrapped:
            # One parameter per line, as black would wrap it. Splitting the joined
            # signature instead is not an option: `Callable[[str, int], None]`
            # contains a comma of its own.
            self.lines.append(f"{indent}def {name}(")
            self.lines.extend(f"{indent}{INDENT}{param}," for param in params)
            self.lines.append(closing)
        else:
            self.lines.append(header)

        # A docstring is already a complete body; only an undocumented declaration
        # needs the `...` to stand in for one. Without it the closing quotes are the
        # only thing separating one declaration from the next, hence the blank line.
        if doc:
            self.lines.extend(doc)
            self.blank()
        elif wrapped:
            self.lines.append(f"{indent}{INDENT}...")
        else:
            self.lines[-1] += " ..."

    def emit_deprecation(self, fn: ast.FunctionDef, indent: str, qualname: str) -> None:
        """Turn the docstring's ``:deprecated:`` marker into a `@deprecated` decorator."""
        class_name = class_of(qualname)
        message = deprecation_message(
            ast.get_docstring(fn, clean=True),
            lambda name: self.ref.knows_callable(self.module, class_name, name),
        )
        if message is None:
            return
        if not message or '"' in message:
            self.problems.add(
                qualname,
                f"`:deprecated:` marker yields no usable message: {message!r}",
                "the generator -- teach it this marker's shape",
            )
            return
        self.note("deprecated")
        self.lines.append(f'{indent}@deprecated("{message}")')

    def emit_assignment(
        self, node: ast.stmt, indent: str, doc: str | None, *, module_level: bool = False
    ) -> bool:
        """Emit a class or module level assignment verbatim. False if skipped."""
        if isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name):
                return False
            name = node.target.id
            text = f"{name}: {ast.unparse(node.annotation)}"
            if node.value is not None:
                text += f" = {ast.unparse(node.value)}"
        elif isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
            if len(targets) != len(node.targets):
                return False  # e.g. `sys.stdout = _LogWriter()`
            name = targets[0].id
            # A bare literal leaves a module constant's type to inference, which
            # `PYI052` flags in a stub; a `CONSTANTS` entry supplies the annotation
            # it asks for while keeping the value in view.
            annotation = self.override("CONSTANTS", self.key(name)) if module_level else None
            declared = f": {self.check_annotation(annotation, self.key(name))}" if annotation else ""
            text = f"{' = '.join(t.id for t in targets)}{declared} = {ast.unparse(node.value)}"
        else:
            return False

        if name == "__slots__" or is_private(name):
            return False
        self.note(text)
        self.lines.append(indent + text)
        self.lines.extend(render_docstring(doc, indent))
        return True

    def init_parameter_types(self, init: ast.FunctionDef, qualname: str) -> dict[str, str]:
        """The resolved type of every ``__init__`` parameter, keyed by parameter name."""
        positional = list(init.args.posonlyargs) + list(init.args.args)
        defaults: list[ast.expr | None] = [None] * (len(positional) - len(init.args.defaults))
        defaults += list(init.args.defaults)
        parameters = list(zip(positional, defaults, strict=True))
        parameters += list(zip(init.args.kwonlyargs, init.args.kw_defaults, strict=True))

        types: dict[str, str] = {}
        for arg, default in parameters:
            resolved = self.resolve_arg(qualname, arg, default)
            if resolved is not None:
                types[arg.arg] = resolved
        return types

    def emit_instance_attributes(self, cls: ast.ClassDef, indent: str) -> bool:
        """Lift annotated ``self.x`` assignments out of ``__init__``."""
        init = next(
            (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"),
            None,
        )
        if init is None:
            return False

        parameter_types = self.init_parameter_types(init, self.key(cls.name, "__init__"))

        emitted = False
        for index, node in enumerate(init.body):
            assignment = self_assignment(node)
            if assignment is None:
                continue
            name, value, annotation = assignment

            qualname = self.key(cls.name, name)
            override = self.override("ATTRIBUTES", qualname)
            if override is not None:
                annotation = override
            if annotation is None and isinstance(value, ast.Name):
                annotation = parameter_types.get(value.id)
            # `self.selection = Selection(id)` and friends
            if (
                annotation is None
                and isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id in self.ref.classes[self.module]
            ):
                annotation = value.func.id
            if annotation is None:
                self.problems.add(qualname, "attribute type cannot be inferred", "ATTRIBUTES")
                annotation = "Any"
            annotation = self.check_annotation(annotation, qualname)
            self.lines.append(f"{indent}{name}: {annotation}")
            self.lines.extend(render_docstring(attribute_docstring(init.body, index), indent))
            emitted = True
        return emitted

    def emit_class(self, cls: ast.ClassDef, indent: str) -> None:
        bases = [ast.unparse(b) for b in cls.bases]
        bases += [f"{kw.arg}={ast.unparse(kw.value)}" for kw in cls.keywords]
        header = f"{indent}class {cls.name}"
        header += f"({', '.join(bases)}):" if bases else ":"
        self.note(" ".join(bases))
        self.lines.append(header)

        body_indent = indent + INDENT
        doc = render_docstring(ast.get_docstring(cls, clean=True), body_indent)
        self.lines.extend(doc)

        self.shadowed = attribute_names(cls) & SHADOWABLE_BUILTINS
        emitted = self.emit_instance_attributes(cls, body_indent)
        emitted |= self.emit_event_handlers(cls, body_indent)

        # Only methods actually present in the stub count as overridable: the
        # reference declares `Command.run`, but the stubs deliberately do not.
        # Everything inherits from `object`, whether the reference says so or not.
        inherited: set[str] = set(OBJECT_METHODS)
        for base in self.ref.bases.get((self.module, cls.name), []):
            inherited |= self.emitted_methods.get(base, set())
        own: set[str] = set()
        for index, node in enumerate(cls.body):
            if isinstance(node, ast.Expr):
                continue  # docstrings, handled above and alongside their assignment
            if isinstance(node, ast.FunctionDef):
                if (
                    is_private(node.name)
                    or node.name in REDUNDANT_OBJECT_METHODS
                    or self.listed("SKIP_MEMBERS", self.key(cls.name, node.name))
                ):
                    continue
                self.emit_function(
                    node,
                    body_indent,
                    self.key(cls.name, node.name),
                    in_class=True,
                    needs_override=node.name in inherited and node.name != "__init__",
                )
                own.add(node.name)
                emitted = True
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                emitted |= self.emit_assignment(node, body_indent, attribute_docstring(cls.body, index))

        self.emitted_methods[cls.name] = inherited | own
        self.shadowed = set()
        if not emitted and not doc:
            self.lines.append(f"{body_indent}...")

    # -- docstring-only event handlers

    def emit_event_handlers(self, cls: ast.ClassDef, indent: str) -> bool:
        if self.module != "sublime_plugin" or not self.listed("EVENT_HANDLER_CLASSES", cls.name):
            return False
        doc = ast.get_docstring(cls, clean=True) or ""
        emitted = False
        for name, params, body in parse_method_directives(doc):
            # Keyed by the bare handler name: the same handler is declared by more
            # than one of the listener classes and always returns the same thing.
            override = self.override("EVENT_HANDLER_RETURNS", name)
            returns = modernize(override or ov.EVENT_HANDLER_DEFAULT_RETURN)
            qualname = self.key(cls.name, name)
            signature = ["self"] + [self.qualify(qualname, p) for p in params]
            self.note(", ".join(signature))
            self.note(returns)
            self.emit_def(indent, name, signature, returns, render_docstring(body, indent + INDENT))
            emitted = True
        return emitted

    def qualify(self, qualname: str, parameter: str) -> str:
        """Qualify bare `sublime` names in a parameter lifted from a docstring.

        A `PARAMS` entry takes precedence, so that a wrong type in the directive
        can be corrected the same way as one in a real signature.
        """

        def replace(match: re.Match[str]) -> str:
            name = match.group(0)
            return f"sublime.{name}" if name in self.ref.sublime_names else name

        name, _, annotation = parameter.partition(":")
        override = self.override("PARAMS", f"{qualname}.{name.strip()}")
        if override is not None:
            return f"{name.strip()}: {modernize(override)}"
        if not annotation:
            return name.strip()
        annotation = re.sub(r"\b[A-Za-z_][A-Za-z_0-9]*\b", replace, annotation.strip())
        return f"{name.strip()}: {modernize(annotation)}"

    # -- module

    def separate(self, previous: str, current: str) -> None:
        """Blank line between top level items, but not between plain constants."""
        if previous and not (previous == current == "assignment"):
            self.blank()

    def generate(self) -> str:
        # `sublime_plugin` is emitted from an allowlist rather than by dropping
        # private names: most of the module is plugin host machinery.
        allowlisted = self.module == "sublime_plugin"
        previous = ""
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                if allowlisted and not self.listed("SUBLIME_PLUGIN_PUBLIC_API", node.name):
                    continue
                if node.name.startswith("_"):
                    continue
                self.separate(previous, "class")
                if self.module == "sublime_plugin" and node.name == "Command":
                    self.lines.append(ov.COMMAND_RUN_NOTE)
                self.emit_class(node, "")
                previous = "class"
            elif isinstance(node, ast.FunctionDef):
                if allowlisted or is_private(node.name):
                    continue
                if self.listed("SKIP_MEMBERS", self.key(node.name)):
                    continue
                self.separate(previous, "function")
                self.emit_function(node, "", self.key(node.name), in_class=False)
                previous = "function"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                if allowlisted:
                    continue
                if self.module == "sublime_types":
                    current = "class" if self.aliases_to_class(node) else "assignment"
                    self.separate(previous, current)
                    self.emit_type_alias(node)
                    previous = current
                else:
                    self.separate(previous, "assignment")
                    _ = self.emit_assignment(node, "", None, module_level=True)
                    previous = "assignment"

        body = "\n".join(self.lines).rstrip() + "\n"
        return self.render_header() + body

    def aliases_to_class(self, node: ast.stmt) -> bool:
        """Whether `node` is a module-level alias replaced by a `TYPE_ALIAS_CLASSES` entry."""
        return (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id in ov.TYPE_ALIAS_CLASSES
        )

    def emit_type_alias(self, node: ast.stmt) -> None:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            return
        name = node.target.id
        class_override = self.override("TYPE_ALIAS_CLASSES", name)
        if class_override is not None:
            self.note(class_override)
            self.lines.append(class_override)
            return
        override = self.override("TYPE_ALIASES", name)
        if override is not None:
            value = modernize(override)
        else:
            assert node.value is not None
            # `modernize` unquotes the string the reference wraps every alias in.
            value = self.check_annotation(ast.unparse(node.value), self.key(name))
        self.note(value)
        self.note("TypeAlias")
        self.lines.append(f"{name}: TypeAlias = {value}")

    def render_header(self) -> str:
        lines = [
            "# This file is generated by tools/generate_stubs.py -- do not edit.",
            (
                f"# Source: references/{REFERENCE_DIR.name}/{self.module}.py"
                f" (Sublime Text build {ST_BUILD})."
            ),
            "",
        ]
        # No `from __future__ import annotations`: it is a no-op in a stub, which a
        # type checker always reads with postponed annotations, so the PEP 604 / 585
        # syntax below needs nothing to enable it.
        stdlib = self.plain_imports(STDLIB_MODULE_IMPORTS)
        abc_used = [n for n in COLLECTIONS_ABC_NAMES if n in self.referenced]
        if abc_used:
            stdlib.append(f"from collections.abc import {', '.join(abc_used)}")
        typing_used = [n for n in TYPING_NAMES if n in self.referenced]
        if typing_used:
            stdlib.append(f"from typing import {', '.join(typing_used)}")

        third_party = self.plain_imports(THIRD_PARTY_MODULE_IMPORTS)
        if self.module == "sublime_types":
            third_party.append("from sublime import CompletionItem, KindId")
        reexports = ov.SUBLIME_TYPES_REEXPORTS.get(self.module)
        # One name per line: that is how isort spells `X as X` re-exports, and the
        # single line they used to share ran well past the stub line width.
        third_party.extend(f"from sublime_types import {n} as {n}" for n in sorted(reexports or []))
        extensions_used = [n for n in TYPING_EXTENSIONS_NAMES if n in self.referenced]
        if extensions_used:
            third_party.append(f"from typing_extensions import {', '.join(extensions_used)}")

        for section in (stdlib, third_party):
            if section:
                lines.extend(section)
                lines.append("")
        return "\n".join(lines) + "\n"

    def plain_imports(self, modules: Sequence[str]) -> list[str]:
        """`import x` for each of `modules` the generated body refers to."""
        return [
            f"import {module}"
            for module in modules
            if module in self.referenced and module != self.module
        ]


# --- `.. method::` directives ------------------------------------------------

DIRECTIVE = re.compile(r"^\.\. method:: (\w+)\((.*)$")


def parse_method_directives(doc: str) -> Iterator[tuple[str, list[str], str]]:
    """Yield ``(name, parameters, docstring)`` for each `.. method::` directive."""
    lines = doc.split("\n")
    index = 0
    while index < len(lines):
        match = DIRECTIVE.match(lines[index].strip())
        if match is None:
            index += 1
            continue
        name = match.group(1)
        signature = match.group(2)
        while signature.rstrip().endswith("\\"):
            index += 1
            signature = signature.rstrip()[:-1] + lines[index].strip()
        # Drop everything from the closing parenthesis on: the directives spell
        # return types in prose-flavoured pseudo-Python (`-> (str, CommandArgs)`),
        # so they come from the override table instead.
        signature = signature[: matching_parenthesis(signature)]

        index += 1
        body: list[str] = []
        while index < len(lines):
            line = lines[index]
            if line.strip() and not line.startswith(" "):
                break
            if DIRECTIVE.match(line.strip()):
                break
            body.append(line)
            index += 1

        yield name, split_parameters(signature), inspect.cleandoc("\n".join(body))


def matching_parenthesis(signature: str) -> int:
    """Index of the parenthesis closing the parameter list."""
    depth = 0
    for index, char in enumerate(signature):
        if char in "[(":
            depth += 1
        elif char in "])":
            if depth == 0:
                return index
            depth -= 1
    raise UnresolvedError(f"unterminated parameter list: {signature!r}")


def split_parameters(signature: str) -> list[str]:
    """Split a parameter list on top level commas."""
    parameters: list[str] = []
    depth = 0
    current = ""
    for char in signature:
        if char in "[(":
            depth += 1
        elif char in "])":
            depth -= 1
        if char == "," and depth == 0:
            parameters.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parameters.append(current.strip())
    return [normalize_generics(p) for p in parameters]


def normalize_generics(text: str) -> str:
    for old, new in (("List[", "list["), ("Dict[", "dict["), ("Tuple[", "tuple[")):
        text = text.replace(old, new)
    return text


# --- entry point -------------------------------------------------------------


class Options(argparse.Namespace):
    """Typed view of the parsed arguments; `argparse.Namespace` is otherwise untyped."""

    check: bool = False


def write_stubs(outputs: dict[Path, str]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(content)
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(content.splitlines())} lines)")


def report_drift(outputs: dict[Path, str]) -> bool:
    """Diff the generated content against the committed stubs; True if any is stale."""
    stale = False
    for path, content in outputs.items():
        relative = path.relative_to(REPO_ROOT)
        current = path.read_text() if path.exists() else ""
        if current != content:
            stale = True
            print(f"{relative} is out of date:")
            print("".join(difflib.unified_diff(
                current.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"{relative} (committed)",
                tofile=f"{relative} (generated)",
            )))
    return stale


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    _ = parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit non-zero if the committed stubs are out of date",
    )
    options = parser.parse_args(argv, namespace=Options())

    problems = Problems()
    reference = Reference(REFERENCE_DIR)

    outputs: dict[Path, str] = {}
    matched: set[tuple[str, str]] = set()
    for module, package in ov.MODULES.items():
        generator = ModuleGenerator(module, reference, problems)
        outputs[REPO_ROOT / "stubs" / package / "__init__.pyi"] = generator.generate()
        matched |= generator.matched

    for table_name, table in (*VALUE_TABLES.items(), *MEMBER_TABLES.items()):
        for key in table:
            if (table_name, key) not in matched:
                problems.stale(f"stub_overrides.{table_name}[{key!r}]")

    # The re-export lists are emitted verbatim rather than looked up, so they are
    # checked against the reference directly.
    for module, names in ov.SUBLIME_TYPES_REEXPORTS.items():
        for name in names:
            if name not in reference.aliases["sublime_types"]:
                problems.stale(f"stub_overrides.SUBLIME_TYPES_REEXPORTS[{module!r}][{name!r}]")

    if problems:
        print("Cannot generate stubs:\n", file=sys.stderr)
        for message in problems.messages:
            print(f"  {message}", file=sys.stderr)
        return 1

    if options.check:
        if report_drift(outputs):
            print("\nRun `python tools/generate_stubs.py` and commit the result.", file=sys.stderr)
            return 1
    else:
        write_stubs(outputs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
