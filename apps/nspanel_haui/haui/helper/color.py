import colorsys
import math
import random

from .value import scale


def generate_color_palette(rgb_color, palette_type, seed=None, num_colors=6):
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
    hsv_background = colorsys.rgb_to_hsv(
        rgb_color[0] / 255, rgb_color[1] / 255, rgb_color[2] / 255
    )
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


def rgb_brightness(rgb_color, brightness):
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


def rgb_to_hsv(r, g, b):
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


def hsv_to_rgb(h, s, v):
    """Converts HSV values to RGB.

    Args:
        h (float): H value
        s (float): S value
        v (float): V value

    Returns:
        tuple[float, float, float]: RGB Values
    """
    hsv = colorsys.hsv_to_rgb(h, s, v)
    return tuple(round(i * 255) for i in hsv)


def color_to_pos(rgb, wh):
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


def pos_to_color(x, y, wh):
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


def rgb_to_rgb565(rgb_color):
    """Converts a RGB888 color to a RGB565 color.

    Args:
        rgb_color (list|tuple): rgb colors

    Returns:
        int: RGB565 color
    """
    red = rgb_color[0]
    green = rgb_color[1]
    blue = rgb_color[2]
    return (int(red >> 3) << 11) | (int(green >> 2) << 5) | (int(blue >> 3))


def rgb565_to_rgb(rgb565_color):
    """Converts a RGB565 color to a RGB888 color.

    Args:
        rgb565_color (int): rgb565 color

    Returns:
        list: RGB888 color
    """
    red = (rgb565_color & 0xF800) >> 11
    green = (rgb565_color & 0x07E0) >> 5
    blue = rgb565_color & 0x001F
    # scale the values up to 8 bits (0-255)
    red = (red * 255) // 31
    green = (green * 255) // 63
    blue = (blue * 255) // 31
    # return the rgb values
    return [red, green, blue]
