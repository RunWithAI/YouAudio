import os
from PIL import Image, ImageDraw
import subprocess
import sys

def round_corners(img, radius):
    """Create a rounded rectangle mask for the image while keeping the inside content"""
    # Create a new RGBA image with transparency
    result = Image.new('RGBA', img.size, (0, 0, 0, 0))
    
    # Create a mask for rounded corners
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Draw a rounded rectangle on the mask
    # The rectangle covers the entire image except for the corners
    w, h = img.size
    draw.rounded_rectangle([0, 0, w-1, h-1], radius, fill=255)
    
    # Paste the original image using the rounded rectangle mask
    result.paste(img, (0, 0), mask)
    
    return result

def add_padding(img, target_size, padding_percentage=0.15):
    """Add transparent padding around the image"""
    # Calculate the size for the image with padding
    padded_size = int(target_size * (1 - 2 * padding_percentage))
    
    # Calculate radius for rounded corners (adjust this value to control corner roundness)
    radius = int(padded_size * 0.2)  # 20% of the padded size
    
    # Resize the original image to the padded size
    aspect_ratio = img.size[0] / img.size[1]
    if aspect_ratio > 1:
        new_width = padded_size
        new_height = int(padded_size / aspect_ratio)
    else:
        new_height = padded_size
        new_width = int(padded_size * aspect_ratio)
    
    # Resize the image
    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Apply rounded corners to the resized image
    rounded = round_corners(resized, radius)
    
    # Create a completely transparent background
    padded = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
    
    # Calculate position to paste the rounded image
    x = (target_size - new_width) // 2
    y = (target_size - new_height) // 2
    
    # Paste the rounded image with its alpha channel
    padded.paste(rounded, (x, y), rounded.split()[3])
    
    return padded

def generate_icns():
    try:
        # Source image path
        source_image = os.path.join('static', 'image', 'learning_cats.jpg')
        print(f"Looking for source image at: {os.path.abspath(source_image)}")
        
        if not os.path.exists(source_image):
            print(f"Error: Source image not found at {source_image}")
            return
        
        # Create iconset directory if it doesn't exist
        iconset_dir = 'YouAudio.iconset'
        if os.path.exists(iconset_dir):
            print(f"Removing existing iconset directory: {iconset_dir}")
            for file in os.listdir(iconset_dir):
                os.remove(os.path.join(iconset_dir, file))
            os.rmdir(iconset_dir)
        
        print(f"Creating iconset directory: {iconset_dir}")
        os.makedirs(iconset_dir)
        
        # Define the sizes needed for macOS icons
        icon_sizes = [
            (16, 'icon_16x16.png'),
            (32, 'icon_16x16@2x.png'),
            (32, 'icon_32x32.png'),
            (64, 'icon_32x32@2x.png'),
            (128, 'icon_128x128.png'),
            (256, 'icon_128x128@2x.png'),
            (256, 'icon_256x256.png'),
            (512, 'icon_256x256@2x.png'),
            (512, 'icon_512x512.png'),
            (1024, 'icon_512x512@2x.png')
        ]
        
        print("Opening source image...")
        # Open and convert the source image
        with Image.open(source_image) as img:
            print(f"Image mode: {img.mode}, Size: {img.size}")
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                print("Converting image to RGBA...")
                img = img.convert('RGBA')
            
            # Generate each icon size
            print("Generating icon sizes...")
            for size, filename in icon_sizes:
                output_path = os.path.join(iconset_dir, filename)
                print(f"Creating {filename} ({size}x{size})...")
                
                # Add padding around the image
                padded = add_padding(img, size)
                
                # Save the image
                padded.save(output_path)
                if not os.path.exists(output_path):
                    print(f"Failed to save {filename}")
                    return
        
        # Convert iconset to icns using iconutil
        print("Converting iconset to icns...")
        result = subprocess.run(['iconutil', '--convert', 'icns', '--output', 'YouAudio.icns', iconset_dir], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error running iconutil: {result.stderr}")
            return
        
        print("Cleaning up...")
        # Clean up the iconset directory
        for size, filename in icon_sizes:
            try:
                # os.remove(os.path.join(iconset_dir, filename))
                pass
            except Exception as e:
                print(f"Error removing {filename}: {e}")
        
        try:
            os.rmdir(iconset_dir)
        except Exception as e:
            print(f"Error removing iconset directory: {e}")
        
        if os.path.exists('YouAudio.icns'):
            print("Successfully created YouAudio.icns")
        else:
            print("Failed to create YouAudio.icns")
            
    except Exception as e:
        print(f"Error generating icons: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    generate_icns()
