"""Field-level rules for the options of a panel.

The rules are data on ``PageOption`` (``required``, ``min``, ``max``, ``domain``,
``choices``, ``max_items``); this module checks a value against them.
``validate_panels`` refuses a saved panel that breaks one, and the editor runs
the same rules as you type (``frontend/option-rules.js`` mirrors this module;
``tests/fixtures/option_rules_cases.json`` keeps the two equal).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .mapping.const import InternalItemType

if TYPE_CHECKING:
    from .mapping.descriptor import PageDescriptor, PageOption

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
_INTERNAL_PREFIXES = tuple(f"{internal}:" for internal in InternalItemType)


@dataclass(frozen=True)
class OptionError:
    """One broken rule.

    ``field`` is the option key, or ``"<key>.<index>"`` for one entry of a list.
    ``kind`` is one of ``required``, ``domain``, ``number``, ``min``, ``max``,
    ``choice``, ``max_items``, ``color``.
    """

    field: str
    kind: str
    message: str


def _item_id(value: Any) -> Any:
    """The ``item`` of an item value: a dict ``{"item": ...}`` or the plain id."""
    return value.get("item") if isinstance(value, dict) else value


def _is_internal(item_id: str) -> bool:
    return item_id in tuple(InternalItemType) or item_id.startswith(_INTERNAL_PREFIXES)


def _domain_error(field: str, item_id: Any, domain: str | None) -> list[OptionError]:
    """A wrong domain for an entity id; internal items and blanks are not entities."""
    if not domain or not isinstance(item_id, str) or not item_id or _is_internal(item_id):
        return []
    if item_id.split(".", 1)[0] == domain:
        return []
    return [OptionError(field, "domain", f"Use a {domain} entity, not {item_id}")]


def _number_errors(option: PageOption, value: Any) -> list[OptionError]:
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not is_number or (option.kind == "int" and not float(value).is_integer()):
        return [OptionError(option.key, "number", f"{value!r} is not a number")]
    if option.min is not None and value < option.min:
        return [OptionError(option.key, "min", f"Use {option.min:g} or more")]
    if option.max is not None and value > option.max:
        return [OptionError(option.key, "max", f"Use {option.max:g} or less")]
    return []


def _is_color(value: Any) -> bool:
    """Whether ``parse_color_value`` (``haui/utils/color.py``) reads ``value`` as a colour."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0 <= value <= 0xFFFF
    if isinstance(value, (list, tuple)):
        return len(value) == 3 and all(
            isinstance(part, int) and not isinstance(part, bool) and 0 <= part <= 255
            for part in value
        )
    if isinstance(value, str):
        text = value.strip()
        if _HEX_COLOR.match(text):
            return True
        return text.isdigit() and int(text) <= 0xFFFF
    return False


def _choice_values(option: PageOption) -> list[str]:
    return [value for value, _label in option.choices or []]


def _is_template(value: Any) -> bool:
    return isinstance(value, str) and ("{{" in value or "{%" in value)


def option_errors(option: PageOption, value: Any, *, popup: bool = False) -> list[OptionError]:
    """Check one option's ``value`` against its rules.

    Args:
        option: The option as the page declares it.
        value: The saved value; ``None`` means not set.
        popup: The panel is saved under a popup key, so its ``item`` comes from
            the context the popup opens with and may stay empty.

    Returns:
        The broken rules, in field order; empty when the value is fine.
    """
    kind = option.kind
    if kind == "item":
        item_id = _item_id(value)
        if item_id == "" or (value is None and option.required):
            if option.required and not (popup and option.key == "item"):
                return [OptionError(option.key, "required", "Choose an entity")]
            return []
        return _domain_error(option.key, item_id, option.domain)
    if value is None:
        return []
    if kind in ("int", "float"):
        return _number_errors(option, value)
    if kind == "select":
        if value in _choice_values(option) or (option.allow_template and _is_template(value)):
            return []
        return [OptionError(option.key, "choice", f"{value!r} is not one of the listed values")]
    if kind == "color":
        if value == "" or _is_color(value):
            return []
        return [OptionError(option.key, "color", f"{value!r} is not a colour")]
    if kind in ("str", "generic"):
        if option.required and not str(value).strip():
            return [OptionError(option.key, "required", "Fill in this field")]
        return []
    if not isinstance(value, list):
        return []
    if kind == "list_items":
        choices = _choice_values(option)
        if not choices:
            return []
        return [
            OptionError(f"{option.key}.{index}", "choice", f"{entry!r} is not a listed value")
            for index, entry in enumerate(value)
            if entry not in choices
        ]
    if kind == "list_entities":
        errors: list[OptionError] = []
        for index, entry in enumerate(value):
            errors += _domain_error(f"{option.key}.{index}", _item_id(entry), option.domain)
        return errors
    if kind == "item_list":
        errors = []
        if option.max_items is not None and len(value) > option.max_items:
            errors.append(
                OptionError(option.key, "max_items", f"Use at most {option.max_items} items")
            )
        for index, entry in enumerate(value):
            if _item_id(entry) == "":
                errors.append(OptionError(f"{option.key}.{index}", "required", "Choose an entity"))
        return errors
    return []


def panel_option_errors(
    panel: dict[str, Any], descriptor: PageDescriptor, *, popup: bool
) -> list[OptionError]:
    """Check every option of ``panel`` against the rules of its page type.

    Args:
        panel: The saved panel config.
        descriptor: The descriptor of the panel's type.
        popup: The panel is saved under a popup key (see ``option_errors``).

    Returns:
        The broken rules of all options, in the descriptor's order.
    """
    errors: list[OptionError] = []
    for option in descriptor.options:
        errors += option_errors(option, panel.get(option.key), popup=popup)
    return errors
