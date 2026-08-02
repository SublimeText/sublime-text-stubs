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
from collections.abc import Iterator, Sequence
from pathlib import Path

import stub_overrides as ov

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = REPO_ROOT / "references" / "python38"
ST_BUILD = "4200"

INDENT = "    "

# Decorators kept on generated declarations. Anything else is a bug in the
# generator's understanding of the reference and is reported as unresolved.
KEPT_DECORATORS = {"classmethod", "staticmethod", "property"}

# Names that must never appear bare in an annotation: strict mode's
# `reportMissingTypeArguments` rejects them.
BARE_GENERICS = {
    "dict", "list", "set", "frozenset", "tuple", "type",
    "Dict", "List", "Set", "FrozenSet", "Tuple", "Type", "Callable", "Iterator", "Iterable",
}

# Modules imported plainly when the generated body refers to them.
MODULE_IMPORTS = ["builtins", "enum", "sublime"]

# Builtins that an attribute name can shadow inside a class body, in which case
# annotations in that class have to spell them `builtins.x` (`TextChange.str`).
SHADOWABLE_BUILTINS = {
    "bool", "bytes", "complex", "dict", "float", "frozenset", "id", "int", "list",
    "object", "property", "range", "set", "slice", "str", "tuple", "type",
}

TYPING_NAMES = [
    "Any", "Callable", "Dict", "Iterable", "Iterator", "List", "Literal",
    "Optional", "Sequence", "Set", "Tuple", "Union",
]

TYPING_EXTENSIONS_NAMES = ["TypeAlias", "override"]


class Unresolved(Exception):
    """Raised for anything the generator refuses to guess at."""


class Problems:
    """Collects every unresolved name so one run reports all of them."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def add(self, where: str, what: str, hint: str) -> None:
        self.messages.append(f"{where}: {what}\n    add to stub_overrides.{hint}")

    def __bool__(self) -> bool:
        return bool(self.messages)


# --- docstrings --------------------------------------------------------------


def render_docstring(doc: str | None, indent: str) -> list[str]:
    """Render a docstring at the given indentation, or nothing if it is empty."""
    if not doc or not doc.strip():
        return []
    doc = doc.strip("\n").rstrip()
    if '"""' in doc:
        raise Unresolved("docstring contains a triple quote")
    prefix = "r" if "\\" in doc else ""
    if prefix and doc.endswith("\\"):
        raise Unresolved("docstring ends with a backslash")
    if "\n" not in doc and len(indent) + len(doc) + 8 <= 100:
        return [f'{indent}{prefix}""" {doc} """']
    lines = [f'{indent}{prefix}"""']
    for line in doc.split("\n"):
        lines.append(f"{indent}{line}".rstrip())
    lines.append(f'{indent}"""')
    return lines


def attribute_docstring(body: Sequence[ast.stmt], index: int) -> str | None:
    """The bare string literal following ``body[index]``, if there is one."""
    if index + 1 >= len(body):
        return None
    node = body[index + 1]
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
        if isinstance(node.value.value, str):
            return inspect.cleandoc(node.value.value)
    return None


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

        for module, tree in self.trees.items():
            names: set[str] = set()
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
                    if isinstance(target, ast.Attribute):
                        if isinstance(target.value, ast.Name) and target.value.id == "self":
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


# --- the generator -----------------------------------------------------------


