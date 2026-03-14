# src/utils/color_utils.py

# ------------------------------
#  STANDALONE UTILITY FUNCTION        -->  # (FIX 1: Resolves AttributeError) #
# ------------------------------

def hex_to_rgb(hex_code):
    """Converts a standard #RRGGBB hex string to an (R, G, B) integer tuple."""
    try:
        if hex_code.startswith("#"):
            hex_code = hex_code[1:]
        
        if len(hex_code) == 6:
            r = int(hex_code[0:2], 16)
            g = int(hex_code[2:4], 16)
            b = int(hex_code[4:6], 16)
            return (r, g, b)
        else:
            # Handle cases like "gray70" which are not standard hex
            # Since we switched ICON_COLOR to hex, this should not trigger
            return (255, 255, 255) 
    except ValueError:
        return (255, 255, 255)