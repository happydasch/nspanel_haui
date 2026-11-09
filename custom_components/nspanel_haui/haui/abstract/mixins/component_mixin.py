"""Component color, text, and visibility mixin for HAUIPage.

Provides display command helpers that wrap send_cmd() with Nextion
component-specific commands for setting colors, visibility, touch
state, and password mode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..component import Component

if TYPE_CHECKING:
    from ....hub.app import NSPanelHAUI

from ...utils.color import parse_color_value


class ComponentMixin:
    """Mixin that adds component color/text/visibility helpers.

    Depends on the host class providing ``send_cmd(str)`` (from
    :class:`~haui.abstract.base.HAUIBase`).
    """

    if TYPE_CHECKING:
        # Provided by HAUIBase / HAUIPage at runtime via MRO.
        app: NSPanelHAUI

        def send_cmd(self, cmd: str) -> None: ...
        def log(self, msg: str, **kwargs: Any) -> None: ...
        def render_template(self, template: str, parse_icons: bool = True) -> str: ...

    def parse_color(self, color: int | str | list | tuple) -> int:
        """Parses the given color.

        Args:
            color (int|str|list|tuple): Color

        Returns:
            int: Color
        """
        return parse_color_value(color)

    def set_component_text_color(
        self, component: Component, color: int | str | list | tuple
    ) -> None:
        """Sets the text color of the given component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        self.send_cmd(f"{component.name}.pco={component_color}")

    def set_component_text_color_pressed(
        self, component: Component, color: int | str | list | tuple
    ) -> None:
        """Sets the text color pressed of the given component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        self.send_cmd(f"{component.name}.pco2={component_color}")

    def set_component_back_color(
        self, component: Component, color: int | str | list | tuple
    ) -> None:
        """Sets the back color of the component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        self.send_cmd(f"{component.name}.bco={component_color}")

    def set_component_back_color_pressed(
        self, component: Component, color: int | str | list | tuple
    ) -> None:
        """Sets the back color pressed of the component.

        Args:
            component (tuple): Component
            color (int|str|list|tuple): Color
        """
        component_color = self.parse_color(color)
        self.send_cmd(f"{component.name}.bco2={component_color}")

    def set_component_touch(self, component: Component, state: bool) -> None:
        """Sets a components touch events.

        Args:
            component (tuple): Component
            state (bool): Should the component recieve touch events
        """
        self.send_cmd(f"tsw {component.name},{int(state)}")

    def show_component(self, component: Component) -> None:
        """Shows the component.

        Args:
            component (tuple): Component
        """
        self.send_cmd(f"vis {component.name},1")

    def hide_component(self, component: Component) -> None:
        """Hides the component.

        Args:
            component (tuple): Component
        """
        self.send_cmd(f"vis {component.name},0")
