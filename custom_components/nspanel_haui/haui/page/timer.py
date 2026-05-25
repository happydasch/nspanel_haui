from __future__ import annotations

import datetime
import threading
from typing import Any

from ..abstract.component import Component, ComponentRegistry
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption
from ..mapping.icons import (
    ICO_PAUSE,
    ICO_RESET,
    ICO_START,
    ICO_STOP,
    ICO_TIMER_FINISHED,
    ICO_TIMER_OFF,
)


class TimerPage(HAUIPage):
    DESCRIPTOR = PageDescriptor(
        type_key="timer",
        page_name="timer",
        label="Timer",
        description="Timer item with start, pause and stop controls.",
        options=[
            PageOption(
                key="show_notification",
                kind="bool",
                default=True,
                label="Show notification on finish",
                description="Show a notification on the display when the timer completes.",
                section="Timer",
            ),
        ],
        can_show_popup=True,
        icon="mdi:timer-outline",
    )

    COMPONENTS = ComponentRegistry(
        fnc_left_pri=Component(3, "bFncLPri"),
        fnc_left_sec=Component(4, "bFncLSec"),
        fnc_right_pri=Component(5, "bFncRPri"),
        fnc_right_sec=Component(6, "bFncRSec"),
        title=Component(2, "tTitle"),
        t_minutes=Component(7, "tMin"),
        t_space=Component(8, "tSpace"),
        t_seconds=Component(9, "tSec"),
        btn_up_1=Component(10, "bUp1"),
        btn_up_2=Component(11, "bUp2"),
        btn_up_3=Component(12, "bUp3"),
        btn_up_4=Component(13, "bUp4"),
        btn_down_1=Component(14, "bDown1"),
        btn_down_2=Component(15, "bDown2"),
        btn_down_3=Component(16, "bDown3"),
        btn_down_4=Component(17, "bDown4"),
        btn_start=Component(18, "bStart"),
        btn_stop=Component(19, "bStop"),
    )

    DISPLAY_UPDATE_INTERVAL = 0.5

    # panel

    def prepare(self) -> None:

        self._show_notification = False
        self._timer: dict
        self._timer_update_display: threading.Timer | None = None

    def start_panel(self, panel: HAUIPanel) -> None:
        # initialise (or restore) the timer dict from panel state
        self._timer = self.initialize_timer(panel)

        # notification on timer finish
        self._show_notification = panel.get("show_notification", self._show_notification)

        # set function buttons
        stop_btn = {
            "fnc_component": self.COMPONENTS.fnc_right_sec,
            "fnc_name": "stop_timer",
            "fnc_args": {
                "icon": ICO_TIMER_OFF,
                "color": self.get_color("component_accent"),
                "visible": self.is_timer_active(),
            },
        }
        self.set_function_buttons(
            self.COMPONENTS.fnc_left_pri,
            self.COMPONENTS.fnc_left_sec,
            self.COMPONENTS.fnc_right_pri,
            stop_btn,
        )

        # adjust buttons for timer
        for x in [
            self.COMPONENTS.btn_up_1,
            self.COMPONENTS.btn_up_2,
            self.COMPONENTS.btn_up_3,
            self.COMPONENTS.btn_up_4,
            self.COMPONENTS.btn_down_1,
            self.COMPONENTS.btn_down_2,
            self.COMPONENTS.btn_down_3,
            self.COMPONENTS.btn_down_4,
        ]:
            visible = not self.is_timer_active()
            self.set_function_component(
                x,
                x[1],
                fnc_name=x[1],
                color=self.get_color("component_active"),
                visible=visible,
            )

        # control buttons for timer
        for ctrl, ctrl_name in [
            (self.COMPONENTS.btn_start, "start_timer"),
            (self.COMPONENTS.btn_stop, "stop_timer"),
        ]:
            self.set_function_component(ctrl, ctrl[1], fnc_name=ctrl_name, visible=False)

        # display
        self.set_function_component(
            self.COMPONENTS.t_minutes,
            self.COMPONENTS.t_minutes.name,
            fnc_name=self.COMPONENTS.t_minutes.name,
            visible=True,
            color=self.get_color("component_text"),
        )
        self.set_function_component(
            self.COMPONENTS.t_space,
            self.COMPONENTS.t_space.name,
            fnc_name=self.COMPONENTS.t_space.name,
            visible=True,
            color=self.get_color("component_text"),
        )
        self.set_function_component(
            self.COMPONENTS.t_seconds,
            self.COMPONENTS.t_seconds.name,
            fnc_name=self.COMPONENTS.t_seconds.name,
            visible=True,
            color=self.get_color("component_text"),
        )

    def _stop_panel(self, panel: HAUIPanel) -> None:
        if self._timer_update_display is not None:
            self._timer_update_display.cancel()
            self._timer_update_display = None

    def render_panel(self, panel: HAUIPanel) -> None:
        self.set_component_text(self.COMPONENTS.title, panel.get_title(self.translate("Timer")))
        # initial call sets up timers
        self.update_timer()

    # misc

    def initialize_timer(self, panel: HAUIPanel) -> dict[str, Any]:
        # timer is stored in panel state so it can be restored after panel was closed
        if panel.get_state("timer") is None:
            panel.set_state(
                "timer",
                {
                    "timer_time": datetime.datetime.now(),
                    "timer_minutes": 0,
                    "timer_seconds": 0,
                    "timer_handle": None,
                    "timer_countdown": False,
                    "timer_paused": False,
                    "timer_active": False,
                    "timer_switch": True,
                },
            )
        return panel.get_state("timer")

    def start_timer(self) -> None:
        timer = self._timer
        # check if there is a active timer and cancel timer handle
        if timer["timer_handle"] is not None:
            timer["timer_handle"].cancel()
            timer["timer_handle"] = None
        # get current timer values and set them in timer dict
        duration = self.get_timer_duration()
        countdown = True if duration > 0 else False
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        # update timer dict
        timer.update(
            {
                "timer_minutes": minutes,
                "timer_seconds": seconds,
                "timer_time": datetime.datetime.now(),
                "timer_countdown": countdown,
                "timer_active": True,
                "timer_paused": False,
                "timer_switch": True,
            }
        )
        if duration > 0:
            timer["timer_handle"] = threading.Timer(duration + 1, self.callback_timer_ended)
            timer["timer_handle"].start()
        # update display
        with self.rec_cmd:
            self.update_adjust_buttons(False)
            self.update_function_component(self.FNC_BTN_R_SEC, visible=True)

    def stop_timer(self) -> None:
        timer = self._timer
        # handle can always be canceled
        if timer["timer_handle"] is not None:
            timer["timer_handle"].cancel()
            timer["timer_handle"] = None
        # update timer dict
        timer.update(
            {
                "timer_active": False,
                "timer_switch": True,
                "timer_minutes": 0,
                "timer_seconds": 0,
            }
        )
        # update display
        with self.rec_cmd:
            self.update_adjust_buttons(True)
            self.update_function_component(self.FNC_BTN_R_SEC, visible=False)

    def pause_timer(self) -> None:
        self._timer["timer_paused"] = True

    def resume_timer(self) -> None:
        self._timer["timer_paused"] = False

    def get_timer_duration(self) -> int:
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        duration = (minutes * 60) + seconds
        return max(duration, 0)

    def is_timer_active(self) -> bool:
        timer = self._timer
        return timer.get("timer_active", False)

    def update_timer(self) -> None:
        if self.is_timer_active():
            timer = self._timer
            # update timer components
            now = datetime.datetime.now()
            prev = timer["timer_time"]
            diff = (now - prev).seconds

            # check minutes and seconds
            duration = self.get_timer_duration()
            if timer["timer_countdown"]:
                duration -= diff
            else:
                duration += diff
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            # only update after something changed
            if not timer["timer_paused"]:
                if minutes != timer["timer_minutes"] or seconds != timer["timer_seconds"]:
                    switch = not timer.get("timer_switch", True)
                    timer.update(
                        {
                            "timer_time": now,
                            "timer_minutes": minutes,
                            "timer_seconds": seconds,
                            "timer_switch": switch,
                        }
                    )
            else:
                timer.update({"timer_time": now, "timer_switch": True})
                if duration > 0:
                    if timer["timer_handle"] is not None:
                        timer["timer_handle"].cancel()
                    timer["timer_handle"] = threading.Timer(duration + 1, self.callback_timer_ended)
                    timer["timer_handle"].start()
        # update display
        with self.rec_cmd:
            self.update_timer_components()
        # set next update using interval
        self._timer_update_display = threading.Timer(
            self.DISPLAY_UPDATE_INTERVAL, self.update_timer
        )
        self._timer_update_display.start()

    def update_timer_components(self) -> None:
        self.update_timer_display()
        self.update_control_buttons()

    def update_timer_display(self) -> None:
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        switch = timer["timer_switch"]
        self.update_function_component(self.COMPONENTS.t_minutes.name, text=f"{minutes:02}")
        self.update_function_component(self.COMPONENTS.t_space.name, text=(":" if switch else " "))
        self.update_function_component(self.COMPONENTS.t_seconds.name, text=f"{seconds:02}")

    def update_control_buttons(self) -> None:
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        for x in [self.COMPONENTS.btn_start, self.COMPONENTS.btn_stop]:
            fnc_name = None
            enabled = True
            if x == self.COMPONENTS.btn_start:
                if not timer["timer_active"]:
                    icon = ICO_START
                    fnc_name = "start_timer"
                elif timer["timer_paused"]:
                    icon = ICO_START
                    fnc_name = "resume_timer"
                else:
                    icon = ICO_PAUSE
                    fnc_name = "pause_timer"
            elif x == self.COMPONENTS.btn_stop:
                fnc_name = "stop_timer"
                icon = ICO_STOP
                if not timer["timer_active"]:
                    if minutes != 0 or seconds != 0:
                        icon = ICO_RESET
                    else:
                        enabled = False
            (
                color,
                color_pressed,
                back_color,
                back_color_pressed,
            ) = self.get_button_colors(enabled)
            self.update_function_component(
                x[1],
                update_fnc_name=fnc_name,
                visible=True,
                color=color,
                color_pressed=color_pressed,
                back_color_pressed=back_color_pressed,
                icon=icon,
                touch=enabled,
            )

    def update_adjust_buttons(self, visible: bool) -> None:
        for x in [
            self.COMPONENTS.btn_up_1,
            self.COMPONENTS.btn_up_2,
            self.COMPONENTS.btn_up_3,
            self.COMPONENTS.btn_up_4,
            self.COMPONENTS.btn_down_1,
            self.COMPONENTS.btn_down_2,
            self.COMPONENTS.btn_down_3,
            self.COMPONENTS.btn_down_4,
        ]:
            self.update_function_component(x[1], visible=visible)

    # callback

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        if fnc_id == self.COMPONENTS.btn_up_1.name:
            minutes += 10
        elif fnc_id == self.COMPONENTS.btn_up_2.name:
            minutes += 1
        elif fnc_id == self.COMPONENTS.btn_up_3.name:
            seconds += 10
        elif fnc_id == self.COMPONENTS.btn_up_4.name:
            seconds += 1
        elif fnc_id == self.COMPONENTS.btn_down_1.name:
            minutes -= 10
        elif fnc_id == self.COMPONENTS.btn_down_2.name:
            minutes -= 1
        elif fnc_id == self.COMPONENTS.btn_down_3.name:
            seconds -= 10
        elif fnc_id == self.COMPONENTS.btn_down_4.name:
            seconds -= 1
        # update timer values in persistent config
        if seconds >= 60:
            seconds = 0
            minutes += 1
        elif seconds < 0:
            seconds = 59
            minutes -= 1
        if minutes >= 60:
            minutes = 0
        elif minutes < 0:
            minutes = 59
        timer["timer_minutes"] = minutes
        timer["timer_seconds"] = seconds
        # functions by name
        if fnc_name == "start_timer":
            self.start_timer()
        elif fnc_name == "stop_timer":
            self.stop_timer()
        elif fnc_name == "pause_timer":
            self.pause_timer()
        elif fnc_name == "resume_timer":
            self.resume_timer()
        self.update_timer_components()

    def callback_timer_ended(self) -> None:
        self.stop_timer()
        if self.app.device.get("sound_on_notification"):
            self.app.device.play_sound("alert")
        if self._show_notification:
            navigation = self.app.controller["navigation"]
            msg = self.translate("Timer has finished.")
            # open notification
            navigation.open_panel(
                SysPanelKey.POPUP_NOTIFY,
                title=self.translate("Timer finished"),
                btn_right=self.translate("Close"),
                icon=ICO_TIMER_FINISHED,
                notification=msg,
            )
