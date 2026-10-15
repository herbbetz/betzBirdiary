# remove background from all img/*.jpg and replace it with a solid gray background
# pip install "rembg[cpu]" pillow
# https://github.com/danielgatis/rembg
import glob
from pathlib import Path
from PIL import Image
from rembg import remove

def process_bird_images(input_dir="img", gray_value=128):
    # Search for all .jpg files in the specified subdirectory
    search_pattern = f"{input_dir}/*.jpg"
    image_paths = glob.glob(search_pattern)
    
    if not image_paths:
        print(f"No .jpg files found in the '{input_dir}/' directory.")
        return

    print(f"Found {len(image_paths)} image(s) to process.\n")

    for img_path in image_paths:
        path_obj = Path(img_path)
        basename = path_obj.stem
        # Define output filename: <basename>-nb.jpg in the same directory (or customize path if needed)
        output_path = path_obj.with_name(f"{basename}-nb.jpg")
        
        print(f"Processing: {path_obj.name} -> {output_path.name}")
        
        try:
            # 1. Open the image
            input_image = Image.open(img_path)
            
            # 2. Extract the foreground bird with an alpha mask
            foreground = remove(input_image)
            
            # 3. Create a solid uniform gray background matching the dimensions
            width, height = input_image.size
            gray_background = Image.new("RGB", (width, height), (gray_value, gray_value, gray_value))
            
            # 4. Paste the bird onto the gray background
            gray_background.paste(foreground, (0, 0), foreground)
            
            # 5. Save the result
            gray_background.save(output_path)
            print(f"Saved successfully!\n")
            
        except Exception as e:
            print(f"Error processing {path_obj.name}: {e}\n")

if __name__ == "__main__":
    process_bird_images()