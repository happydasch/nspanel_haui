from PIL import Image


def rgb565_to_rgb(color):
    # Split the 16-bit RGB565 color into its 5-6-5 components.
    red = (color & 0xF800) >> 11
    green = (color & 0x07E0) >> 5
    blue = color & 0x001F

    # Scale 5 bits up to 8.
    red = (red * 527 + 23) >> 6
    green = (green * 259 + 33) >> 6
    blue = (blue * 527 + 23) >> 6

    return (red, green, blue)


width = 256
height = 256

img = Image.new("RGB", (width, height))

for i in range(256 * 256):
    x = int(i % 256)
    y = int((i - (i % 256)) / 256)
    img.putpixel((x, y), rgb565_to_rgb(i))

img.save("rgb565.png")
