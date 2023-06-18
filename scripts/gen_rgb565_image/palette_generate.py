from PIL import Image


def rgb565_to_rgb(color):
    # Extract the red, green, and blue components from the 16-bit RGB565 color
    red = (color & 0xF800) >> 11
    green = (color & 0x07E0) >> 5
    blue = color & 0x001F

    # Scale the values from 5-bit to 8-bit
    red = (red * 527 + 23) >> 6
    green = (green * 259 + 33) >> 6
    blue = (blue * 527 + 23) >> 6

    return (red, green, blue)


# define image size
width = 256
height = 256

# create a new image with RGB mode
img = Image.new('RGB', (width, height))

# create all colors
for i in range(256*256):
    x = int(i % 256)
    y = int((i - (i % 256)) / 256)
    img.putpixel((x, y), rgb565_to_rgb(i))

# save the image
img.save('rgb565.png')
