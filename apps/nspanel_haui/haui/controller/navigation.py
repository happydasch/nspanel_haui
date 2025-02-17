import threading
from datetime import datetime

from ..mapping.const import ESP_EVENT
from ..helper.page import get_page_id_for_panel, get_page_class_for_panel
from ..abstract.part import HAUIPart
from ..abstract.event import HAUIEvent


class HAUINavigationController(HAUIPart):
    """Navigation Controller

    Provides the whole navigation functionality. Implemented as a controller
    so full app access is possible when navigating.
    """

    def __init__(self, app, config):
        """Initialize for navigation controlller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f"Creating Navigation Controller with config: {config}")
        self.page = None
        self.panel = None  # current panel config
        self.panel_kwargs = {}  # current panel kwargs
        self._current_nav = None  # current nav panel config
        self._current_nav_kwargs = {}  # current nav panel kwargs
        self._ids = None  # ids of nav panels
        self._home_panel = None  # home panel config
        self._sleep_panel = None  # sleep panel config
        self._sleep_panel_active = False  # sleep panel state
        self._wakeup_panel = None  # wakeup panel config
        self._page_timeout = None  # Timer for switching pages
        self._close_timeout = None  # Timer for panel auto close
        self._stack = []  # stack for non-nav panels
        self._snapshot = None  # snapshot for navigation

    # part

    def start_part(self):
        """Starts the part."""
        # get panels
        all_panels = self.app.config.get_panels()
        nav_panels = self.app.config.get_panels(filter_nav_panel=True)
        # store all navigateable panel ids
        self._ids = [panel.id for panel in nav_panels]
        # set special panels
        for panel in all_panels:
            if panel.is_home_panel():
                if self._home_panel is None:
                    self.log(f"Home panel using panel {panel.id}")
                    self._home_panel = panel
                else:
                    self.log("Multiple home panels defined in config, using first")
            if panel.is_sleep_panel():
                if self._sleep_panel is None:
                    self.log(f"Sleep panel using panel {panel.id}")
                    self._sleep_panel = panel
                else:
                    self.log("Multiple sleep panels defined in config, using first")
            if panel.is_wakeup_panel():
                if self._wakeup_panel is None:
                    self.log(f"Wakeup panel using panel {panel.id}")
                    self._wakeup_panel = panel
                else:
                    self.log("Multiple wakeup panels defined in config, using first")
        # set home panel
        if self._home_panel is None and len(self._ids) > 0:
            self.log(f"Using first panel {self._ids[0]} as home panel")
            self._home_panel = self._ids[0]
        # log start
        self.log(
            f'Panels used for navigation: {", ".join([str(x) for x in self._ids])}'
        )

    # public methods

    def goto_page(self, page_id):
        """Goto page method.

        Args:
            page_id (str): Page name or id
        """
        self.log(f"Goto page: {page_id}")
        self.send_mqtt("goto_page", str(page_id))

    def unset_page(self):
        """Unsets the currently set page."""
        if self.page is not None:
            if self.page.is_started():
                self.page.stop()
            self.page = None

    def get_current_panel(self):
        """Returns the current panel.

        Returns:
            HAUIConfigPanel|None
        """
        return self.panel

    def get_current_nav_panel(self):
        """Returns the current nav panel.

        Returns:
            HAUIConfigPanel|None
        """
        return self._current_nav

    def has_prev_panel(self):
        """Returns if a previous panel is available.

        Returns:
            bool: True if current panel has a previous panel
        """
        if self._current_nav is None:
            return False
        try:
            idx = self._ids.index(self._current_nav.id)
            if idx != 0:
                return True
        except ValueError:
            pass
        return False

    def has_next_panel(self):
        """Returns if a next panel is available.

        Returns:
            bool: True if current panel has a next panel
        """
        if self._current_nav is None:
            return False
        try:
            idx = self._ids.index(self._current_nav.id)
            if len(self._ids) > 1 and idx != len(self._ids) - 1:
                return True
        except ValueError:
            pass
        return False

    def has_up_panel(self):
        """Returns if a up panel is available.

        Returns:
            bool: True if current panel has a up panel
        """
        if len(self._stack) == 0:
            return False
        return True

    # main methods

    def reload_panel(self):
        """Reloads the current panel."""
        self.log(f"Reloading panel: {self.panel.id}")
        self.unset_page()
        if len(self._stack) > 0:
            self._stack.pop()
        self.open_panel(self.panel.id, **self.panel_kwargs)

    def refresh_panel(self):
        """Refreshes the current panel."""
        if self.page is None:
            return
        self.log(f"Refreshing panel: {self.panel.id}")
        self.page.refresh_panel()

    def display_panel(self, panel):
        """Displays the given panel.

        Args:
            panel (HAUIConfigPanel): Panel to display.
        """
        page_id = get_page_id_for_panel(panel.get_type())
        if self.page is not None and self.page.page_id == page_id:
            self.log(f"Setting new panel: {panel.get_type()}")
            # only start the page if it was not started before
            if not self.page.is_started():
                self.page.start()
            self.page.set_panel(panel)

    def open_popup(self, panel_id, **kwargs):
        """Opens a panel as a popup.

        Args:
            panel_id (str): Id of panel
            kwargs (dict): Additional arguments for panel
        """
        kwargs["mode"] = "popup"
        self.open_panel(panel_id, **kwargs)

    def open_panel(self, panel_id, **kwargs):
        """Opens the panel with the given id.

        Args:
            panel_id (str): Id of panel
            kwargs (dict): Additional arguments for panel
        """
        self.log(f"Opening panel: {panel_id}-{kwargs}")

        # lock current panel before setting new
        if self.panel is not None:
            persistent_config = self.panel.get_persistent_config(return_copy=False)
            # only if has a locked attr
            if "locked" in persistent_config:
                # ensure the panel is locked before setting new panel
                persistent_config["locked"] = True

        # create and check page of new panel
        panel = self.app.config.get_panel(panel_id)
        if panel is None:
            self.log(f"Panel {panel_id} not found")
            self.open_home_panel()
            return
        page_id = get_page_id_for_panel(panel.get_type())
        page_class = get_page_class_for_panel(panel.get_type())
        if page_id is None or page_class is None:
            if page_id is None:
                self.log(f"Panel {panel_id} ({panel.get_type()}) has no page defined")
            if page_class is None:
                self.log(
                    f"Panel {panel_id} ({panel.get_type()}) has no page class defined"
                )
            self.open_home_panel()
            return

        # create new config and make kwargs available in new panel
        config = panel.get_default_config(return_copy=True)
        config = {**config, **kwargs}
        panel.set_config(config)

        # new panel is a navigatable panel
        if panel.get_mode() == "panel":
            self._current_nav = panel
            self._current_nav_kwargs = kwargs
            # new panel is a nav panel, clear stack
            if len(self._stack) > 0:
                self._stack = []
        # new panel is not a navigatable panel
        else:
            # add to the navigation stack
            self._stack.append((panel, kwargs))

        # set new panel as current panel
        self.panel = panel
        self.panel_kwargs = kwargs

        # if new panel has an unlock code set and panel is locked,
        # open unlock panel instead
        persistent_config = panel.get_persistent_config(return_copy=False)
        if panel.get("unlock_code", "") != "" and persistent_config.get("locked", True):
            self.log(f"Unlock code set, locking panel {panel.id}")
            # lock new panel
            persistent_config["locked"] = True
            # open the unlock panel with the panel to unlock as a param
            self.open_popup("popup_unlock", unlock_panel=panel)
            return

        # check current page before setting new panel
        curr_page_id = None
        if self.page is not None:
            curr_page_id = self.page.page_id
            self.page.stop()
            self.page = None

        # set new current page and panel
        self.log(f"Switching to page {page_id} from {curr_page_id}")
        self.page = page_class(self.app, {"page_id": page_id})

        # notify about panel creation early in process
        self.page.create_panel(panel)

        # set new page for panel
        self.goto_page(page_id)

        # page autostart
        #
        # at this point, it is possible to return
        # and let the page event handle the page switch but this will add a big delay, since
        # it will be needed to wait until a mqtt event is received so just assume the
        # correct page is set already here and continue without return
        #
        # If autostart then it is assumed that the new page is available when called
        # goto_page. If autostart is false, the page will get started when it is
        # active (when a page event is received)
        if kwargs.get("autostart", False) or curr_page_id == page_id:
            self.display_panel(self.panel)
        else:
            self.log("No autostart, waiting for page event")
            # add timer for timeout
            timeout = self.get("page_timeout", 10.0)
            if self._page_timeout is not None:
                self._page_timeout.cancel()
            self._page_timeout = threading.Timer(
                timeout,
                self.open_panel,
                # provide current params and make sure that autostart is on for timeout call
                kwargs={**kwargs, **{"panel_id": panel_id, "autostart": True}},
            )
            self._page_timeout.start()

        # check for close timeout in panel config (contains also kwargs)
        timeout = panel.get("close_timeout", 0)
        if timeout > 0:
            self._close_timeout = threading.Timer(timeout, self.close_panel)
            self._close_timeout.start()

    def close_panel(self):
        """Closes the current panel."""
        # check for active timer
        if self._close_timeout is not None:
            self._close_timeout.cancel()
            self._close_timeout = None
        prev_panel, prev_kwargs = None, None
        # check stack
        if len(self._stack) > 0:
            # remove last stacked panel
            curr_panel, curr_kwargs = self._stack.pop()
            unlock_panel = (
                curr_kwargs["unlock_panel"] if "unlock_panel" in curr_kwargs else None
            )
            self.log(f"Closing panel: {curr_panel.id}")
            # get previous panel
            while len(self._stack) > 0:
                panel, kwargs = self._stack.pop()
                # if a unlock panel is set, check if it should be skipped (if not unlocked)
                persistent_config = panel.get_persistent_config()
                if unlock_panel and panel.id == unlock_panel.id:
                    if persistent_config.get("locked", False):
                        continue
                prev_panel, prev_kwargs = panel, kwargs
                break
        # no stack, use current nav panel
        if prev_panel is None:
            if self._current_nav:
                prev_panel, prev_kwargs = self._current_nav, self._current_nav_kwargs
        # fallback panel home panel
        if prev_panel is None:
            prev_panel, prev_kwargs = self._home_panel, {}
        # check for locked panel before opening
        if prev_panel is not None:
            unlock_panel = prev_panel.get("unlock_panel")
            persistent_config = prev_panel.get_persistent_config()
            if unlock_panel is not None:
                if prev_panel.id == unlock_panel.id and persistent_config.get(
                    "locked", False
                ):
                    prev_panel, prev_kwargs = None, None
        # open new panel
        if prev_panel is not None:
            self.log(f"Open previous panel: {prev_panel.id}")
            self.open_panel(prev_panel.id, **prev_kwargs)

    # additional methods

    def open_next_panel(self):
        """Opens the next panel."""
        self.log("Open next panel")
        if self._current_nav is None:
            return
        if self._current_nav.id not in self._ids:
            return
        idx = self._ids.index(self._current_nav.id)
        if idx < len(self._ids) - 1:
            panel_id = self._ids[idx + 1]
        else:
            panel_id = self._ids[0]
        self.open_panel(panel_id)

    def open_prev_panel(self):
        """Opens the previous panel."""
        self.log("Open prev panel")
        if self._current_nav is None:
            return
        if self._current_nav.id not in self._ids:
            self.log(f"current nav not in ids {self._current_nav} - {self._ids}")
            return
        idx = self._ids.index(self._current_nav.id)
        if idx > 0:
            panel_id = self._ids[idx - 1]
        else:
            panel_id = self._ids[len(self._ids) - 1]
        self.open_panel(panel_id)

    def open_home_panel(self, autostart=False):
        """Opens the home panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to False.
        """
        if self._home_panel is None:
            self.close_panel()
            self.log("No home panel available")
            return
        self.open_panel(self._home_panel.id, autostart=autostart)

    def open_sleep_panel(self, autostart=False, create_snapshot=True):
        """Opens the sleep panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to False.
            create_snapshot (bool, optional): Should a navigation snapshot be created. Defaults to True.
        """
        if create_snapshot:
            self.create_snapshot()
        if self._sleep_panel is None:
            self.close_panel()
            self.log("No sleep panel available")
            return
        self.open_panel(self._sleep_panel.id, autostart=autostart)

    def open_wakeup_panel(self, autostart=False):
        """Opens the wakeup panel.

        Args:
            autostart (bool, optional): Should the page be autostarted. Defaults to False.
        """
        if self._wakeup_panel is None:
            self.close_panel()
            self.log("No wakeup panel available")
            return
        self.open_panel(self._wakeup_panel.id, autostart=autostart)

    # snapshot methods

    def create_snapshot(self) -> None:
        """Creates a snapshot of the current navigation state."""
        panel = self.panel
        panel_kwargs = self.panel_kwargs.copy()
        current_nav = self._current_nav
        current_nav_kwargs = self._current_nav_kwargs.copy()
        stack = self._stack.copy()
        snapshot = (panel, panel_kwargs, current_nav, current_nav_kwargs, stack)
        self._snapshot = snapshot
        self.log("Navigation snapshot created")

    def unset_snapshot(self) -> None:
        """Unsets the current navigation snapshot."""
        self._snapshot = None

    def restore_snapshot(self, max_seconds_ago: int = 0) -> bool:
        """Restores a previously created navigation snapshot.

        Returns:
            bool: True if successfully restored, False if not
        """
        if self._snapshot is None:
            return False
        (
            self.panel,
            self.panel_kwargs,
            self._current_nav,
            self._current_nav_kwargs,
            self._stack,
        ) = self._snapshot
        self.reload_panel()
        self.log("Navigation snapshot restored")
        return True

    # event

    def process_event(self, event: HAUIEvent):
        """Process events.

        Args:
            event (HAUIEvent): Event
        """
        device = self.app.device

        # check for page
        if event.name == ESP_EVENT["page"]:
            # cancel page timeout if any
            if self._page_timeout is not None:
                self._page_timeout.cancel()
                self._page_timeout = None
            # check current page is not blank page
            if self.page is not None and event.as_int() != 0:
                # wrong page id
                if self.page.page_id != event.as_int():
                    self.log(
                        f"Wrong page {event.as_int()} for current panel page activated,"
                        f" reloading panel to reset page to {self.page.page_id}"
                    )
                    self.reload_panel()
                # page is correct
                else:
                    # update page id
                    if self.page.page_id_recv is None:
                        self.page.page_id_recv = event.as_int()
                    # page not started yet
                    if not self.page.is_started():
                        self.display_panel(self.panel)

        # check timeout page event (sleep)
        if event.name == ESP_EVENT["timeout"]:
            if event.value == "page":
                self._sleep_panel_active = True
                if self._sleep_panel and self._sleep_panel.id != self.panel.id:
                    self.open_sleep_panel()

        # check for display state event (dimmed/off/on)
        if event.name == ESP_EVENT["display_state"]:
            prev_state = device.device_info.get("display_state")
            # previous state was off
            if prev_state is not None and prev_state == "off":
                self.log(f"Display state changed from sleep to {event.as_str()}")
                self._sleep_panel_active = False
                self.open_wakeup_panel()
            # previous state was dimmed
            elif event.as_str() == "on":
                if self._sleep_panel_active:
                    self.log(f"Display state changed to {event.as_str()}")
                    self._sleep_panel_active = False

        # wakeup handling, ensure the correct page is set
        # when waking up from sleep
        if event.name == ESP_EVENT["wakeup"]:
            if self._wakeup_panel is not None:
                self.log(f"Wakeup panel: {self._wakeup_panel.id}")
                self.open_wakeup_panel()
            else:
                # if no wakeup panel is set, use home panel instead of
                # previous panel
                self.log("No wakeup panel available, using home panel")
                self.open_home_panel()

        # sleep handling
        if event.name == ESP_EVENT["sleep"]:
            if self.page:
                # unset current page
                self.unset_page()

        # allow page to process events
        if self.page is not None:
            self.page.process_event(event)
