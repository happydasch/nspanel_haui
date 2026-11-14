"""Cycle cards shared by the clock and weather pages.

Both pages show a big text widget (``tTime``) with a line below it (``tDate``).
The pair rotates through the panel's cards: the time, a date card, the outside
and inside temperature and any entities the panel lists.  Only the time card is
on by default, so nothing cycles until the panel enables more cards.  Every
card is fitted to its widget with the display font's glyph widths, so a card
that would be clipped switches to a shorter form ("21°C" -> "21°") or, with no
shorter form left, to a smaller font (the date card always keeps its weekday:
"Mon 16").  The card on screen redraws as soon as its source changes.
"""

from __future__ import annotations

import zoneinfo
from collections.abc import Callable
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

from ...mapping.descriptor import PageOption, _
from ...utils.datetime import format_datetime, get_date_localized, get_time_localized
from ...utils.text import TextBox, fit_line, fits_line, has_glyphs
from ...utils.value import format_number

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from ....hub.app import NSPanelHAUI
    from ..component import Component, ComponentRegistry
    from ..haui_event import HAUIEvent
    from ..haui_item import HAUIItem
    from ..haui_panel import HAUIPanel

_SECTION = _("Cycle cards")

CARD_OPTIONS: list[PageOption] = [
    PageOption(
        key="show_time_time",
        kind="bool",
        default=True,
        label=_("Show time"),
        description=_("Show current time as a cycle card."),
        section=_SECTION,
    ),
    PageOption(
        key="show_time_date",
        kind="bool",
        default=False,
        label=_("Show date"),
        description=_("Show current date as a cycle card."),
        section=_SECTION,
    ),
    PageOption(
        key="show_time_outside_temp",
        kind="bool",
        default=False,
        label=_("Show outside temperature"),
        description=_("Show outside temperature as a cycle card."),
        section=_SECTION,
    ),
    PageOption(
        key="show_time_inside_temp",
        kind="bool",
        default=False,
        label=_("Show inside temperature"),
        description=_("Show inside (NSPanel) temperature as a cycle card."),
        section=_SECTION,
    ),
    PageOption(
        key="card_items",
        kind="item_list",
        max_items=4,
        label=_("Card entities"),
        description=_("Entities shown as extra cycle cards: value large, name below (4 max)."),
        section=_SECTION,
    ),
    PageOption(
        key="card_interval",
        kind="int",
        min=1,
        default=5,
        label=_("Seconds per card"),
        description=_("How long each cycle card is shown."),
        section=_SECTION,
    ),
    PageOption(
        key="card_pause",
        kind="int",
        min=0,
        default=15,
        label=_("First card pause"),
        description=_("Seconds the first card stays after a full cycle."),
        section=_SECTION,
    ),
]
_DEFAULTS: dict[str, Any] = {opt.key: opt.default for opt in CARD_OPTIONS}


def _option(panel: HAUIPanel, key: str) -> Any:
    """The panel's value for a card option, or the option's default."""
    return panel.get(key, _DEFAULTS[key])


class CardBox(NamedTuple):
    """A cycle card widget: its drawing area and font, from the HMI."""

    box: TextBox
    font: int


class Card(NamedTuple):
    """One cycle card; ``item`` is set for an entity card."""

    kind: str  # time, date, outside_temperature, inside_temperature or item
    item: HAUIItem | None = None


