from __future__ import annotations

import datetime
import re
import zoneinfo
from typing import Any

from ..abstract.component import Component
from ..abstract.haui_event import HAUIEvent
from ..abstract.haui_page import HAUIPage
from ..abstract.haui_panel import HAUIPanel
from ..mapping.background import BACKGROUNDS
from ..mapping.const import SysPanelKey
from ..mapping.descriptor import PageDescriptor, PageOption
from ..mapping.icons import ICO_MESSAGE, ICO_SPECIAL

MATRIX = {
    "en": (
        "ITLISBFAMPM"  # 0
        "ACQUARTERDC"  # 11
        "TWENTYFIVEX"  # 22
        "HALFBTENFTO"  # 33
        "PASTERUNINE"  # 44
        "ONESIXTHREE"  # 55
        "FOURFIVETWO"  # 66
        "EIGHTELEVEN"  # 77
        "SEVENTWELVE"  # 88
        "TENSE[O']CLOCK"  # 99
    ),
    "de": (
        "ESKISTAFÜNF"  # 0
        "ZEHNZWANZIG"  # 11
        "DREIVIERTEL"  # 22
        "VORFUNKNACH"  # 33
        "HALBAELFÜNF"  # 44
        "EINSXAMZWEI"  # 55
        "DREIPMJVIER"  # 66
        "SECHSNLACHT"  # 77
        "SIEBENZWÖLF"  # 88
        "ZEHNEUNKUHR"  # 99
    ),
    "pl": (
        "ZAEKWADRANS"  # 0
        "DWADZIEŚCIA"  # 11
        "DZIESIĘĆ[PI]ĘĆ"  # 22
        "WPÓŁPODOESR"  # 33
        "[PI]ERWSZA[PI]ĄTA"  # 44
        "DRUGATRZE[CI]A"  # 55
        "ÓSMACZWARTA"  # 66
        "SZÓSTA[SI]ÓDMA"  # 77
        "DWUD[ZI]EWS[IĄ]TA"  # 88
        "[JE]DENASTAIEJ"  # 99
    ),
}

