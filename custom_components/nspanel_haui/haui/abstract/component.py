"""Nextion display component types.

Provides ``Component`` (a typed NamedTuple with ``.id`` and ``.name``)
and ``ComponentRegistry`` for composing page-level component declarations.
"""

from __future__ import annotations

from typing import NamedTuple


class Component(NamedTuple):
    """A Nextion display component identified by numeric page ID and string widget name.

    Attributes:
        id: The numeric component identifier on the Nextion page.
        name: The Nextion internal name of the component (e.g. ``"tTitle"``).
    """

    id: int
    name: str


class ComponentRegistry:
    """A registry of Component objects for a page.

    Use ``.merge()`` to extend a parent page's component set with
    overrides or additions.

    Example::

        class HAUIPage:
            components: ClassVar[ComponentRegistry] = ComponentRegistry(
                fnc_left_pri=Component(3, "bFncLPri"),
                fnc_left_sec=Component(4, "bFncLSec"),
                fnc_right_pri=Component(5, "bFncRPri"),
                fnc_right_sec=Component(6, "bFncRSec"),
            )

        class CoverPage(HAUIPage):
            components = HAUIPage.components.merge(
                title=Component(2, "tTitle"),
                btn_up=Component(7, "bUp"),
            )
    """

    def __init__(self, **kwargs: Component) -> None:
        self._components: dict[str, Component] = kwargs

    def values(self) -> list[Component]:
        """Return all Component values in insertion order."""
        return list(self._components.values())

    def __getattr__(self, name: str) -> Component:
        try:
            return self._components[name]
        except KeyError:
            raise AttributeError(f"{type(self).__name__!r} has no component {name!r}") from None

    def merge(self, **kwargs: Component) -> ComponentRegistry:
        """Return a new registry with overrides/additions.

        Args:
            **kwargs: Component fields to merge.

        Returns:
            A new ComponentRegistry combining existing and new fields.
        """
        merged = {**self._components, **kwargs}
        return ComponentRegistry(**merged)
