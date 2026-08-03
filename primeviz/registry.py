"""The representation registry.

A representation is two things bolted together:

  render(iset, subfig, ctx)   draw this integer set into one column of a figure
  stats(iset, ctx) -> dict    scalar summaries of the same encoding

The render is what you look at. The stats are what stops you fooling yourself:
the harness recomputes them over an ensemble of null draws and reports a
z-score, so "I can see something" has to survive "the null sees it too".

`headline` names the one statistic the verdict is based on. `mechanism` is only
printed once a representation actually survives -- it is the explanation the
harness owes you, not a hypothesis it starts from.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Callable

REGISTRY: dict[str, "Representation"] = {}


@dataclass
class Representation:
    key: str
    title: str
    question: str  # what this encoding is asking of the integers
    render: Callable
    stats: Callable | None = None
    headline: str | None = None
    iteration: int = 1
    panel_size: tuple[float, float] = (5.0, 5.2)
    mechanism: str = ""
    notes: str = ""
    tags: tuple = ()

    def __post_init__(self):
        if self.key in REGISTRY:
            raise ValueError(f"duplicate representation key: {self.key}")
        REGISTRY[self.key] = self


def representation(**kw):
    """Decorate a render function to register it.

    The decorated function is the renderer; `stats=` is passed in kw.
    """

    def deco(fn):
        Representation(render=fn, **kw)
        return fn

    return deco


def load_all() -> None:
    from . import reps

    for mod in pkgutil.iter_modules(reps.__path__):
        importlib.import_module(f"{reps.__name__}.{mod.name}")


def selected(iteration_max: int | None = None, only: list[str] | None = None):
    load_all()
    items = sorted(REGISTRY.values(), key=lambda r: (r.iteration, r.key))
    if only:
        items = [r for r in items if r.key in only]
    if iteration_max is not None:
        items = [r for r in items if r.iteration <= iteration_max]
    return items
