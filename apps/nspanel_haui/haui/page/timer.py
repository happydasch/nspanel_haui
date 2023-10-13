import datetime
import threading

from ..mapping.color import COLORS
from ..helper.icon import get_icon

from . import HAUIPage


class TimerPage(HAUIPage):
    ICO_START = get_icon("mdi:play")
    ICO_PAUSE = get_icon("mdi:pause")
    ICO_STOP = get_icon("mdi:stop")
    ICO_RESET = get_icon("mdi:close")
    ICO_TIMER_OFF = get_icon("mdi:timer-off-outline")

    # common components
    TXT_TITLE = (2, "tTitle")
    BTN_FNC_LEFT_PRI, BTN_FNC_LEFT_SEC = (3, "bFncLPri"), (4, "bFncLSec")
    BTN_FNC_RIGHT_PRI, BTN_FNC_RIGHT_SEC = (5, "bFncRPri"), (6, "bFncRSec")
    # timer
    TXT_MINUTES, TXT_SPACE, TXT_SECONDS = (7, "tMin"), (8, "tSpace"), (9, "tSec")
    # up and down buttons
    BTN_UP_1, BTN_UP_2, BTN_UP_3, BTN_UP_4 = (
        (10, "bUp1"),
        (11, "bUp2"),
        (12, "bUp3"),
        (13, "bUp4"),
    )
    BTN_DOWN_1, BTN_DOWN_2, BTN_DOWN_3, BTN_DOWN_4 = (
        (14, "bDown1"),
        (15, "bDown2"),
        (16, "bDown3"),
        (17, "bDown4"),
    )
    # buttons
    BTN_START, BTN_STOP = (18, "bStart"), (19, "bStop")

    DISPLAY_UPDATE_INTERVAL = 0.5

    _persistent_config = None
    _timer = None
    _timer_update_display = None

    # panel

    def start_panel(self, panel):
        # set persistent timer dict for later access
        self._persistent_config = panel.get_persistent_config(return_copy=False)
        self._timer = self.initialize_timer()
        # set function buttons
        stop_btn = {
            "fnc_component": self.BTN_FNC_RIGHT_SEC,
            "fnc_name": "stop_timer",
            "fnc_args": {
                "icon": self.ICO_TIMER_OFF,
                "color": COLORS["component_accent"],
                "visible": self.is_timer_active(),
            },
        }
        self.set_function_buttons(
            self.BTN_FNC_LEFT_PRI,
            self.BTN_FNC_LEFT_SEC,
            self.BTN_FNC_RIGHT_PRI,
            stop_btn,
        )
        # adjust buttons for timer

        for x in [
            self.BTN_UP_1,
            self.BTN_UP_2,
            self.BTN_UP_3,
            self.BTN_UP_4,
            self.BTN_DOWN_1,
            self.BTN_DOWN_2,
            self.BTN_DOWN_3,
            self.BTN_DOWN_4,
        ]:
            visible = not self.is_timer_active()
            self.set_function_component(
                x, x[1], fnc_name=x[1], color=COLORS["component"], visible=visible
            )
        # control buttons for timer
        for x in [(self.BTN_START, "start_timer"), (self.BTN_STOP, "stop_timer")]:
            self.set_function_component(x[0], x[0][1], fnc_name=x[1], visible=False)
        # display
        self.set_function_component(
            self.TXT_MINUTES,
            self.TXT_MINUTES[1],
            fnc_name=self.TXT_MINUTES[1],
            visible=True,
            color=COLORS["component"],
        )
        self.set_function_component(
            self.TXT_SPACE,
            self.TXT_SPACE[1],
            fnc_name=self.TXT_SPACE[1],
            visible=True,
            color=COLORS["component"],
        )
        self.set_function_component(
            self.TXT_SECONDS,
            self.TXT_SECONDS[1],
            fnc_name=self.TXT_SECONDS[1],
            visible=True,
            color=COLORS["component"],
        )

    def stop_panel(self, panel):
        if self._timer_update_display is not None:
            self._timer_update_display.cancel()
            self._timer_update_display = None

    def render_panel(self, panel):
        self.set_component_text(
            self.TXT_TITLE, panel.get_title(self.translate("Timer"))
        )
        # initial call sets up timers
        self.update_timer()

    # misc

    def initialize_timer(self):
        # timer is stored in persistent config so it can be restored
        # after panel was closed
        if "timer" not in self._persistent_config:
            timer = {
                "timer_time": datetime.datetime.now(),
                "timer_minutes": 0,
                "timer_seconds": 0,
                "timer_handle": None,
                "timer_countdown": False,
                "timer_paused": False,
                "timer_active": False,
                "timer_switch": True,
            }
            self._persistent_config["timer"] = timer
        return self._persistent_config["timer"]

    def start_timer(self):
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
            timer["timer_handle"] = threading.Timer(
                duration + 1, self.callback_timer_ended
            )
            timer["timer_handle"].start()
        # update display
        self.start_rec_cmd()
        self.update_adjust_buttons(False)
        self.update_function_component(self.FNC_BTN_R_SEC, visible=True)
        self.stop_rec_cmd(send_commands=True)

    def stop_timer(self):
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
        self.start_rec_cmd()
        self.update_adjust_buttons(True)
        self.update_function_component(self.FNC_BTN_R_SEC, visible=False)
        self.stop_rec_cmd(send_commands=True)

    def pause_timer(self):
        self._timer["timer_paused"] = True

    def resume_timer(self):
        self._timer["timer_paused"] = False

    def get_timer_duration(self):
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        duration = (minutes * 60) + seconds
        return max(duration, 0)

    def is_timer_active(self):
        timer = self._timer
        return timer.get("timer_active", False)

    def update_timer(self):
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
                if (
                    minutes != timer["timer_minutes"]
                    or seconds != timer["timer_seconds"]
                ):
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
                    timer["timer_handle"] = threading.Timer(
                        duration + 1, self.callback_timer_ended
                    )
                    timer["timer_handle"].start()
        # update display
        self.start_rec_cmd()
        self.update_timer_components()
        self.stop_rec_cmd(send_commands=True)
        # set next update using interval
        self._timer_update_display = threading.Timer(
            self.DISPLAY_UPDATE_INTERVAL, self.update_timer
        )
        self._timer_update_display.start()

    def update_timer_components(self):
        self.update_timer_display()
        self.update_control_buttons()

    def update_timer_display(self):
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        switch = timer["timer_switch"]
        self.update_function_component(self.TXT_MINUTES[1], text=f"{minutes:02}")
        self.update_function_component(self.TXT_SPACE[1], text=(":" if switch else " "))
        self.update_function_component(self.TXT_SECONDS[1], text=f"{seconds:02}")

    def update_control_buttons(self):
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        for x in [self.BTN_START, self.BTN_STOP]:
            fnc_name = None
            enabled = True
            if x == self.BTN_START:
                if not timer["timer_active"]:
                    icon = self.ICO_START
                    fnc_name = "start_timer"
                elif timer["timer_paused"]:
                    icon = self.ICO_START
                    fnc_name = "resume_timer"
                else:
                    icon = self.ICO_PAUSE
                    fnc_name = "pause_timer"
            elif x == self.BTN_STOP:
                fnc_name = "stop_timer"
                icon = self.ICO_STOP
                if not timer["timer_active"]:
                    if minutes != 0 or seconds != 0:
                        icon = self.ICO_RESET
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

    def update_adjust_buttons(self, visible):
        for x in [
            self.BTN_UP_1,
            self.BTN_UP_2,
            self.BTN_UP_3,
            self.BTN_UP_4,
            self.BTN_DOWN_1,
            self.BTN_DOWN_2,
            self.BTN_DOWN_3,
            self.BTN_DOWN_4,
        ]:
            self.update_function_component(x[1], visible=visible)

    # callback

    def callback_function_component(self, fnc_id, fnc_name):
        timer = self._timer
        minutes = timer["timer_minutes"]
        seconds = timer["timer_seconds"]
        if fnc_id == self.BTN_UP_1[1]:
            minutes += 10
        elif fnc_id == self.BTN_UP_2[1]:
            minutes += 1
        elif fnc_id == self.BTN_UP_3[1]:
            seconds += 10
        elif fnc_id == self.BTN_UP_4[1]:
            seconds += 1
        elif fnc_id == self.BTN_DOWN_1[1]:
            minutes -= 10
        elif fnc_id == self.BTN_DOWN_2[1]:
            minutes -= 1
        elif fnc_id == self.BTN_DOWN_3[1]:
            seconds -= 10
        elif fnc_id == self.BTN_DOWN_4[1]:
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

    def callback_timer_ended(self):
        self.stop_timer()
        device_name = self.app.device.get("device_name", "nspanel_haui")
        self.app.call_service(f"esphome/{device_name}_play_sound", name="alert")


class PopupTimerPage(TimerPage):
    pass
