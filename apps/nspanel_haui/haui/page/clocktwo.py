import datetime
import re
import threading
from typing import List, Tuple

from ..mapping.background import BACKGROUNDS
from ..mapping.color import COLORS

from ..helper.icon import get_icon
from ..abstract.panel import HAUIPanel


from . import HAUIPage


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
    )
}

MATRIX_WORDS = {
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
        "am": [],  # -
        "pm": [],  # -
        "to": {
            "*": [33, 34, 35],  # vor
            ("twenty-u", "five-u"): [],  # -
            ("quarter-u"): [],  # -
        },
        "past": {
            "*": [40, 41, 42, 43],  # nach
            ("twenty-u", "five-u"): [],  # -
        },
        #
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
        "am": [],  # -
        "pm": [],  # -
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
    "twelve", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "eleven"
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
    (55, 60, ["five-u", "to"])
]

INDEX_LETTER_START = 2
INDEX_LETTER_LENGTH = 110
INDEX_SPECIAL_START = 113
INDEX_SPECIAL_LENGTH = 4


class ClockTwoPage(HAUIPage):

    # components, skipping l1-110, s1-4
    TXT_NOTIF = (117, "tNotif")

    DISPLAY_UPDATE_INTERVAL = 1.0

    ICO_SPECIAL = get_icon("mdi:circle-medium")

    _timer_time = None
    _timer_notifications = None
    _show_notifications = True
    _new_notifications = False
    _letter_current_state = []
    _special_current_state = []
    _off_color = COLORS["component_background"]
    _letter_color = COLORS["component"]
    _special_color = COLORS["component_accent"]
    _show_ampm = False
    _show_intro_text = True
    _show_intro_text_full_hour = False
    _clock_language = "en"
    _clock_letters = []

    # panel

    def create_panel(self, panel: HAUIPanel):
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
        self._show_intro_text_full_hour = panel.get("show_intro_text_full_hour", self._show_intro_text_full_hour)
        if background in BACKGROUNDS:
            self.send_cmd(f"clocktwo.background.val={BACKGROUNDS[background]}")

    def start_panel(self, panel: HAUIPanel):
        # time update callback
        time = datetime.time(0, 0, 0)
        self._timer_time = self.app.run_minutely(self.callback_update_time, time)
        # notification
        self._show_notifications = panel.get("show_notifications", True)
        self.set_function_component(
            self.TXT_NOTIF, self.TXT_NOTIF[1], visible=self._show_notifications)
        self.init_interface(panel)

    def render_panel(self, panel: HAUIPanel):
        self.update_interface()
        self.update_notifications()

    def stop_panel(self, panel: HAUIPanel):
        # cancel time timer
        if self._timer_time is not None:
            self.app.cancel_timer(self._timer_time)
            self._timer_time = None

    # clock

    def init_interface(self, panel):
        pattern = re.compile(r"\[([^\]]+)\]|.")
        self._clock_letters = [
            match.group(1) if match.group(1)
            else match.group(0)
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
            specials.append(self.ICO_SPECIAL)
        components = letter_components + special_components
        components_text = self._clock_letters + specials
        for component, component_text in zip(components, components_text):
            self.start_rec_cmd()
            self.set_component_text_color(component, self._off_color)
            self.set_component_text(component, text=component_text)
            self.stop_rec_cmd(True)
        self._letter_current_state = [False] * INDEX_LETTER_LENGTH
        self._special_current_state = [False] * INDEX_SPECIAL_LENGTH

    def update_interface(self):
        current_time = datetime.datetime.now()
        letters_active, specials_active, time_words = self.get_matrix_from_time(
            current_time)

        matrix_text = ""
        for letter_index in range(INDEX_LETTER_LENGTH):
            if letters_active[letter_index] is True:
                if letter_index > 0 and letters_active[letter_index - 1] is False:
                    matrix_text += " "
                matrix_text += self._clock_letters[letter_index]
        self.log(f"text: {matrix_text} for words: {' '.join(time_words)}")
        for i, old, new in zip(
            range(INDEX_LETTER_LENGTH),
            self._letter_current_state,
            letters_active
        ):
            component = self.get_letter_component(i)
            if old != new:
                if new is True:
                    self.set_component_text_color(component, self._letter_color)
                else:
                    self.set_component_text_color(component, self._off_color)
                self._letter_current_state[i] = new
        for i, old, new in zip(
            range(INDEX_SPECIAL_LENGTH),
            self._special_current_state,
            specials_active
        ):
            component = self.get_special_component(i)
            if old != new:
                if new is True:
                    self.set_component_text_color(component, self._special_color)
                else:
                    self.set_component_text_color(component, self._off_color)
                self._special_current_state[i] = new

    def get_matrix_from_time(self, time: datetime) -> Tuple[List[int], List[bool], List[str]]:
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
                    lit_key = None
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

    def get_words_from_time(self, time: datetime) -> List[str]:
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

    def get_letter_component(self, idx: int) -> Tuple[int, str]:
        return (INDEX_LETTER_START + idx, f"l{idx+1}")

    def get_special_component(self, idx: int) -> Tuple[int, str]:
        return (INDEX_SPECIAL_START + idx, f"s{idx+1}")

    def update_notifications(self):
        if not self._show_notifications:
            return
        notification = self.app.controller["notification"]
        if self._new_notifications:
            color = COLORS["component_accent"]
        else:
            color = COLORS["component"]
        if self._new_notifications:
            if datetime.datetime.now().second % 2:
                visible = False
            else:
                visible = True
        else:
            visible = notification.has_notifications()
        notif_kwargs = {
            "icon": self.ICO_MESSAGE,
            "visible": visible,
            "color": color,
        }
        self.update_function_component(self.TXT_NOTIF[1], **notif_kwargs)
        if self._new_notifications:
            self._timer_notifications = threading.Timer(
                self.DISPLAY_UPDATE_INTERVAL, self.update_notifications
            )
            self._timer_notifications.start()

    # callback

    def callback_update_time(self, cb_args):
        if self.app.device.sleeping:
            return
        self.update_interface()
