from PIL import Image
import numpy as np

img = Image.open('public/inverso.png').convert("RGBA")
data = np.array(img)
# Find the non-transparent pixels
alpha = data[:, :, 3]
y_indices, x_indices = np.where(alpha > 0)
# We want to remove the bottom line. Let's look at the vertical projection.
# The logo has some text, then a gap, then a line.
# Let's crop the bottom 15% or find the gap.
if len(y_indices) > 0:
    max_y = np.max(y_indices)
    # The line is at the bottom.
    # We can crop the bottom 10 pixels if they are disjoint.
    # Let's just crop out the bottom 15%.
    crop_h = int(img.height * 0.85)
    img = img.crop((0, 0, img.width, crop_h))
    img.save('public/inverso.png')
    print("Cropped!")
