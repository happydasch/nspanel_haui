from __future__ import annotations

import colorsys
import logging
import re

from .value import scale

_LOGGER = logging.getLogger(__name__)


def rgb_brightness(rgb_color: tuple[int, int, int], brightness: int | None) -> list[int]:
    """Returns a dimmed RGB value.

    Args:
        rgb_color (list): RGB color to dim
        brightness (int): Brightness value

    Returns:
        list[int, int, int]: Dimmed RGB color
    """
    # rescale the 0-255 brightness so the colour is never lost
    brightness = 0 if brightness is None else int(brightness)
    brightness = int(scale(brightness, (0, 255), (96, 255)))
    red = rgb_color[0] / 255 * brightness
    green = rgb_color[1] / 255 * brightness
    blue = rgb_color[2] / 255 * brightness
    return [int(red), int(green), int(blue)]


def rgb_to_hsv(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Converts RGB values to HSV.

    Args:
        r (float): Red value
        g (float): Green vlaue
        b (float): Blue vlaue

    Returns:
        tuple[float, float, float]: HSV values
    """
    hsv = colorsys.rgb_to_hsv(r, g, b)
    return hsv


def hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Converts HSV values to RGB.

    Args:
        h (float): H value
        s (float): S value
        v (float): V value

    Returns:
        tuple[float, float, float]: RGB Values
    """
    hsv = colorsys.hsv_to_rgb(h, s, v)
    return (round(hsv[0] * 255), round(hsv[1] * 255), round(hsv[2] * 255))


def color_to_rect_pos(rgb: tuple[int, int, int], w: int, h: int) -> tuple[int, int]:
    """Converts an RGB color to a 2D (x, y) position within a rectangle.

    Maps: X = hue * w, Y = (1 - saturation) * h.
    Value is ignored (always full, controlled separately via brightness slider).

    Args:
        rgb: RGB color tuple (r, g, b) with values 0-255.
        w: Width of the color rectangle in pixels.
        h: Height of the color rectangle in pixels.

    Returns:
        (x, y) position within the rectangle.
    """
    hsv = rgb_to_hsv(rgb[0], rgb[1], rgb[2])
    x = round(hsv[0] * w)
    y = round(h - hsv[1] * h)  # inverted: 0 sat at top, 1 sat at bottom
    return (x, y)


def rect_pos_to_color(x: float, y: float, w: int, h: int) -> tuple[int, int, int]:
    """Converts a 2D (x, y) position within a rectangle to an RGB color.

    Maps: hue = x / w, saturation = 1 - y / h.

    Args:
        x: X position (0 = left edge).
        y: Y position (0 = top edge).
        w: Width of the color rectangle in pixels.
        h: Height of the color rectangle in pixels.

    Returns:
        RGB color tuple (r, g, b) with values 0-255.
    """
    hue = max(0.0, min(1.0, x / w))
    sat = max(0.0, min(1.0, 1.0 - y / h))
    return hsv_to_rgb(hue, sat, 1.0)


def rgb_to_rgb565(rgb_color: list | tuple) -> int:
    """Converts a RGB888 color to a RGB565 color.

    Args:
        rgb_color (list|tuple): rgb colors

    Returns:
        int: RGB565 color
    """

    red = int(rgb_color[0])
    green = int(rgb_color[1])
    blue = int(rgb_color[2])
    return (int(red >> 3) << 11) | (int(green >> 2) << 5) | (int(blue >> 3))


def rgb565_to_rgb(rgb565_color: int) -> tuple[int, int, int]:
    """Converts a RGB565 color to a RGB888 color.

    Args:
        rgb565_color (int): rgb565 color

    Returns:
        tuple[int, int, int]: RGB888 color
    """
    red = (rgb565_color & 0xF800) >> 11
    green = (rgb565_color & 0x07E0) >> 5
    blue = rgb565_color & 0x001F
    # scale the values up to 8 bits (0-255)
    red = (red * 255) // 31
    green = (green * 255) // 63
    blue = (blue * 255) // 31
    # return the rgb values
    return (red, green, blue)


def mix_rgb565(background: int, foreground: int, ratio: float) -> int:
    """Mixes an RGB565 foreground into an RGB565 background.

    Args:
        background (int): rgb565 color the result sits on
        foreground (int): rgb565 color mixed into it
        ratio (float): how far towards the foreground, 0 keeps the background
            and 1 returns the foreground

    Returns:
        int: the mixed rgb565 color
    """
    back = rgb565_to_rgb(background)
    front = rgb565_to_rgb(foreground)
    return rgb_to_rgb565([round(b + (f - b) * ratio) for b, f in zip(back, front, strict=True)])


def parse_color_value(value: int | str | list | tuple) -> int:
    """Parse a color value in any supported format into an RGB565 int.

    Handles:
    - ``int``: passed through directly (assumed RGB565).
    - ``#rrggbb`` hex string format (from frontend color picker).
    - ``list`` / ``tuple`` of 3 ints: converted via ``rgb_to_rgb565``.
    - Integer string: converted to int directly.

    Args:
        value: A color in one of the supported formats.

    Returns:
        RGB565 integer color value. Returns 0 (black) for an empty or invalid
        value and logs a warning: rendering continues instead of aborting the
        whole command batch over one bad color.
    """
    if isinstance(value, int):
        return value

    if isinstance(value, (list, tuple)):
        return rgb_to_rgb565(value)

    if not isinstance(value, str) or not value.strip():
        return _invalid_color(value)

    stripped = value.strip()

    # Handle "#rrggbb" hex format (from frontend color picker)
    if re.match(r"^#([0-9a-fA-F]{6})$", stripped):
        hex_str = stripped[1:]
        return rgb_to_rgb565(
            [
                int(hex_str[0:2], 16),
                int(hex_str[2:4], 16),
                int(hex_str[4:6], 16),
            ]
        )

    # Try direct integer parsing (e.g. "65535")
    try:
        return int(stripped)
    except ValueError:
        return _invalid_color(value)


def _invalid_color(value: object) -> int:
    _LOGGER.warning("Invalid color value %r, using black", value)
    return 0


def contrast_ratio(foreground: int, background: int) -> float:
    """Return the WCAG contrast ratio of an RGB565 foreground on a background.

    Args:
        foreground (int): rgb565 color of the text or icon
        background (int): rgb565 color it is drawn on

    Returns:
        float: the contrast ratio, from 1.0 (invisible) to 21.0 (black on white)
    """

    def relative_luminance(color: int) -> float:
        red, green, blue = rgb565_to_rgb(color)

        def linear(value: int) -> float:
            channel = value / 255
            return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

        return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)

    low, high = sorted((relative_luminance(foreground), relative_luminance(background)))
    return (high + 0.05) / (low + 0.05)
