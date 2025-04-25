# Image Management Scripts

Scripts for managing product images in the MeatWise database.

## Scripts

### verify_images.py
Comprehensive image verification tool that:
- Validates image data integrity
- Checks image URLs accessibility
- Reports invalid images
- Updates database for invalid images

Usage:
```bash
python verify_images.py
```

### fix_images.py
Fixes broken or missing product images:
- Downloads images from URLs with retry logic
- Processes and optimizes images
- Handles bulk operations efficiently
- Updates database with fixed images

Usage:
```bash
python fix_images.py --batch-size 50 --max-retries 3
```

## Common Operations

1. **Verify All Images**
   ```bash
   python verify_images.py
   ```

2. **Fix Broken Images**
   ```bash
   python fix_images.py
   ```

3. **Bulk Process with Custom Settings**
   ```bash
   python fix_images.py --batch-size 100 --max-retries 5
   ```

## Image Processing Standards

- Maximum image size: 800x800 pixels
- Format: JPEG
- Quality: 85%
- Color mode: RGB
- Storage: Base64 encoded in database 