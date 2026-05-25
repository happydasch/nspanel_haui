from __future__ import annotations

import colorsys
import math
import random
import re

from .value import scale


def generate_color_palette(
    rgb_color: tuple[int, int, int],
    palette_type: str,
    seed: int | None = None,
    num_colors: int = 6,
) -> list[tuple[int, int, int]]:
    """Generates random color matching the provided color.

    Args:
        rgb_color (list): RGB color
        palette_type (str): Palette type: vibrant, pastel, light
        seed (int, optional): Seed to use for random color generation. Defaults to random.
        num_colors (int, optional): Number of colors to generate. Defaults to 6.

    Returns:
        tuple: A list with rgb values
    """
    if seed is None:
        seed = random.randint(0, 1000)
    random.seed(seed)
    # Guard against empty or unknown palette_type — return unmodified base color
    if not palette_type or palette_type not in (
        "vibrant",
        "pastel",
        "light",
        "lighten",
        "dark",
        "darken",
    ):
        return [rgb_color] * num_colors
    hsv_background = colorsys.rgb_to_hsv(rgb_color[0] / 255, rgb_color[1] / 255, rgb_color[2] / 255)
    colors = []
    for _ in range(num_colors):
        if palette_type == "vibrant":
            # Generate vibrant colors by randomizing hue, saturation, and value
            hue = random.random()
            saturation = random.uniform(0.7, 1.0)
            value = random.uniform(0.7, 1.0)
        elif palette_type == "pastel":
            # Generate pastel colors by reducing saturation and increasing value
            hue = random.random()
            saturation = random.uniform(0.2, 0.5)
            value = random.uniform(0.7, 1.0)
        elif palette_type == "light":
            # Generate light colors by increasing random value
            hue = hsv_background[0]
            saturation = hsv_background[1]
            value = random.uniform(0.7, 0.8)
        elif palette_type == "lighten":
            # Generate light colors by decreasing value
            hue = hsv_background[0]
            saturation = hsv_background[1]
            value = 0.8
        elif palette_type == "dark":
            # Generate light colors by decreasing random value
            hue = hsv_background[0]
            saturation = hsv_background[1]
            value = random.uniform(0.2, 0.3)
        elif palette_type == "darken":
            # Generate light colors by decreasing value
            hue = hsv_background[0]
            saturation = hsv_background[1]
            value = 0.2
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        rgb = int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
        colors.append(rgb)
    return colors


def rgb_brightness(rgb_color: tuple[int, int, int], brightness: int | None) -> list[int]:
    """Returns a dimmed RGB value.

    Args:
        rgb_color (list): RGB color to dim
        brightness (int): Brightness value

    Returns:
        list[int, int, int]: Dimmed RGB color
    """
    # brightness values are in range 0-255
    # to make sure that the color is not completly lost we need to rescale
    # this to 96-255
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


def color_to_pos(rgb: tuple[int, int, int], wh: int) -> tuple[int, int]:
    """Converts a RGB color to 2d position data.

    Args:
        rgb (tuple): RGB value
        wh (int): WH value

    Returns:
        tuple[float, float]: XY pos
    """
    r = wh / 2
    hsv = rgb_to_hsv(rgb[0], rgb[1], rgb[2])
    sat = hsv[1]
    angle = hsv[0] * 2 * math.pi
    x = round(r * sat * math.cos(angle) + r)
    y = round(r - r * sat * math.sin(angle))
    return (x, y)


def pos_to_color(x: float, y: float, wh: int) -> tuple[int, int, int]:
    """Converts 2d position data to a RGB color.

    Args:
        x (int): X Pos
        y (int): Y Pos
        wh (int): WH value

    Returns:
        tuple[float, float, float]: RGB Value
    """
    r = wh / 2
    x = round((x - r) / r * 100) / 100
    y = round((r - y) / r * 100) / 100
    #
    r = math.sqrt(x * x + y * y)
    sat = r = max(0, min(r, 1))
    hsv = (math.degrees(math.atan2(y, x)) % 360 / 360, sat, 1)
    rgb = hsv_to_rgb(hsv[0], hsv[1], hsv[2])
    return rgb


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


def parse_color_value(value: int | str | list | tuple) -> int:
    """Parse a color value in any supported format into an RGB565 int.

    Handles:
    - ``int``: passed through directly (assumed RGB565).
    - ``[r, g, b]`` bracket string format (legacy configs).
    - ``#rrggbb`` hex string format (from frontend color picker).
    - ``list`` / ``tuple`` of 3 ints: converted via ``rgb_to_rgb565``.
    - Integer string: converted to int directly.

    Args:
        value: A color in one of the supported formats.

    Returns:
        RGB565 integer color value. Returns 0 for empty/invalid strings.
    """
    if isinstance(value, int):
        return value

    if isinstance(value, (list, tuple)):
        return rgb_to_rgb565(value)

    if not isinstance(value, str):
        return 0

    stripped = value.strip()
    if not stripped:
        return 0

    # Handle "[r,g,b]" string format (legacy configs)
    rgb_match = re.match(
        r"\[\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\]",
        stripped,
    )
    if rgb_match:
        return rgb_to_rgb565(
            [
                int(rgb_match.group(1)),
                int(rgb_match.group(2)),
                int(rgb_match.group(3)),
            ]
        )

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
    except (ValueError, TypeError):
        return 0
