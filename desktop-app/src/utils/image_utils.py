# src/utils/image_utils.py

from PIL import Image
from src.utils.color_utils import hex_to_rgb 

# =============================
#     HANDLING IMAGES ICONS
# =============================

def tint_image(img: Image.Image, target_color_hex: str) -> Image.Image:
    """pulls these hex codes to re-color your .png assets so they stay visible and 
    high-contrast when you switch between light and dark modes.
    """
    target_color_rgb = hex_to_rgb(target_color_hex) 

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    data = img.getdata()
    new_data = []

    for r, g, b, a in data:
        if r < 50 and g < 50 and b < 50:
            new_data.append((*target_color_rgb, a))
        else:
            new_data.append((r, g, b, a))
            
    new_img = Image.new("RGBA", img.size)
    new_img.putdata(new_data)
    return new_img
       
        
            
            
            
            
            