MATRIX_WORDS: dict[str, dict] = {
    "en": {
        "it-is": [0, 1, 3, 4],  # it is
        "am": [7, 8],  # am
        "pm": [9, 10],  # pm
        "to": [42, 43],  # to
        "past": [44, 45, 46, 47],  # past
        #
        "five-u": [28, 29, 30, 31],  # five
        "ten-u": [38, 39, 40],  # ten
        "quarter-u": [13, 14, 15, 16, 17, 18, 19],  # quarter
        "twenty-u": [22, 23, 24, 25, 26, 27],  # twenty
        "half-u": [33, 34, 35, 36, 44, 45, 46, 47],  # half past
        #
        "one": [55, 56, 57],  # one
        "two": [74, 75, 76],  # two
        "three": [61, 62, 63, 64, 65],  # three
        "four": [66, 67, 68, 69],  # four
        "five": [70, 71, 72, 73],  # five
        "six": [58, 59, 60],  # six
        "seven": [88, 89, 90, 91, 92],  # seven
        "eight": [77, 78, 79, 80, 81],  # eight
        "nine": [51, 52, 53, 54],  # nine
        "ten": [99, 100, 101],  # ten
        "eleven": [82, 83, 84, 85, 86, 87],  # eleven
        "twelve": [93, 94, 95, 96, 97, 98],  # twelve
        "oclock": [104, 105, 106, 107, 108, 109],  # oclock
    },
    "de": {
        "it-is": [0, 1, 3, 4, 5],  # es is
        "am": [],  # am
        "pm": [],  # pm
        "to": [33, 34, 35],  # vor
        "past": [40, 41, 42, 43],  # nach
        "five-u": [7, 8, 9, 10],  # fünf
        "ten-u": [11, 12, 13, 14],  # zehn
        "quarter-u": {
            "past": [26, 27, 28, 29, 30, 31, 31, 32],  # viertel
            "to": [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 31, 32],  # dreiviertel
        },
        "twenty-u": {
            "*": [15, 16, 17, 18, 19, 20, 21],  # zwanzig
            ("five-u", "past"): [33, 34, 35, 44, 45, 46, 47],  # vor halb
            ("five-u", "to"): [40, 41, 42, 43, 44, 45, 46, 47],  # nach halb
        },
        "half-u": [44, 45, 46, 47],  # halb
        #
        "one": [55, 56, 57, 58],  # eins
        "two": [62, 63, 64, 65],  # zwei
        "three": [66, 67, 68, 69],  # drei
        "four": [73, 74, 75, 76],  # vier
        "six": [77, 78, 79, 80, 81],  # sechs
        "seven": [88, 89, 90, 91, 92, 93],  # sieben
        "eight": [84, 85, 86, 87],  # acht
        "nine": [102, 103, 104, 105],  # neun
        "eleven": [49, 50, 51],  # elf
        "twelve": [94, 95, 96, 97, 98],  # zwölf
        "five": [51, 52, 53, 54],  # fünf
        "ten": [99, 100, 101, 102],  # zehn
        "oclock": [107, 108, 109],  # uhr
    },
    "pl": {
        "it-is": [],  # -
        "am": [],  # am
        "pm": [],  # pm
        "to": [0, 1],  # za
        "past": [37, 38],  # po
        "five-u": [30, 31, 32],  # piec
        "ten-u": [22, 23, 24, 25, 26, 27, 28, 29],  # dziesiec
        "quarter-u": [3, 4, 5, 6, 7, 8, 9, 10],  # kwadrans
        "twenty-u": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],  # dwadziescia
        "half-u": [33, 34, 35, 36, 39, 40],  # wpol do
        "one": {
            "*": [44, 45, 46, 47, 48, 49, 108, 109],  # pierwszej
            "to": [44, 45, 46, 47, 48, 49, 50],  # pierwsza
            "oclock": [44, 45, 46, 47, 48, 49, 50],  # pierwsza
        },
        "two": {
            "*": [55, 56, 57, 58, 107, 108, 109],  # drugiej
            "to": [55, 56, 57, 58, 59],  # druga
            "oclock": [55, 56, 57, 58, 59],  # druga
        },
        "three": {
            "*": [60, 61, 62, 63, 64, 108, 109],  # trzeciej
            "to": [60, 61, 62, 63, 64, 65],  # trzecia
            "oclock": [60, 61, 62, 63, 64, 65],  # trzecia
        },
        "four": {
            "*": [70, 71, 72, 73, 74, 75, 108, 109],  # czwartej
            "to": [70, 71, 72, 73, 74, 75, 76],  # czwarta
            "oclock": [70, 71, 72, 73, 74, 75, 76],  # czwarta
        },
        "five": {
            "*": [51, 52, 53, 108, 109],  # piatej
            "to": [51, 52, 53, 54],  # piata
            "oclock": [51, 52, 53, 54],  # piata
        },
        "six": {
            "*": [77, 78, 79, 80, 81, 108, 109],  # szostej
            "to": [77, 78, 79, 80, 81, 82],  # szosta
            "oclock": [77, 78, 79, 80, 81, 82],  # szosta
        },
        "seven": {
            "*": [83, 84, 85, 86, 108, 109],  # siodmej
            "to": [83, 84, 85, 86, 87],  # siodma
            "oclock": [83, 84, 85, 86, 87],  # siodma
        },
        "eight": {
            "*": [66, 67, 68, 108, 109],  # osmej
            "to": [66, 67, 68, 69],  # osma
            "oclock": [66, 67, 68, 69],  # osma
        },
        "nine": {
            "*": [91, 92, 93, 94, 96, 97, 108, 109],  # dziewiątej
            "to": [91, 92, 93, 94, 96, 97, 98],  # dziewiąta
            "oclock": [91, 92, 93, 94, 96, 97, 98],  # dziewiąta
        },
        "ten": {
            "*": [91, 92, 93, 95, 96, 97, 108, 109],  # dziesiątej
            "to": [91, 92, 93, 95, 96, 97, 98],  # dziesiąta
            "oclock": [91, 92, 93, 95, 96, 97, 98],  # dziesiąta
        },
        "eleven": {
            "*": [99, 100, 101, 102, 103, 104, 105, 108, 109],  # jedenstej
            "to": [99, 100, 101, 102, 103, 104, 105, 106],  # jedensta
            "oclock": [99, 100, 101, 102, 103, 104, 105, 106],  # jedensta
        },
        "twelve": {
            "*": [88, 89, 90, 102, 103, 104, 105, 108, 109],  # dwunastej
            "to": [88, 89, 90, 102, 103, 104, 105, 106],  # dwunasta
            "oclock": [88, 89, 90, 102, 103, 104, 105, 106],  # dwunasta
        },
        "oclock": [],  # -
    },
}