class CycleCardsMixin:
    """Rotates ``tTime``/``tDate`` through the panel's cycle cards.

    The host declares ``t_time``, ``t_date`` and ``t_main_icon`` components and
    ``CARD_BOXES`` (the two widgets per orientation, checked against the HMI
    layouts by a test), and provides ``_weather_item``, ``_temp_unit``,
    ``TEMP_PRECISION`` and ``update_main_weather()`` for its header.
    """

    CARD_BOXES: ClassVar[dict[str, dict[str, CardBox]]]
    TEMP_PRECISION: ClassVar[int]

    if TYPE_CHECKING:
        app: NSPanelHAUI
        panel: HAUIPanel | None
        COMPONENTS: ClassVar[ComponentRegistry]
        _weather_item: HAUIItem | None
        _temp_unit: str

        @property
        def rec_cmd(self) -> AbstractContextManager[None]: ...
        def translate(self, text: str) -> str: ...
        def get_locale(self) -> str: ...
        def get_color(self, key: str) -> int: ...
        def set_component_text_color(
            self, component: Component, color: int | str | list | tuple
        ) -> None: ...
        def send_cmd(self, cmd: str) -> None: ...
        def set_function_component(
            self, component: Any, fnc_id: str, fnc_name: str | None = None, **fnc_args: Any
        ) -> None: ...
        def update_function_component(
            self, fnc_id: str, update_fnc_name: str | None = None, **kwargs: Any
        ) -> None: ...
        def get_inside_temp_entity_id(self, panel: HAUIPanel | None = None) -> str | None: ...
        def option(self, panel: HAUIPanel, key: str) -> Any: ...
        def _build_items_from_panel(self, panel: HAUIPanel, *keys: str) -> list[HAUIItem]: ...
        def listen_items(self, items: list[HAUIItem], render: Callable[[], None]) -> None: ...
        def add_item_listener(
            self, item_id: str, callback: Callable, attribute: str | None = None
        ) -> str: ...
        def update_main_weather(self) -> None: ...

    def _init_cards(self) -> None:
        """Sets the card defaults; call from ``prepare()``."""
        self._cycle_cards: list[Card] = [Card("time")]
        self._current_card_index = 0
        self._card_timer = 0
        self._cycle_state = "cycling"  # "cycling" or "paused" on the first card
        self._card_interval: int = _DEFAULTS["card_interval"]
        self._card_pause: int = _DEFAULTS["card_pause"]
        self._tick_handle: Any = None
        self._time_font: int | None = None  # font last sent to tTime

    def _start_cards(self, panel: HAUIPanel, has_weather: bool) -> None:
        """Builds the panel's cards and starts the cycle; call from ``start_panel()``.

        Args:
            panel: The panel being started.
            has_weather: Whether the panel has a weather entity; without one
                there is no outside temperature to show.
        """
        self._card_interval = int(_option(panel, "card_interval"))
        self._card_pause = int(_option(panel, "card_pause"))
        cards = []
        if _option(panel, "show_time_time"):
            cards.append(Card("time"))
        if _option(panel, "show_time_date"):
            cards.append(Card("date"))
        if _option(panel, "show_time_outside_temp") and has_weather:
            cards.append(Card("outside_temperature"))
        if _option(panel, "show_time_inside_temp"):
            cards.append(Card("inside_temperature"))
        cards += [Card("item", item) for item in self._build_items_from_panel(panel, "card_items")]
        self._cycle_cards = cards or [Card("time")]
        self._current_card_index = 0
        self._card_timer = 0
        self._cycle_state = "cycling"
        if self._tick_handle is None and len(self._cycle_cards) > 1:
            self._tick_handle = self.app.run_every(self._tick, 0, 1.0)
        for component in (self.COMPONENTS.t_time, self.COMPONENTS.t_date):
            self.set_function_component(component, component.name, visible=True)
        # live updates: the inside sensor feeds the header and its card, entity
        # cards follow their entities
        if self.option(panel, "show_home_temp") or _option(panel, "show_time_inside_temp"):
            inside_temp_id = self.get_inside_temp_entity_id(panel)
            if inside_temp_id is not None:
                self.add_item_listener(inside_temp_id, self.callback_inside_temp)
        for card in self._cycle_cards:
            if card.item is not None:
                self.listen_items([card.item], partial(self._refresh_card, card))

    def _stop_cards(self) -> None:
        """Cancels the cycle timer; call from ``_stop_panel()``."""
        if self._tick_handle is not None:
            self.app.cancel_timer(self._tick_handle)
            self._tick_handle = None

    def _render_cards(self) -> None:
        """Shows the first card; call from ``render_panel()``."""
        self._current_card_index = 0
        self._card_timer = 0
        self._cycle_state = "cycling"
        # the widget may hold the HMI's font (page reload) or another panel's
        self._time_font = None
        self._render_cycle_card()

    def _refresh_card(self, *cards: Card) -> None:
        """Redraws the card on screen if it is one of *cards*."""
        if self._cycle_cards[self._current_card_index] in cards:
            self._render_cycle_card()

    # texts

    def _render_cycle_card(self) -> None:
        """Draws the current card into ``tTime`` and the line below it."""
        main_texts, sub_text = self._card_texts(self._cycle_cards[self._current_card_index])
        boxes = self.CARD_BOXES["portrait" if self.app.device.is_portrait else "landscape"]
        t_time, t_date = self.COMPONENTS.t_time, self.COMPONENTS.t_date
        time_box, date_box = boxes[t_time.name], boxes[t_date.name]
        self.set_component_text_color(t_time, self.get_color("text"))
        self.set_component_text_color(t_date, self.get_color("text"))
        main_text, font = self._fit_card(main_texts, time_box)
        if font != self._time_font:
            self.send_cmd(f"{t_time.name}.font={font}")
            self._time_font = font
        self.update_function_component(t_time.name, text=main_text)
        self.update_function_component(
            t_date.name, text=fit_line([sub_text], date_box.font, date_box.box)
        )
        self.send_cmd(f"ref {self.COMPONENTS.t_main_icon.name}")

    @staticmethod
    def _fit_card(texts: list[str], card_box: CardBox) -> tuple[str, int]:
        """The first of *texts* that fits the widget, and the font to draw it in.

        Every form is tried in the widget's font, then in each smaller font
        (display fonts grow with their id), so a card is drawn smaller rather
        than cut.  A font without a glyph for one of the characters is skipped:
        the big fonts hold Latin-1 only ("zamknięta" needs a smaller one).  Only
        when even font 0 is too large is the last form cut, in the widget's font.
        """
        for font in range(card_box.font, -1, -1):
            for text in texts:
                if has_glyphs(text, font) and fits_line(text, font, card_box.box):
                    return text, font
        return fit_line(texts, card_box.font, card_box.box), card_box.font

    def _card_texts(self, card: Card) -> tuple[list[str], str]:
        """The card's big text, preferred form first, and the line below it."""
        if card.kind == "time":
            timezone = self.app.get_timezone()
            timeformat = self.app.device.get_time_format()
            times = [get_time_localized(timeformat, timezone)]
            if "%p" in timeformat:
                times.append(get_time_localized(timeformat.replace("%p", "").strip(), timezone))
            return times, self._date_text(timezone)
        if card.kind == "date":
            timezone = self.app.get_timezone()
            now = datetime.now(zoneinfo.ZoneInfo(timezone))
            weekday = format_datetime(now, "%a", "E", self.get_locale())
            # no day-only form: the weekday is what the card adds to the time card
            return [f"{weekday} {now.day}"], self._date_text(timezone)
        if card.kind == "outside_temperature":
            outside = (
                self._weather_item.get_item_attr("temperature", "")
                if self._weather_item is not None
                else None
            )
            return self._temperature_texts(outside, self._temp_unit), self.translate("OUTSIDE")
        if card.kind == "inside_temperature":
            entity_id = self.get_inside_temp_entity_id(self.panel)
            inside = self.app.get_item(entity_id).get_state() if entity_id is not None else None
            unit = self._temp_unit if self._weather_item is not None else "°C"
            return self._temperature_texts(inside, unit), self.translate("INSIDE")
        if card.kind == "item" and card.item is not None:
            return self._item_texts(card.item), card.item.get_name()
        raise ValueError(f"Unknown cycle card: {card}")

    def _date_text(self, timezone: str) -> str:
        device = self.app.device
        return get_date_localized(
            device.get_date_format(), device.get_date_format_locale(), device.get_locale(), timezone
        )

    def _temperature_texts(self, value: Any, unit: str) -> list[str]:
        """``21°C``, then ``21°`` for a widget too narrow for the unit; ``--`` when unknown."""
        temp = "--"
        if value not in (None, "", "unavailable", "unknown"):
            try:
                rounded = round(float(value), self.TEMP_PRECISION)
            except ValueError, TypeError:
                pass
            else:
                temp = format_number(rounded if self.TEMP_PRECISION else int(rounded))
        texts = [f"{temp}{unit}"]
        if unit.startswith("°") and unit != "°":
            texts.append(f"{temp}°")
        return texts

    @staticmethod
    def _item_texts(item: HAUIItem) -> list[str]:
        """An entity's value with its unit, then rounder numbers, then without the unit."""
        value = item.get_value()
        # a configured value template carries its own formatting
        unit = (
            ""
            if item.get("value", None)
            else str(item.get_item_attr("unit_of_measurement", "") or "")
        )
        numbers = [value]
        try:
            number = float(value)
            numbers += [format_number(round(number, 1)), str(round(number))]
        except ValueError, OverflowError:
            pass
        texts = []
        if unit:
            separator = "" if unit.startswith("°") or unit == "%" else " "
            texts = [f"{n}{separator}{unit}" for n in numbers]
        return list(dict.fromkeys([*texts, *numbers]))

    # cycle

    def _tick(self, _data: dict | None = None) -> None:
        """Called every second. Advance cycle card when interval elapses."""
        # Only the card animation pauses while dark.  Content callbacks keep
        # drawing: with a hub connected the Nextion stays awake at brightness
        # 0, and a wake touch lights the backlight before the hub can redraw.
        if self.app.device.device_info.get("display_state") == "off":
            return
        self._card_timer += 1
        threshold = self._card_pause if self._cycle_state == "paused" else self._card_interval
        if self._card_timer >= threshold:
            with self.rec_cmd:
                self._advance_card()

    def _advance_card(
        self, _event: HAUIEvent | None = None, _component: Component | None = None
    ) -> None:
        """Advance to the next cycle card or enter/exit pause state."""
        if self._cycle_state == "paused":
            # Pause period over — start a new cycle from the beginning
            self._cycle_state = "cycling"
            self._current_card_index = 0
            self._card_timer = 0
            self._render_cycle_card()
            return

        next_index = self._current_card_index + 1
        if next_index >= len(self._cycle_cards):
            # Last card shown — enter pause on the first card
            self._cycle_state = "paused"
            self._current_card_index = 0
            self._card_timer = 0
            self._render_cycle_card()
            return

        self._current_card_index = next_index
        self._card_timer = 0
        self._render_cycle_card()

    # callback

    def callback_inside_temp(
        self, item: str, attribute: str, old: Any, new: Any, kwargs: dict[str, Any]
    ) -> None:
        with self.rec_cmd:
            self.update_main_weather()
            self._refresh_card(Card("inside_temperature"))
