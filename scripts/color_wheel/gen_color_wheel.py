import colorsys
import math

from PIL import Image, ImageDraw

width = 200
height = 200
filename = "output.png"


def hsv_to_rgb(h, s, v):
    hsv = colorsys.hsv_to_rgb(h, s, v)
    return tuple(round(i * 255) for i in hsv)


def pos_to_color(x, y, wh):
    r = wh / 2
    x = round((x - r) / r * 100) / 100
    y = round((r - y) / r * 100) / 100

    r = math.sqrt(x * x + y * y)

    # Outside the circle r > 1; the clamp is disabled, so the corners saturate.
    sat = r
    hsv = (math.degrees(math.atan2(y, x)) % 360 / 360, sat, 1)
    rgb = hsv_to_rgb(hsv[0], hsv[1], hsv[2])
    return rgb


img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rectangle((0, 0, width, height), fill="#1b1b1b")
for y in range(height):
    for x in range(width):
        color = pos_to_color(x, y, width)
        if color is not None:
            draw.point((x, y), fill=color)

img.save(filename)
