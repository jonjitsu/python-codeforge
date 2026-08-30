# Invoke ships no type information. This is the only module that touches its API.
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false
"""Typed facade over Invoke's decorator and collection API."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast, overload

from invoke.collection import Collection
from invoke.exceptions import Exit
from invoke.tasks import Task
from invoke.tasks import task as _invoke_task

if TYPE_CHECKING:
    from types import ModuleType

AnyTask = Callable[..., Any]

__all__ = ["AnyTask", "Exit", "build_namespace", "task"]


@overload
def task[**P, R](func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def task[**P, R](
    *,
    pre: Sequence[AnyTask] = ...,
    post: Sequence[AnyTask] = ...,
    help: Mapping[str, str] = ...,
    name: str = ...,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def task(func: Callable[..., Any] | None = None, /, **kwargs: Any) -> Any:
    """Register an Invoke task while preserving its static signature."""
    if func is not None:
        return _invoke_task(func)
    return cast("Callable[[AnyTask], AnyTask]", _invoke_task(**kwargs))


def build_namespace(root: Sequence[AnyTask], collections: Mapping[str, ModuleType]) -> Any:
    """Assemble a root namespace from root tasks and collection modules."""
    namespace = Collection()
    for entry in root:
        namespace.add_task(cast("Task[Any]", entry))
    for name, module in collections.items():
        namespace.add_collection(Collection.from_module(module), name=name)
    return namespace