class ModuleGenerator:
    def __init__(self, module: str, reference: Reference, problems: Problems) -> None:
        self.module: str = module
        self.ref: Reference = reference
        self.problems: Problems = problems
        self.tree: ast.Module = reference.trees[module]
        self.used_overrides: set[str] = set()
        self.referenced: set[str] = set()
        self.emitted_methods: dict[str, set[str]] = {}
        self.shadowed: set[str] = set()
        self.lines: list[str] = []

    # -- helpers

    def note(self, code: str) -> None:
        """Record the identifiers of an emitted expression, to derive imports."""
        self.referenced.update(re.findall(r"\b[A-Za-z_][A-Za-z_0-9]*\b", code))

    def key(self, *parts: str) -> str:
        return ".".join((self.module,) + parts)

    def override(self, table: dict[str, str], key: str) -> str | None:
        if key in table:
            self.used_overrides.add(key)
            return table[key]
        return None

    def check_annotation(self, annotation: str, where: str) -> str:
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
        if isinstance(default, ast.UnaryOp) and isinstance(default.operand, ast.Constant):
            if isinstance(default.operand.value, (int, float)):
                return type(default.operand.value).__name__
        if isinstance(default, ast.Attribute):
            return self.ref.enum_members.get(ast.unparse(default))
        return None

    # -- signatures

    def render_signature(self, fn: ast.FunctionDef, qualname: str, in_class: bool) -> str:
        args = fn.args
        positional = list(args.posonlyargs) + list(args.args)
        defaults: list[ast.expr | None] = [None] * (len(positional) - len(args.defaults))
        defaults += list(args.defaults)

        rendered: list[str] = []
        for index, (arg, default) in enumerate(zip(positional, defaults)):
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
        for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults):
            rendered.append(self.render_arg(qualname, arg, kw_default))
        if args.kwarg is not None:
            rendered.append("**" + self.render_arg(qualname, args.kwarg, None))

        return ", ".join(rendered)

    def resolve_arg(
        self, qualname: str, arg: ast.arg, default: ast.expr | None
    ) -> str | None:
        annotation = self.override(ov.PARAMS, f"{qualname}.{arg.arg}")
        if annotation is None and arg.annotation is not None:
            annotation = ast.unparse(arg.annotation)
        if annotation is None and default is not None:
            annotation = self.infer_from_default(default)
        if annotation is not None and is_none(default) and not accepts_none(annotation):
            # The reference writes `on_navigate: Callable[[str], None] = None`
            # in a few places; under strict checking that has to be Optional.
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
        annotation = self.override(ov.RETURNS, qualname)
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
        if needs_override:
            self.note("override")
            self.lines.append(f"{indent}@override")

        signature = self.render_signature(fn, qualname, in_class)
        returns = self.render_return(fn, qualname)
        doc = render_docstring(ast.get_docstring(fn, clean=True), indent + INDENT)
        header = f"{indent}def {fn.name}({signature}) -> {returns}:"
        if doc:
            self.lines.append(header)
            self.lines.extend(doc)
            self.lines.append(f"{indent}{INDENT}...")
        else:
            self.lines.append(header + " ...")

    def emit_assignment(self, node: ast.stmt, indent: str, doc: str | None) -> bool:
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
            text = f"{' = '.join(t.id for t in targets)} = {ast.unparse(node.value)}"
        else:
            return False

        if name == "__slots__" or is_private(name):
            return False
        self.note(text)
        self.lines.append(indent + text)
        self.lines.extend(render_docstring(doc, indent))
        return True

    def emit_instance_attributes(self, cls: ast.ClassDef, indent: str) -> bool:
        """Lift annotated ``self.x`` assignments out of ``__init__``."""
        init = next(
            (n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"),
            None,
        )
        if init is None:
            return False

        init_qualname = self.key(cls.name, "__init__")
        positional = list(init.args.posonlyargs) + list(init.args.args)
        defaults: list[ast.expr | None] = [None] * (len(positional) - len(init.args.defaults))
        defaults += list(init.args.defaults)
        parameters = list(zip(positional, defaults))
        parameters += list(zip(init.args.kwonlyargs, init.args.kw_defaults))

        parameter_types: dict[str, str] = {}
        for arg, default in parameters:
            resolved = self.resolve_arg(init_qualname, arg, default)
            if resolved is not None:
                parameter_types[arg.arg] = resolved

        emitted = False
        for index, node in enumerate(init.body):
            target: ast.expr | None = None
            value: ast.expr | None = None
            annotation: str | None = None
            if isinstance(node, ast.AnnAssign):
                target, value, annotation = node.target, node.value, ast.unparse(node.annotation)
            elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                target, value = node.targets[0], node.value
            if not isinstance(target, ast.Attribute):
                continue
            if not (isinstance(target.value, ast.Name) and target.value.id == "self"):
                continue
            name = target.attr
            if name.startswith("_"):
                continue

            qualname = self.key(cls.name, name)
            override = self.override(ov.ATTRIBUTES, qualname)
            if override is not None:
                annotation = override
            if annotation is None and isinstance(value, ast.Name):
                annotation = parameter_types.get(value.id)
            if annotation is None and isinstance(value, ast.Call):
                # `self.selection = Selection(id)` and friends
                if isinstance(value.func, ast.Name) and value.func.id in self.ref.classes[self.module]:
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
        self.lines.extend(render_docstring(ast.get_docstring(cls, clean=True), body_indent))

        self.shadowed = attribute_names(cls) & SHADOWABLE_BUILTINS
        emitted = self.emit_instance_attributes(cls, body_indent)
        emitted |= self.emit_event_handlers(cls, body_indent)

        # Only methods actually present in the stub count as overridable: the
        # reference declares `Command.run`, but the stubs deliberately do not.
        inherited: set[str] = set()
        for base in self.ref.bases.get((self.module, cls.name), []):
            inherited |= self.emitted_methods.get(base, set())
        own: set[str] = set()
        for index, node in enumerate(cls.body):
            if isinstance(node, ast.Expr):
                continue  # docstrings, handled above and alongside their assignment
            if isinstance(node, ast.FunctionDef):
                if is_private(node.name) or self.key(cls.name, node.name) in ov.SKIP_MEMBERS:
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
        if not emitted:
            self.lines.append(f"{body_indent}...")

    # -- docstring-only event handlers

    def emit_event_handlers(self, cls: ast.ClassDef, indent: str) -> bool:
        if self.module != "sublime_plugin" or cls.name not in ov.EVENT_HANDLER_CLASSES:
            return False
        doc = ast.get_docstring(cls, clean=True) or ""
        emitted = False
        for name, params, body in parse_method_directives(doc):
            returns = ov.EVENT_HANDLER_RETURNS.get(name, ov.EVENT_HANDLER_DEFAULT_RETURN)
            signature = ", ".join(["self"] + [self.qualify(p) for p in params])
            self.note(signature)
            self.note(returns)
            header = f"{indent}def {name}({signature}) -> {returns}:"
            rendered = render_docstring(body, indent + INDENT)
            if rendered:
                self.lines.append(header)
                self.lines.extend(rendered)
                self.lines.append(f"{indent}{INDENT}...")
            else:
                self.lines.append(header + " ...")
            emitted = True
        return emitted

    def qualify(self, parameter: str) -> str:
        """Qualify bare `sublime` names in a parameter lifted from a docstring."""

        def replace(match: re.Match[str]) -> str:
            name = match.group(0)
            return f"sublime.{name}" if name in self.ref.sublime_names else name

        name, _, annotation = parameter.partition(":")
        if not annotation:
            return name.strip()
        annotation = re.sub(r"\b[A-Za-z_][A-Za-z_0-9]*\b", replace, annotation.strip())
        return f"{name.strip()}: {annotation}"

    # -- module

    def separate(self, previous: str, current: str) -> None:
        """Blank line between top level items, but not between plain constants."""
        if previous and not (previous == current == "assignment"):
            self.lines.append("")

    def generate(self) -> str:
        allowlist = (
            set(ov.SUBLIME_PLUGIN_PUBLIC_API) if self.module == "sublime_plugin" else None
        )
        previous = ""
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                if allowlist is not None and node.name not in allowlist:
                    continue
                if node.name.startswith("_"):
                    continue
                self.separate(previous, "class")
                if self.module == "sublime_plugin" and node.name == "Command":
                    self.lines.append(ov.COMMAND_RUN_NOTE)
                self.emit_class(node, "")
                previous = "class"
            elif isinstance(node, ast.FunctionDef):
                if allowlist is not None or is_private(node.name):
                    continue
                if self.key(node.name) in ov.SKIP_MEMBERS:
                    continue
                self.separate(previous, "function")
                self.emit_function(node, "", self.key(node.name), in_class=False)
                previous = "function"
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                if allowlist is not None:
                    continue
                self.separate(previous, "assignment")
                if self.module == "sublime_types":
                    self.emit_type_alias(node)
                else:
                    _ = self.emit_assignment(node, "", None)
                previous = "assignment"

        body = "\n".join(self.lines).rstrip() + "\n"
        return self.render_header() + body

    def emit_type_alias(self, node: ast.stmt) -> None:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            return
        name = node.target.id
        override = self.override(ov.TYPE_ALIASES, name)
        if override is not None:
            value = override
        else:
            assert node.value is not None
            value = ast.unparse(node.value)
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                # The reference quotes every alias to keep it lazily evaluated.
                value = node.value.value
            _ = self.check_annotation(value, self.key(name))
        self.note(value)
        self.note("TypeAlias")
        self.lines.append(f"{name}: TypeAlias = {value}")

    def render_header(self) -> str:
        lines = [
            "# This file is generated by tools/generate_stubs.py -- do not edit.",
            f"# Source: references/{REFERENCE_DIR.name}/{self.module}.py"
            + f" (Sublime Text build {ST_BUILD}).",
            "",
        ]
        for module_name in MODULE_IMPORTS:
            if module_name in self.referenced and module_name != self.module:
                lines.append(f"import {module_name}")

        typing_used = [n for n in TYPING_NAMES if n in self.referenced]
        if typing_used:
            lines.append(f"from typing import {', '.join(typing_used)}")
        extensions_used = [n for n in TYPING_EXTENSIONS_NAMES if n in self.referenced]
        if extensions_used:
            lines.append(f"from typing_extensions import {', '.join(extensions_used)}")

        reexports = ov.SUBLIME_TYPES_REEXPORTS.get(self.module)
        if reexports:
            names = ", ".join(f"{n} as {n}" for n in sorted(reexports))
            lines.append(f"from sublime_types import {names}")
        if self.module == "sublime_types":
            lines.append("from sublime import CompletionItem, KindId")

        lines.append("")
        return "\n".join(lines) + "\n"


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
    raise Unresolved(f"unterminated parameter list: {signature!r}")


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
    used_overrides: set[str] = set()
    for module, package in ov.MODULES.items():
        generator = ModuleGenerator(module, reference, problems)
        outputs[REPO_ROOT / "stubs" / package / "__init__.pyi"] = generator.generate()
        used_overrides |= generator.used_overrides

    for table_name, table in (("RETURNS", ov.RETURNS), ("PARAMS", ov.PARAMS),
                              ("ATTRIBUTES", ov.ATTRIBUTES), ("TYPE_ALIASES", ov.TYPE_ALIASES)):
        for key in table:
            if key not in used_overrides:
                problems.add(f"stub_overrides.{table_name}[{key!r}]", "unused override",
                             f"{table_name} -- remove it")

    if problems:
        print("Cannot generate stubs:\n", file=sys.stderr)
        for message in problems.messages:
            print(f"  {message}", file=sys.stderr)
        return 1

    stale = False
    for path, content in outputs.items():
        relative = path.relative_to(REPO_ROOT)
        if options.check:
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
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            _ = path.write_text(content)
            print(f"wrote {relative} ({len(content.splitlines())} lines)")

    if stale:
        print("\nRun `python tools/generate_stubs.py` and commit the result.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
