import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.images.core.fix_images import supabase

# Get 30 random products with images
response = supabase.table('products').select('name,image_data,image_url,source').not_.is_('image_data', 'null').limit(30).execute()
products = response.data

def get_image_src(product):
    image_data = product.get('image_data', '')
    image_url = product.get('image_url', '')
    if image_data and not image_data.startswith('http'):
        # Add base64 prefix if not present
        return f"data:image/jpeg;base64,{image_data}"
    elif image_data and image_data.startswith('http'):
        return image_data
    elif image_url:
        return image_url
    else:
        return ''

# Generate HTML
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Recently Scraped Images Sample</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding: 20px;
            background-color: #fff;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .product-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .product-card img {
            width: 100%;
            height: 200px;
            object-fit: contain;
            border-radius: 4px;
            background: #e0e7ef;
        }
        .product-card h3 {
            margin: 10px 0;
            font-size: 16px;
            color: #333;
        }
        .product-info {
            font-size: 14px;
            color: #666;
            margin: 5px 0;
        }
        .product-card a {
            color: #0066cc;
            text-decoration: none;
            font-size: 14px;
            display: block;
            margin-top: 5px;
        }
        .product-card a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Recently Scraped Images Sample</h1>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Showing 30 random products with images</p>
        </div>
        <div class="grid">
"""

for product in products:
    image_src = get_image_src(product)
    html_content += f"""
            <div class="product-card">
                <img src=\"{image_src}\" alt=\"{product['name']}\">
                <h3>{product['name']}</h3>
                <div class="product-info">Source: {product['source']}</div>
                <a href=\"{product['image_url']}\" target=\"_blank\">View Original Image</a>
            </div>
    """

html_content += """
        </div>
    </div>
</body>
</html>
"""

# Save the HTML file
output_dir = "reports"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_file = os.path.join(output_dir, f"image_samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
with open(output_file, "w") as f:
    f.write(html_content)

print(f"Report generated: {output_file}") 