NEXT_HOUR_START = {
    "en": 35,
    "de": 25,
    "pl": 30,
}

HOUR_WORDS = [
    "twelve",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
]

MINUTE_RANGES = [
    (5, 10, ["five-u", "past"]),
    (10, 15, ["ten-u", "past"]),
    (15, 20, ["quarter-u", "past"]),
    (20, 25, ["twenty-u", "past"]),
    (25, 30, ["twenty-u", "five-u", "past"]),
    (30, 35, ["half-u"]),
    (35, 40, ["twenty-u", "five-u", "to"]),
    (40, 45, ["twenty-u", "to"]),
    (45, 50, ["quarter-u", "to"]),
    (50, 55, ["ten-u", "to"]),
    (55, 60, ["five-u", "to"]),
]

INDEX_LETTER_START = 2
INDEX_LETTER_LENGTH = 110
INDEX_SPECIAL_START = 113
INDEX_SPECIAL_LENGTH = 4


class ClockTwoPage(HAUIPage):
    PICTURE_BACKGROUND = True
    USE_SYSTEM_COLORS = False
    DESCRIPTOR = PageDescriptor(
        type_key="clocktwo",
        page_name="clocktwo",
        label="Clock Two",
        description="Word-clock display in multiple languages.",
        options=[
            PageOption(
                key="background",
                kind="select",
                default="default",
                label="Background",
                description="Background image theme for the word clock display.",
                section="Appearance",
                choices=[
                    ("default", "Default"),
                    ("spring", "Spring"),
                    ("summer", "Summer"),
                    ("autumn", "Autumn"),
                    ("winter", "Winter"),
                    ("dog_1", "Dog 1"),
                    ("dog_2", "Dog 2"),
                    ("cat", "Cat"),
                ],
            ),
            PageOption(
                key="clock_language",
                kind="select",
                default="en",
                label="Clock language",
                description="Language for the word clock text matrix.",
                section="Appearance",
                choices=[("en", "English"), ("de", "German"), ("pl", "Polish")],
            ),
            PageOption(
                key="off_color",
                kind="color",
                default=8452,
                label="Off-letter color",
                description="Default: 8452 (dark gray). Accepts RGB565, [r,g,b], or #rrggbb.",
                section="Colors",
            ),
            PageOption(
                key="letter_color",
                kind="color",
                default=65535,
                label="Active letter color",
                description="Default: 65535 (white). Accepts RGB565, [r,g,b], or #rrggbb.",
                section="Colors",
            ),
            PageOption(
                key="special_color",
                kind="color",
                default=62694,
                label="Special letter color",
                description="Default: 62694 (amber). Accepts RGB565, [r,g,b], or #rrggbb.",
                section="Colors",
            ),
            PageOption(
                key="show_ampm",
                kind="bool",
                default=False,
                label="Show AM/PM",
                description="Show AM/PM indicator on the word clock display.",
                section="Display",
            ),
            PageOption(
                key="show_intro_text",
                kind="bool",
                default=True,
                label="Show intro text",
                description="Show intro text ('IT IS') at start of word clock display.",
                section="Display",
            ),
            PageOption(
                key="show_intro_text_full_hour",
                kind="bool",
                default=True,
                label="Show intro text on full hour",
                description="Show 'IT IS' text on full hour (e.g. 'IT IS FIVE OCLOCK').",
                section="Display",
            ),
            PageOption(
                key="show_notifications",
                kind="bool",
                default=True,
                label="Show notifications",
                description="Show notification indicator icon on the word clock screen.",
                section="Notifications",
            ),
        ],
        icon="mdi:clock-edit-outline",
        has_header=False,
    )

    # components, skipping l1-110, s1-4
    COMPONENTS = HAUIPage.COMPONENTS.merge(
        t_notif=Component(117, "tNotif"),
    )

    DISPLAY_UPDATE_INTERVAL = 1.0

    # panel

    def prepare(self) -> None:
        # Initialize defaults used by create_panel() before start_page() runs.
        # Navigation calls create_panel() immediately after constructing the
        # page instance, which is before start_page() is invoked.
        self._off_color = self.get_color("component_background")
        self._letter_color = self.get_color("component_text")
        self._special_color = self.get_color("component_accent")
        self._clock_language = "en"
        self._show_ampm = False
        self._show_intro_text = True
        self._show_intro_text_full_hour = False

        self._show_notifications = True

        self._letter_current_state: list[bool] = []
        self._special_current_state: list[bool] = []
        self._clock_letters: list[str] = []

    def create_panel(self, panel: HAUIPanel) -> None:
        # setting: background
        # set before showing panel
        background = panel.get("background", "default")
        background = self.render_template(background, False)
        self._off_color = panel.get("off_color", self._off_color)
        self._letter_color = panel.get("letter_color", self._letter_color)
        self._special_color = panel.get("special_color", self._special_color)
        self._clock_language = panel.get("clock_language", self._clock_language)
        self._show_ampm = panel.get("show_ampm", self._show_ampm)
        self._show_intro_text = panel.get("show_intro_text", self._show_intro_text)
        self._show_intro_text_full_hour = panel.get(
            "show_intro_text_full_hour", self._show_intro_text_full_hour
        )
        if background in BACKGROUNDS:
            self.send_cmd(f"clocktwo.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel: HAUIPanel) -> None:
        # time update callback (shared device-wide tick)
        self.app.subscribe_tick("minute", self.callback_update_time)
        # Register notification indicator with the shared blinker
        self.app.controller["notification"].set_blinker_callback(self._refresh_notif)
        # notification
        self._show_notifications = panel.get("show_notifications", True)
        self.set_function_component(
            self.COMPONENTS.t_notif, self.COMPONENTS.t_notif.name, visible=self._show_notifications
        )
        self.init_interface(panel)

    def render_panel(self, panel: HAUIPanel) -> None:
        self.update_interface()
        self.app.controller["notification"].blinker.refresh()

    def _stop_panel(self, panel: HAUIPanel) -> None:
        # cancel time tick subscription
        self.app.unsubscribe_tick("minute", self.callback_update_time)
        # unregister notification indicator from shared blinker
        self.app.controller["notification"].clear_blinker_callback()

    # clock

    def init_interface(self, panel: HAUIPanel) -> None:
        pattern = re.compile(r"\[([^\]]+)\]|.")
        self._clock_letters = [
            (match.group(1) if match.group(1) else match.group(0)) or ""
            for match in pattern.finditer(MATRIX[self._clock_language])
        ]
        letter_components = []
        special_components = []
        specials = []
        for i in range(INDEX_LETTER_LENGTH):
            component = self.get_letter_component(i)
            letter_components.append(component)
        for i in range(INDEX_SPECIAL_LENGTH):
            component = self.get_special_component(i)
            special_components.append(component)
            specials.append(ICO_SPECIAL)
        components = letter_components + special_components
        components_text = self._clock_letters + specials
        for component, component_text in zip(components, components_text, strict=True):
            with self.rec_cmd:
                self.set_component_text_color(component, self._off_color)
                self.set_component_text(component, text=component_text or "")
        self._letter_current_state = [False] * INDEX_LETTER_LENGTH
        self._special_current_state = [False] * INDEX_SPECIAL_LENGTH

    def update_interface(self) -> None:
        timezone = self.app.hass.config.time_zone
        current_time = datetime.datetime.now(tz=zoneinfo.ZoneInfo(timezone))
        letters_active, specials_active, time_words = self.get_matrix_from_time(current_time)

        matrix_text = ""
        for letter_index in range(INDEX_LETTER_LENGTH):
            if letters_active[letter_index] is True:
                if letter_index > 0 and letters_active[letter_index - 1] is False:
                    matrix_text += " "
                matrix_text += self._clock_letters[letter_index]
        self.log(f"text: {matrix_text} for words: {' '.join(time_words)}")
        for i, old, new in zip(
            range(INDEX_LETTER_LENGTH), self._letter_current_state, letters_active, strict=True
        ):
            component = self.get_letter_component(i)
            if old != new:
                if new is True:
                    self.set_component_text_color(component, self._letter_color)
                else:
                    self.set_component_text_color(component, self._off_color)
                self._letter_current_state[i] = new
        for i, old, new in zip(
            range(INDEX_SPECIAL_LENGTH), self._special_current_state, specials_active, strict=True
        ):
            component = self.get_special_component(i)
            if old != new:
                if new is True:
                    self.set_component_text_color(component, self._special_color)
                else:
                    self.set_component_text_color(component, self._off_color)
                self._special_current_state[i] = new

    def get_matrix_from_time(
        self, time: datetime.datetime
    ) -> tuple[list[bool], list[bool], list[str]]:
        words_index = MATRIX_WORDS[self._clock_language]
        time_words, specials = self.get_words_from_time(time)
        letters_active = [False] * INDEX_LETTER_LENGTH
        specials_active = [False] * INDEX_SPECIAL_LENGTH

        for word in time_words:
            if word in words_index:
                lit = words_index[word]
                if isinstance(lit, list):
                    # list with letters
                    for i in lit:
                        letters_active[i] = True
                elif isinstance(lit, dict):
                    # dict with rules when to lit
                    # if key is a tuple then all words need to match
                    # if key is a string then this word needs to match
                    # if no key matched and * in key then this will be used
                    lit_key: tuple | str | None = None
                    for key in lit.keys():
                        if isinstance(key, tuple):
                            lit_key = key
                            for k in key:
                                if k not in time_words:
                                    lit_key = None
                                    break
                        elif key in time_words:
                            lit_key = key
                            break
                        if lit_key is not None:
                            break
                    if lit_key is None and "*" in lit:
                        lit_key = "*"
                    if lit_key is not None:
                        for i in lit[lit_key]:
                            letters_active[i] = True

        for idx in range(INDEX_SPECIAL_LENGTH):
            specials_active[idx] = specials[idx]

        return letters_active, specials_active, time_words

    def get_words_from_time(self, time: datetime.datetime) -> tuple[list[str], list[bool]]:
        minutes = time.minute
        hours = time.hour % 12
        words = []
        # intro text it is. can be shown only on full hour, allways or never.
        if self._show_intro_text or (minutes < 5 and self._show_intro_text_full_hour):
            words += ["it-is"]
        # set minutes
        for start, end, range_words in MINUTE_RANGES:
            if start <= minutes < end:
                words += range_words
                break
        # adjust the hour based on minutes
        temp_hours = hours
        if minutes >= NEXT_HOUR_START[self._clock_language]:
            temp_hours = (hours + 1) % 12
        words.append(HOUR_WORDS[temp_hours])
        # on full hours
        if minutes < 5:
            words += ["oclock"]
        # am/pm
        if self._show_ampm:
            if time.hour >= 12:
                words.append("pm")
            else:
                words.append("am")

        # specials
        specials = [i < minutes % 5 for i in range(INDEX_SPECIAL_LENGTH)]

        return words, specials

    def get_letter_component(self, idx: int) -> Component:
        return Component(INDEX_LETTER_START + idx, f"l{idx + 1}")

    def get_special_component(self, idx: int) -> Component:
        return Component(INDEX_SPECIAL_START + idx, f"s{idx + 1}")

    def _refresh_notif(self) -> None:
        if not self._show_notifications:
            return
        notification = self.app.controller["notification"]
        notif_blinker = notification.blinker
        if notif_blinker.new_notifications:
            color = self.get_color("component_accent")
            visible = datetime.datetime.now().second % 2 == 0
        else:
            color = self.get_color("component_text")
            visible = notification.has_notifications()
        self.update_function_component(
            self.COMPONENTS.t_notif.name,
            icon=ICO_MESSAGE,
            visible=visible,
            color=color,
        )

    # callback

    def callback_update_time(self, cb_args: dict[str, Any]) -> None:
        if self.app.device.device_info.get("display_state") == "off":
            return
        self.update_interface()

    def process_event(self, event: HAUIEvent) -> None:
        super().process_event(event)

    def callback_function_component(self, fnc_id: str, fnc_name: str) -> None:
        if fnc_id == self.COMPONENTS.t_notif.name:
            navigation = self.app.controller["navigation"]
            navigation.open_panel(SysPanelKey.POPUP_NOTIFY)
