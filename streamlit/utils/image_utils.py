import os
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import hashlib
import time

def get_image_from_url(url, timeout=5):
    """
    Fetch an image from a URL with timeout and error handling
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        return None

def create_default_meat_image(meat_type="Generic", size=(300, 300), bg_color="#F8F8F8", text_color="#333333"):
    """
    Create a default placeholder image for a meat product
    """
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fall back to default if not available
    try:
        font = ImageFont.truetype("Arial", 36)
        small_font = ImageFont.truetype("Arial", 24)
    except IOError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw a border
    border_width = 5
    draw.rectangle(
        [(border_width, border_width), (size[0]-border_width, size[1]-border_width)],
        outline="#CCCCCC",
        width=border_width
    )
    
    # Add meat icon (simple drawing)
    center_x, center_y = size[0]//2, size[1]//2 - 40
    draw.ellipse(
        [(center_x-40, center_y-40), (center_x+40, center_y+40)],
        fill="#FF6B6B"
    )
    
    # Add text
    draw.text(
        (size[0]//2, size[1]//2 + 40),
        f"{meat_type} Meat",
        font=font,
        fill=text_color,
        anchor="mm"
    )
    
    draw.text(
        (size[0]//2, size[1]//2 + 80),
        "Image Unavailable",
        font=small_font,
        fill=text_color,
        anchor="mm"
    )
    
    return img

def generate_default_meat_image(save_path="streamlit/assets/default_meat.jpg"):
    """
    Generate and save the default meat image
    """
    # Check if directory exists
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Create default image
    img = create_default_meat_image()
    
    # Save to file
    img.save(save_path, "JPEG", quality=90)
    
    return save_path

def get_or_create_meat_image(meat_type, save_dir="streamlit/assets/meat_types"):
    """
    Get or create a meat type specific image
    """
    # Create hash of meat type for filename
    filename = f"{meat_type.lower().replace(' ', '_')}.jpg"
    file_path = os.path.join(save_dir, filename)
    
    # Check if directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Check if file exists
    if os.path.exists(file_path):
        return file_path
    
    # Create image for specific meat type
    img = create_default_meat_image(meat_type=meat_type)
    
    # Save to file
    img.save(file_path, "JPEG", quality=90)
    
    return file_path

if __name__ == "__main__":
    # Generate default meat image when run directly
    generate_default_meat_image()
    
    # Generate meat type specific images
    meat_types = ["Beef", "Pork", "Poultry", "Lamb", "Fish", "Venison", "Duck", "Turkey"]
    for meat_type in meat_types:
        get_or_create_meat_image(meat_type) 