import struct

from PIL import Image

image = Image.open("image.png")

width, height = image.size
pixel_list = []
for y in range(height):
    for x in range(width):
        r, g, b = image.getpixel((x, y))
        rgb565 = ((r & 0xF8) << 8) + ((g & 0xFC) << 3) + (b >> 3)
        pixel_list.append(rgb565)
pixel_string = b""
for pixel in pixel_list:
    pixel_string += struct.pack(">H", pixel)

print(f"pixelData~{width}~{height}~{pixel_string}")
