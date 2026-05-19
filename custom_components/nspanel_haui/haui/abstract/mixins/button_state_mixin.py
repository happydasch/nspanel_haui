"""Button state management mixin for HAUIPage.

Tracks physical button state components and provides methods to update
their display values on the Nextion panel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..component import Component

if TYPE_CHECKING:
    from ....nspanel_haui import NSPanelHAUI
    from ..haui_event import HAUIEvent


class ButtonStateMixin:
    """Mixin for physical button state tracking on the display.

    Depends on the host class providing ``set_component_value()`` (from
    :class:`~haui.page.component_mixin.ComponentMixin`) and
    ``self._btn_state_left`` / ``self._btn_state_right`` (set in
    :class:`~haui.page.HAUIPage.__init__`).
    """

    if TYPE_CHECKING:
        # Provided by HAUIPage / HAUIBase at runtime via MRO.
        app: NSPanelHAUI
        _btn_state_left: Component | None
        _btn_state_right: Component | None

        def set_component_value(self, component: Component, value: int) -> None: ...
        def log(self, msg: str, **kwargs: str) -> None: ...

    def set_button_state_buttons(self, btn_left: Component, btn_right: Component) -> None:
        """Sets the button state buttons.

        Args:
            btn_left (tuple): Component
            btn_right (tuple): Component
        """
        self._btn_state_left = btn_left
        self._btn_state_right = btn_right

    def set_button_left_state(self, state: bool) -> None:
        """Sets the state of button left.

        Args:
            state (bool): state
        """
        if self._btn_state_left:
            self.set_component_value(self._btn_state_left, state)

    def set_button_right_state(self, state: bool) -> None:
        """Sets the state of button right.

        Args:
            state (bool): state
        """
        if self._btn_state_right:
            self.set_component_value(self._btn_state_right, state)

    def callback_button_state_buttons(
        self, event: HAUIEvent, component: Component, button_state: bool
    ) -> None:
        """Callback method for button state buttons.

        Args:
            event (HAUIEvent): Event
            component (tuple): Component
            button_state (bool): Button state
        """
        # process button state button press callback
        self.log(f"Got button state button press: {component}-{button_state}")
        if button_state != 0:
            return

        # parse json response, set button state on device
        data = event.as_json()
        if self._btn_state_left and self._btn_state_left[1] == data.get("name", ""):
            self.app.device.set_left_button_state(button_state)
        elif self._btn_state_right and self._btn_state_right[1] == data.get("name", ""):
            self.app.device.set_right_button_state(button_state)
