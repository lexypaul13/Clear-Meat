# Image Management Scripts

Scripts for managing product images in the MeatWise database.

## Directory Structure

```
scripts/images/
├── core/           # Core image processing scripts
│   ├── fix_images.py      # Main image processing script
│   └── run_nightly.sh     # Nightly scheduler
├── utils/          # Utility scripts
│   ├── supabase_image_stats.py    # Database statistics
│   └── create_image_gallery.py    # Image visualization
└── maintenance/    # Maintenance scripts
    ├── verify_images.py           # Image verification
    └── check_images_in_openfoodfacts.py  # OpenFoodFacts specific
```

## Core Scripts

### fix_images.py
Main image processing script that:
- Scrapes images from multiple sources
- Processes and optimizes images
- Updates database with processed images

Usage:
```bash
python scripts/images/core/fix_images.py --batch-size 50 --max-retries 3 --time-limit 8
```

### run_nightly.sh
Scheduler script that runs the image processing nightly.

## Utility Scripts

### supabase_image_stats.py
Generates statistics about images in the database.

Usage:
```bash
python scripts/images/utils/supabase_image_stats.py
```

### create_image_gallery.py
Creates an image gallery for visualization.

Usage:
```bash
python scripts/images/utils/create_image_gallery.py
```

## Maintenance Scripts

### verify_images.py
Verifies image integrity and accessibility.

Usage:
```bash
python scripts/images/maintenance/verify_images.py
```

### check_images_in_openfoodfacts.py
Checks for images in OpenFoodFacts.

Usage:
```bash
python scripts/images/maintenance/check_images_in_openfoodfacts.py
```

## Image Processing Standards

- Maximum image size: 800x800 pixels
- Format: JPEG
- Quality: 85%
- Color mode: RGB
- Storage: Base64 encoded in database 