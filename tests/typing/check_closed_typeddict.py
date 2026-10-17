# mypy 2.4.0 does not implement PEP 728 and rejects every `TypedDict` as a `ValueLike`,
# closed or not. The other three checkers do, so they alone carry this file.
# mypy: disable-error-code="arg-type, type-var"
"""Sample consumer code passing a `TypedDict` where a `ValueLike` is accepted.

Not executed. Its only purpose is to give the type checkers something concrete to
verify the stubs against, since `sublime` cannot be imported outside Sublime Text.
"""

from typing import TYPE_CHECKING

import sublime

if TYPE_CHECKING:
    # `typing.TypedDict` accepts `closed=True` only from Python 3.15 on, so a plugin
    # targeting the 3.14 host takes it from `typing_extensions`. Defining the class
    # here too spares the plugin a runtime dependency on that package; values of the
    # type are plain `dict` literals either way.
    from typing_extensions import TypedDict

    class Entry(TypedDict, closed=True):
        # An open `TypedDict` may carry further keys of any type, so it is not a
        # `Mapping[str, ValueLike]`; `closed=True` rules those out.
        name: str
        tags: list[str]


def store_entry(settings: sublime.Settings, entry: Entry) -> None:
    settings.set("entry", entry)


def entry_item(entry: Entry) -> sublime.ListInputItem[Entry]:
    return sublime.ListInputItem(entry["name"], entry)
