from PIL import Image, ImageOps, ImageDraw

def process_amce_logo():
    # Load raw image
    img = Image.open('/Users/nourine/.gemini/antigravity/brain/f876e677-101e-45c7-9779-2a217a11e112/media__1779129243188.jpg')
    
    # The photo is upside down, rotate it 180 degrees
    img = img.rotate(180)
    
    # We want to find the logo inside the white paper area
    # Convert to RGB to access pixel values
    img = img.convert('RGBA')
    width, height = img.size
    
    # Scan for the bounding box of the logo elements (the red/pink cube and dark blue text)
    # The paper background is white (high R, G, B), and elements are darker or colored.
    # Let's define the search area (usually in the bottom half of the rotated image)
    left, top, right, bottom = width, height, 0, 0
    
    for x in range(width):
        for y in range(int(height * 0.4), height): # Scan bottom 60%
            r, g, b, a = img.getpixel((x, y))
            # If the pixel is not white/gray paper background (e.g. dark blue or red logo)
            # Threshold: let's say sum of RGB is less than 500 (since white paper is > 650)
            # and it's not the gray desk background (gray desk is darker, but we look for the white paper first)
            # Let's do a more precise condition:
            # We are looking for the red cube (high R, lower G, B) or dark blue text (low R, low G, high-ish B)
            is_cube = (r > 120 and g < 100 and b < 120)
            is_text = (r < 80 and g < 100 and b > 90) or (r < 100 and g < 100 and b < 100) # dark elements
            
            if is_cube or is_text:
                if x < left: left = x
                if x > right: right = x
                if y < top: top = y
                if y > bottom: bottom = y
                
    # Add padding to the crop box
    padding = 15
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(width, right + padding)
    bottom = min(height, bottom + padding)
    
    print(f"AMCE Crop Box: left={left}, top={top}, right={right}, bottom={bottom}")
    
    # Crop the logo
    logo = img.crop((left, top, right, bottom))
    
    # Clean the background: convert any white-ish pixels to transparent
    logo_w, logo_h = logo.size
    datas = logo.getdata()
    new_data = []
    for item in datas:
        # If the pixel is white-ish (background of the card paper), make it transparent
        r, g, b, a = item
        # White paper typically has high brightness
        if r > 180 and g > 180 and b > 180:
            new_data.append((255, 255, 255, 0)) # Transparent
        else:
            # Enhance colors slightly
            if r > 120 and g < 100 and b < 120: # Red cube
                new_data.append((210, 40, 60, 255)) # Pure vibrant red
            elif r < 100 and g < 100 and b > 80: # Dark blue text
                new_data.append((12, 35, 80, 255)) # Deep navy
            elif r < 110 and g < 110 and b < 110: # Blackish text
                new_data.append((12, 35, 80, 255)) # Deep navy
            else:
                new_data.append(item)
                
    logo.putdata(new_data)
    
    # Save the polished AMCE logo
    logo.save('/Users/nourine/.gemini/antigravity/scratch/noro_unified/static/img/amce_logo.png')
    print("AMCE logo processed successfully.")

def process_fiat_logo():
    # Load raw image
    img = Image.open('/Users/nourine/.gemini/antigravity/brain/f876e677-101e-45c7-9779-2a217a11e112/media__1779129275126.jpg')
    
    # Make it a perfect circle transparent PNG
    img = img.convert('RGBA')
    width, height = img.size
    
    # Create circular mask
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    # Draw white circle in the middle
    draw.ellipse((5, 5, width-5, height-5), fill=255)
    
    # Apply mask
    output = Image.new('RGBA', (width, height), (0,0,0,0))
    output.paste(img, (0, 0), mask=mask)
    
    # Save the polished FIAT logo
    output.save('/Users/nourine/.gemini/antigravity/scratch/noro_unified/static/img/fiat_logo.png')
    print("FIAT logo processed successfully.")

if __name__ == '__main__':
    process_amce_logo()
    process_fiat_logo()
