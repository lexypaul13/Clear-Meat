#!/usr/bin/env python
"""
Supabase Image Statistics
------------------------
This script analyzes the meat products in Supabase and provides statistics about image availability.

Usage: python scripts/supabase_image_stats.py --url SUPABASE_URL --key SUPABASE_KEY

Command-line arguments:
  --url SUPABASE_URL: URL of your Supabase instance
  --key SUPABASE_KEY: API key for your Supabase instance
  --demo: Use fake data for demonstration purposes
"""

import os
import logging
import json
import asyncio
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from supabase import create_client, Client
from tabulate import tabulate

# Add the parent directory to the Python path to import from app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class SupabaseImageStats:
    """Analyzes meat products in Supabase and provides image statistics"""
    
    def __init__(self, supabase_url=None, supabase_key=None, demo=False):
        """Initialize the Supabase client with URL and key"""
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self.supabase = None
        self.demo = demo
        
        # If demo mode, we don't need Supabase credentials
        if not self.demo:
            # Ensure we have the required credentials
            if not self.supabase_url or not self.supabase_key:
                logger.error("SUPABASE_URL and SUPABASE_KEY must be provided (via args or env vars)")
                sys.exit(1)
    
    def setup(self):
        """Set up Supabase client"""
        # If demo mode, skip Supabase connection
        if self.demo:
            logger.info("Running in demo mode with fake data")
            return True
            
        try:
            logger.info(f"Connecting to Supabase at {self.supabase_url[:30]}...")
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            
            # Test the connection
            response = self.supabase.table('products').select('id').limit(1).execute()
            if hasattr(response, 'data'):
                logger.info("Successfully connected to Supabase")
                return True
            else:
                logger.error("Failed to connect to Supabase - no data returned")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {str(e)}")
            return False
    
    def get_total_products(self):
        """Get total count of products in the database"""
        if self.demo:
            return 1161  # Fake number from README
            
        try:
            response = self.supabase.table('products').select('id', count='exact').execute()
            total = 0
            if hasattr(response, 'count'):
                total = response.count
            else:
                total = len(response.data)
            return total
        except Exception as e:
            logger.error(f"Error getting total products: {str(e)}")
            return 0
    
    def get_products_with_images_stats(self):
        """Get statistics on products with and without images"""
        if self.demo:
            # Fake stats
            total = 1161
            with_images = 439
            without_images = total - with_images
            with_images_percent = round(with_images / total * 100, 2)
            without_images_percent = round(without_images / total * 100, 2)
            
            return {
                'total': total,
                'with_images': with_images,
                'without_images': without_images,
                'with_images_percent': with_images_percent,
                'without_images_percent': without_images_percent
            }
            
        try:
            # Get total count
            total = self.get_total_products()
            
            # Get count of products with images
            with_images_response = self.supabase.table('products') \
                .select('id', count='exact') \
                .not_.is_('image_url', 'null') \
                .neq('image_url', '') \
                .execute()
            
            # Handle count attribute if available
            with_images = 0
            if hasattr(with_images_response, 'count'):
                with_images = with_images_response.count
            else:
                with_images = len(with_images_response.data)
            
            # Calculate products without images
            without_images = total - with_images
            
            # Calculate percentages
            with_images_percent = round(with_images / total * 100, 2) if total > 0 else 0
            without_images_percent = round(without_images / total * 100, 2) if total > 0 else 0
            
            return {
                'total': total,
                'with_images': with_images,
                'without_images': without_images,
                'with_images_percent': with_images_percent,
                'without_images_percent': without_images_percent
            }
        except Exception as e:
            logger.error(f"Error getting image statistics: {str(e)}")
            return {'total': 0, 'with_images': 0, 'without_images': 0, 'with_images_percent': 0, 'without_images_percent': 0}
    
    def get_category_distribution(self):
        """Get distribution of products by category (meat_type)"""
        if self.demo:
            # Fake category distribution
            return {
                'beef': 275,
                'pork': 251,
                'chicken': 217,
                'turkey': 98,
                'lamb': 76,
                'mixed': 124,
                'other': 120
            }
            
        try:
            categories = {}
            response = self.supabase.table('products') \
                .select('meat_type, count') \
                .not_.is_('meat_type', 'null') \
                .execute()
            
            # Process the response to get category distribution
            if hasattr(response, 'data'):
                # Group by meat_type
                for item in response.data:
                    meat_type = item.get('meat_type', 'unknown')
                    if meat_type:
                        categories[meat_type] = categories.get(meat_type, 0) + 1
            
            return categories
        except Exception as e:
            logger.error(f"Error getting category distribution: {str(e)}")
            return {}
    
    def get_image_availability_by_category(self):
        """Get image availability statistics by category"""
        if self.demo:
            # Fake image availability by category
            categories = {}
            meat_types = {
                'beef': 275,
                'pork': 251, 
                'chicken': 217,
                'turkey': 98,
                'lamb': 76,
                'mixed': 124,
                'other': 120
            }
            
            image_rates = {
                'beef': 48,
                'pork': 35,
                'chicken': 42,
                'turkey': 25,
                'lamb': 22,
                'mixed': 38,
                'other': 30
            }
            
            for meat_type, total in meat_types.items():
                with_images_percent = image_rates[meat_type]
                with_images = int(total * with_images_percent / 100)
                without_images = total - with_images
                
                categories[meat_type] = {
                    'total': total,
                    'with_images': with_images,
                    'without_images': without_images,
                    'with_images_percent': with_images_percent
                }
                
            return categories
            
        try:
            # For each meat type, get the count of products with and without images
            categories = {}
            
            # First get all meat types
            meat_types_response = self.supabase.table('products') \
                .select('meat_type') \
                .not_.is_('meat_type', 'null') \
                .execute()
            
            if not hasattr(meat_types_response, 'data'):
                return {}
                
            # Get unique meat types
            meat_types = set()
            for item in meat_types_response.data:
                meat_type = item.get('meat_type')
                if meat_type:
                    meat_types.add(meat_type)
            
            # For each meat type, get image availability stats
            for meat_type in meat_types:
                # Get total count for this meat type
                total_response = self.supabase.table('products') \
                    .select('id', count='exact') \
                    .eq('meat_type', meat_type) \
                    .execute()
                
                total = 0
                if hasattr(total_response, 'count'):
                    total = total_response.count
                else:
                    total = len(total_response.data)
                
                # Get count with images for this meat type
                with_images_response = self.supabase.table('products') \
                    .select('id', count='exact') \
                    .eq('meat_type', meat_type) \
                    .not_.is_('image_url', 'null') \
                    .neq('image_url', '') \
                    .execute()
                
                with_images = 0
                if hasattr(with_images_response, 'count'):
                    with_images = with_images_response.count
                else:
                    with_images = len(with_images_response.data)
                
                # Calculate without images
                without_images = total - with_images
                
                # Calculate percentages
                with_images_percent = round(with_images / total * 100, 2) if total > 0 else 0
                
                # Store results
                categories[meat_type] = {
                    'total': total,
                    'with_images': with_images,
                    'without_images': without_images,
                    'with_images_percent': with_images_percent
                }
            
            return categories
        except Exception as e:
            logger.error(f"Error getting image availability by category: {str(e)}")
            return {}
    
    def get_recent_products(self, limit=5):
        """Get most recently added products"""
        if self.demo:
            # Fake recent products
            return [
                {'id': 1161, 'name': 'Maple Bacon', 'code': '5201567899871', 'has_image': True, 'created_at': '2025-04-20'},
                {'id': 1160, 'name': 'Beef Ribeye Steak', 'code': '5200198765432', 'has_image': False, 'created_at': '2025-04-19'},
                {'id': 1159, 'name': 'Chicken Breast Fillets', 'code': '5201600987652', 'has_image': True, 'created_at': '2025-04-18'},
                {'id': 1158, 'name': 'Turkey Mince', 'code': '5201611198765', 'has_image': False, 'created_at': '2025-04-17'},
                {'id': 1157, 'name': 'Lamb Shoulder', 'code': '5201855432198', 'has_image': True, 'created_at': '2025-04-16'},
            ]
            
        try:
            response = self.supabase.table('products') \
                .select('id, code, name, image_url, created_at') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            result = []
            if hasattr(response, 'data'):
                for product in response.data:
                    result.append({
                        'id': product.get('id'),
                        'name': product.get('name'),
                        'code': product.get('code'),
                        'has_image': bool(product.get('image_url')),
                        'created_at': product.get('created_at')
                    })
            
            return result
        except Exception as e:
            logger.error(f"Error getting recent products: {str(e)}")
            return []
    
    def generate_image_stats_chart(self, stats):
        """Generate a chart for image statistics"""
        labels = ['With Images', 'Without Images']
        sizes = [stats['with_images'], stats['without_images']]
        colors = ['#66b3ff', '#ff9999']
        explode = (0.1, 0)  # explode the 1st slice (With Images)
        
        plt.figure(figsize=(10, 7))
        plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title('Product Images Availability')
        plt.savefig('meat_products_images_stats.png')
        logger.info("Image stats chart saved as 'meat_products_images_stats.png'")
    
    def generate_category_chart(self, categories):
        """Generate a chart for category distribution"""
        if not categories:
            return
            
        labels = list(categories.keys())
        values = list(categories.values())
        
        plt.figure(figsize=(12, 8))
        plt.bar(range(len(labels)), values, align='center')
        plt.xticks(range(len(labels)), labels, rotation=45, ha='right')
        plt.xlabel('Categories')
        plt.ylabel('Number of Products')
        plt.title('Distribution of Meat Products by Category')
        plt.tight_layout()
        plt.savefig('meat_products_categories.png')
        logger.info("Category distribution chart saved as 'meat_products_categories.png'")
    
    def generate_image_availability_by_category_chart(self, categories):
        """Generate a chart for image availability by category"""
        if not categories:
            return
            
        # Prepare data for chart
        labels = list(categories.keys())
        with_images = [categories[label]['with_images'] for label in labels]
        without_images = [categories[label]['without_images'] for label in labels]
        
        # Set up the bar chart
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Set the width of the bars
        width = 0.35
        
        # Set up the positions of the bars
        x = range(len(labels))
        
        # Create the bars
        ax.bar([i - width/2 for i in x], with_images, width, label='With Images', color='#66b3ff')
        ax.bar([i + width/2 for i in x], without_images, width, label='Without Images', color='#ff9999')
        
        # Add labels, title, and legend
        ax.set_xlabel('Meat Type')
        ax.set_ylabel('Number of Products')
        ax.set_title('Image Availability by Meat Type')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig('meat_products_image_availability_by_category.png')
        logger.info("Image availability by category chart saved as 'meat_products_image_availability_by_category.png'")
    
    def display_database_statistics(self):
        """Display comprehensive statistics about the meat database"""
        logger.info("Retrieving database statistics...")
        
        # Get all statistics
        total_products = self.get_total_products()
        image_stats = self.get_products_with_images_stats()
        categories = self.get_category_distribution()
        image_by_category = self.get_image_availability_by_category()
        recent_products = self.get_recent_products()
        
        # Display statistics
        print("\n========== MEAT PRODUCTS DATABASE STATISTICS ==========\n")
        
        print(f"Total Products: {total_products}")
        
        print("\n------ IMAGE AVAILABILITY ------")
        table_data = [
            ["Status", "Count", "Percentage"],
            ["With Images", image_stats['with_images'], f"{image_stats['with_images_percent']}%"],
            ["Without Images", image_stats['without_images'], f"{image_stats['without_images_percent']}%"]
        ]
        print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
        
        print("\n------ CATEGORY DISTRIBUTION ------")
        category_data = [["Category", "Count"]]
        for category, count in categories.items():
            category_data.append([category, count])
        print(tabulate(category_data, headers="firstrow", tablefmt="grid"))
        
        print("\n------ IMAGE AVAILABILITY BY CATEGORY ------")
        cat_image_data = [["Category", "Total", "With Images", "Without Images", "With Images %"]]
        for category, stats in image_by_category.items():
            cat_image_data.append([
                category,
                stats['total'],
                stats['with_images'],
                stats['without_images'],
                f"{stats['with_images_percent']}%"
            ])
        print(tabulate(cat_image_data, headers="firstrow", tablefmt="grid"))
        
        print("\n------ RECENT PRODUCTS ------")
        recent_data = [["ID", "Name", "Code", "Has Image", "Created At"]]
        for product in recent_products:
            recent_data.append([
                product['id'],
                product['name'],
                product['code'],
                "✅" if product['has_image'] else "❌",
                product['created_at']
            ])
        print(tabulate(recent_data, headers="firstrow", tablefmt="grid"))
        
        print("\n========== GENERATING CHARTS ==========\n")
        
        # Generate charts
        self.generate_image_stats_chart(image_stats)
        self.generate_category_chart(categories)
        self.generate_image_availability_by_category_chart(image_by_category)
        
        print("\nStatistics analysis complete!")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Analyze meat products database image statistics')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    parser.add_argument('--demo', action='store_true', help='Use fake data for demonstration')
    return parser.parse_args()

def main():
    """Main function"""
    # Parse arguments
    args = parse_args()
    
    # Create analyzer
    analyzer = SupabaseImageStats(
        supabase_url=args.url,
        supabase_key=args.key,
        demo=args.demo
    )
    
    # Set up analyzer
    if not analyzer.setup():
        logger.error("Failed to set up database analyzer, exiting")
        return
    
    # Run analysis
    analyzer.display_database_statistics()

if __name__ == "__main__":
    main() 