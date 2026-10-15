from PIL import Image
from rembg import remove

def isolate_bird_on_gray(image_path, output_path, gray_value=128):
    # 1. Open the image captured by the raspicam
    input_image = Image.open(image_path)
    
    # 2. Extract the foreground bird with an alpha (transparency) channel
    # This automatically handles soft or blurry background edges
    foreground = remove(input_image)
    
    # 3. Create a solid, uniform gray background image of the exact same dimensions
    # gray_value can range from 0 (black) to 255 (white). 128 creates a neutral medium gray.
    width, height = input_image.size
    gray_background = Image.new("RGB", (width, height), (gray_value, gray_value, gray_value))
    
    # 4. Paste the isolated bird onto the gray background using its own alpha mask for smooth blending
    gray_background.paste(foreground, (0, 0), foreground)
    
    # 5. Save the final processed image
    gray_background.save(output_path)
    print(f"Bird successfully isolated and saved to {output_path}")

# Example usage:
isolate_bird_on_gray("bird_raspicam.jpg", "bird_on_gray.jpg", gray_value=128)