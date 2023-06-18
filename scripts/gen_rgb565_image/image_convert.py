import struct
from PIL import Image


# Open the image
image = Image.open("image.png")

# Get image size
width, height = image.size
# Create a list to store the pixels
pixel_list = []
# Loop through each row of pixels
for y in range(height):
    # Loop through each column of pixels
    for x in range(width):
        # Get the RGB values of the current pixel
        r, g, b = image.getpixel((x, y))
        # Convert the RGB values to RGB565
        rgb565 = (((r & 0xf8) << 8) + ((g & 0xfc) << 3) + (b >> 3))
        # Add the RGB565 value to the pixel list
        pixel_list.append(rgb565)
# Convert the list of pixels to a string of bytes
pixel_string = b''
for pixel in pixel_list:
    # Pack the number into a two-byte string
    pixel_string += struct.pack('>H', pixel)

print(f'pixelData~{width}~{height}~{pixel_string}')
