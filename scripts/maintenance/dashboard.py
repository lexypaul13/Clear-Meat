#!/usr/bin/env python
"""
Product Image Dashboard
-------------------
This script creates a dashboard to monitor and visualize image update progress.

Usage: python scripts/dashboard.py --url SUPABASE_URL --key SUPABASE_KEY
"""

import os
import sys
import argparse
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageDashboard:
    def __init__(self, supabase_url, supabase_key):
        """Initialize the dashboard with Supabase credentials."""
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.supabase = None
        self.update_interval = 60  # seconds
        self.should_update = True
        
        # Initialize UI
        self.root = tk.Tk()
        self.root.title("Meat Products Image Dashboard")
        self.root.geometry("1000x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Setup UI components
        self.setup_ui()
        
        # Connect to Supabase
        self.connect_to_supabase()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self.update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def connect_to_supabase(self):
        """Connect to Supabase database."""
        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self.status_label.config(text="Connected to Supabase", fg="green")
            logger.info("Connected to Supabase")
        except Exception as e:
            self.status_label.config(text=f"Failed to connect: {str(e)}", fg="red")
            logger.error(f"Failed to connect to Supabase: {str(e)}")
    
    def setup_ui(self):
        """Setup the UI components."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, text="Initializing...", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Last updated label
        self.last_updated_label = ttk.Label(status_frame, text="", anchor=tk.E)
        self.last_updated_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Top stats frame
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.pack(fill=tk.X, pady=10)
        
        # Stats grid
        self.total_products_label = self.create_stat_label(stats_frame, "Total Products:", 0, 0)
        self.products_with_images_label = self.create_stat_label(stats_frame, "Products with Images:", 0, 1)
        self.products_without_images_label = self.create_stat_label(stats_frame, "Products without Images:", 1, 0)
        self.products_updated_today_label = self.create_stat_label(stats_frame, "Updated Today:", 1, 1)
        
        # Progress bar
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        ttk.Label(progress_frame, text="Image Coverage:").pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.progress_percent = ttk.Label(progress_frame, text="0%")
        self.progress_percent.pack(side=tk.LEFT, padx=5)
        
        # Tabs
        tab_control = ttk.Notebook(main_frame)
        
        # Charts tab
        charts_tab = ttk.Frame(tab_control)
        tab_control.add(charts_tab, text="Charts")
        
        # Create figure for charts
        self.fig = plt.Figure(figsize=(10, 6), dpi=100)
        
        # Add subplots
        self.ax1 = self.fig.add_subplot(221)  # Coverage pie chart
        self.ax2 = self.fig.add_subplot(222)  # Updates over time
        self.ax3 = self.fig.add_subplot(223)  # Meat type distribution
        self.ax4 = self.fig.add_subplot(224)  # Recent updates
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, charts_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Recent updates tab
        updates_tab = ttk.Frame(tab_control)
        tab_control.add(updates_tab, text="Recent Updates")
        
        # Recent updates table
        table_frame = ttk.Frame(updates_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview for updates
        columns = ("code", "name", "meat_type", "last_updated")
        self.updates_table = ttk.Treeview(table_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        
        # Set column headings
        self.updates_table.heading("code", text="Code")
        self.updates_table.heading("name", text="Name")
        self.updates_table.heading("meat_type", text="Type")
        self.updates_table.heading("last_updated", text="Last Updated")
        
        # Set column widths
        self.updates_table.column("code", width=100)
        self.updates_table.column("name", width=300)
        self.updates_table.column("meat_type", width=150)
        self.updates_table.column("last_updated", width=150)
        
        self.updates_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.updates_table.yview)
        
        # Without images tab
        missing_tab = ttk.Frame(tab_control)
        tab_control.add(missing_tab, text="Missing Images")
        
        # Missing images table
        missing_frame = ttk.Frame(missing_tab)
        missing_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        missing_scrollbar = ttk.Scrollbar(missing_frame)
        missing_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview for missing images
        self.missing_table = ttk.Treeview(missing_frame, columns=columns, show="headings", yscrollcommand=missing_scrollbar.set)
        
        # Set column headings
        for col in columns:
            self.missing_table.heading(col, text=col.capitalize())
        
        # Set column widths
        self.missing_table.column("code", width=100)
        self.missing_table.column("name", width=300)
        self.missing_table.column("meat_type", width=150)
        self.missing_table.column("last_updated", width=150)
        
        self.missing_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        missing_scrollbar.config(command=self.missing_table.yview)
        
        # Add the tabs to the main frame
        tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Refresh Now", command=self.refresh_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Run Image Update", command=self.run_image_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Report", command=self.export_report).pack(side=tk.LEFT, padx=5)
    
    def create_stat_label(self, parent, text, row, col):
        """Create a statistic label with a default value."""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")
        
        label = ttk.Label(frame, text=text)
        label.pack(side=tk.LEFT)
        
        value = ttk.Label(frame, text="0")
        value.pack(side=tk.LEFT, padx=5)
        
        return value
    
    def update_loop(self):
        """Background thread for periodic updates."""
        while self.should_update:
            try:
                self.refresh_data()
            except Exception as e:
                logger.error(f"Error in update loop: {str(e)}")
            
            # Sleep for update interval
            time.sleep(self.update_interval)
    
    def refresh_data(self):
        """Refresh all data from Supabase."""
        if not self.supabase:
            self.status_label.config(text="Not connected to Supabase", fg="red")
            return
        
        try:
            self.status_label.config(text="Refreshing data...", fg="blue")
            self.root.update_idletasks()
            
            # Get statistics
            stats = self.get_statistics()
            
            # Update UI with statistics
            self.update_statistics_ui(stats)
            
            # Get recent updates for table
            recent_updates = self.get_recent_updates()
            self.update_recent_updates_table(recent_updates)
            
            # Get missing images for table
            missing_images = self.get_missing_images()
            self.update_missing_images_table(missing_images)
            
            # Update charts
            self.update_charts(stats, recent_updates)
            
            # Update last refreshed time
            self.last_updated_label.config(text=f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
            
            self.status_label.config(text="Data refreshed successfully", fg="green")
        except Exception as e:
            self.status_label.config(text=f"Error refreshing data: {str(e)}", fg="red")
            logger.error(f"Error refreshing data: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from Supabase."""
        # Get total products count
        total_response = self.supabase.table('products').select('id', count='exact').execute()
        total_count = total_response.count
        
        # Get products with images count
        with_images_response = self.supabase.table('products').select('id', count='exact') \
                             .not_('image_url', 'is', 'null') \
                             .not_('image_url', 'eq', '') \
                             .execute()
        with_images_count = with_images_response.count
        
        # Get products updated today
        today = datetime.now().date().isoformat()
        updated_today_response = self.supabase.table('products').select('id', count='exact') \
                               .gte('last_updated', today) \
                               .execute()
        updated_today_count = updated_today_response.count
        
        # Get meat type distribution
        meat_type_response = self.supabase.table('products').select('meat_type') \
                           .not_('meat_type', 'is', 'null') \
                           .execute()
        
        meat_types = {}
        for item in meat_type_response.data:
            meat_type = item.get('meat_type', 'Unknown')
            if meat_type in meat_types:
                meat_types[meat_type] += 1
            else:
                meat_types[meat_type] = 1
        
        # Get updates over time (last 7 days)
        updates_by_day = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            next_date = (datetime.now() - timedelta(days=i-1)).date().isoformat()
            
            # Query for updates on this day
            day_updates_response = self.supabase.table('products').select('id', count='exact') \
                                 .gte('last_updated', date) \
                                 .lt('last_updated', next_date) \
                                 .execute()
            
            day_label = (datetime.now() - timedelta(days=i)).strftime('%a')
            updates_by_day[day_label] = day_updates_response.count
        
        # Return statistics
        return {
            'total_count': total_count,
            'with_images_count': with_images_count,
            'without_images_count': total_count - with_images_count,
            'updated_today_count': updated_today_count,
            'coverage_percent': (with_images_count / total_count * 100) if total_count > 0 else 0,
            'meat_types': meat_types,
            'updates_by_day': updates_by_day
        }
    
    def get_recent_updates(self) -> List[Dict[str, Any]]:
        """Get recently updated products."""
        # Get products updated in the last 3 days
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        
        response = self.supabase.table('products') \
                 .select('code, name, meat_type, last_updated, image_url') \
                 .gte('last_updated', three_days_ago) \
                 .not_('image_url', 'is', 'null') \
                 .not_('image_url', 'eq', '') \
                 .order('last_updated', desc=True) \
                 .limit(100) \
                 .execute()
        
        return response.data
    
    def get_missing_images(self) -> List[Dict[str, Any]]:
        """Get products with missing images."""
        response = self.supabase.table('products') \
                 .select('code, name, meat_type, last_updated') \
                 .or_('image_url.is.null,image_url.eq.') \
                 .limit(100) \
                 .execute()
        
        return response.data
    
    def update_statistics_ui(self, stats: Dict[str, Any]):
        """Update UI with statistics."""
        self.total_products_label.config(text=str(stats['total_count']))
        self.products_with_images_label.config(text=str(stats['with_images_count']))
        self.products_without_images_label.config(text=str(stats['without_images_count']))
        self.products_updated_today_label.config(text=str(stats['updated_today_count']))
        
        # Update progress bar
        self.progress_bar['value'] = stats['coverage_percent']
        self.progress_percent.config(text=f"{stats['coverage_percent']:.1f}%")
    
    def update_recent_updates_table(self, updates: List[Dict[str, Any]]):
        """Update recent updates table."""
        # Clear existing items
        for item in self.updates_table.get_children():
            self.updates_table.delete(item)
        
        # Add new items
        for product in updates:
            self.updates_table.insert('', tk.END, values=(
                product.get('code', ''),
                product.get('name', ''),
                product.get('meat_type', ''),
                product.get('last_updated', '')
            ))
    
    def update_missing_images_table(self, products: List[Dict[str, Any]]):
        """Update missing images table."""
        # Clear existing items
        for item in self.missing_table.get_children():
            self.missing_table.delete(item)
        
        # Add new items
        for product in products:
            self.missing_table.insert('', tk.END, values=(
                product.get('code', ''),
                product.get('name', ''),
                product.get('meat_type', ''),
                product.get('last_updated', '')
            ))
    
    def update_charts(self, stats: Dict[str, Any], recent_updates: List[Dict[str, Any]]):
        """Update all charts."""
        # Clear all axes
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()
        
        # 1. Coverage Pie Chart
        labels = ['With Images', 'Without Images']
        sizes = [stats['with_images_count'], stats['without_images_count']]
        colors = ['#4CAF50', '#F44336']
        
        self.ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        self.ax1.set_title('Image Coverage')
        
        # 2. Updates over time
        days = list(stats['updates_by_day'].keys())
        counts = list(stats['updates_by_day'].values())
        
        self.ax2.bar(days, counts, color='#2196F3')
        self.ax2.set_title('Updates by Day')
        self.ax2.set_xlabel('Day')
        self.ax2.set_ylabel('Number of Updates')
        
        # 3. Meat Type Distribution
        meat_types = list(stats['meat_types'].keys())
        meat_counts = list(stats['meat_types'].values())
        
        # Only show top 5 meat types if there are many
        if len(meat_types) > 5:
            # Sort by count
            meat_data = sorted(zip(meat_types, meat_counts), key=lambda x: x[1], reverse=True)
            top_meat_types = [item[0] for item in meat_data[:5]]
            top_meat_counts = [item[1] for item in meat_data[:5]]
            
            # Add "Other" category
            other_count = sum(meat_counts) - sum(top_meat_counts)
            top_meat_types.append('Other')
            top_meat_counts.append(other_count)
            
            meat_types = top_meat_types
            meat_counts = top_meat_counts
        
        self.ax3.bar(meat_types, meat_counts, color='#FF9800')
        self.ax3.set_title('Meat Type Distribution')
        self.ax3.set_xticklabels(meat_types, rotation=45, ha='right')
        
        # 4. Recent Updates (last 24 hours)
        one_day_ago = (datetime.now() - timedelta(days=1)).isoformat()
        recent_counts = {}
        
        for product in recent_updates:
            updated = product.get('last_updated', '')
            if updated >= one_day_ago:
                hour = datetime.fromisoformat(updated.replace('Z', '+00:00')).strftime('%H:00')
                if hour in recent_counts:
                    recent_counts[hour] += 1
                else:
                    recent_counts[hour] = 1
        
        hours = list(recent_counts.keys())
        hour_counts = list(recent_counts.values())
        
        self.ax4.bar(hours, hour_counts, color='#9C27B0')
        self.ax4.set_title('Updates in Last 24 Hours')
        self.ax4.set_xlabel('Hour')
        self.ax4.set_ylabel('Number of Updates')
        self.ax4.set_xticklabels(hours, rotation=45, ha='right')
        
        # Adjust layout and draw
        self.fig.tight_layout()
        self.canvas.draw()
    
    def run_image_update(self):
        """Run the image update script."""
        # This would launch fix_broken_images_bulk.py in a separate process
        self.status_label.config(text="Starting image update process...", fg="blue")
        
        # Create a new thread to run the process
        def run_process():
            try:
                # Import the script and run it
                from fix_broken_images_bulk import main as fix_images
                fix_images()
                
                # Refresh data after completion
                self.status_label.config(text="Image update completed, refreshing data...", fg="blue")
                self.refresh_data()
            except Exception as e:
                self.status_label.config(text=f"Error during image update: {str(e)}", fg="red")
                logger.error(f"Error during image update: {str(e)}")
        
        threading.Thread(target=run_process).start()
    
    def export_report(self):
        """Export current statistics to a CSV file."""
        try:
            # Get current statistics
            stats = self.get_statistics()
            recent_updates = self.get_recent_updates()
            missing_images = self.get_missing_images()
            
            # Create a timestamp for the filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_report_{timestamp}.xlsx"
            
            # Create Excel writer
            with pd.ExcelWriter(filename) as writer:
                # Write summary statistics
                summary_data = {
                    'Metric': ['Total Products', 'Products with Images', 'Products without Images', 
                              'Image Coverage', 'Products Updated Today'],
                    'Value': [
                        stats['total_count'],
                        stats['with_images_count'],
                        stats['without_images_count'],
                        f"{stats['coverage_percent']:.1f}%",
                        stats['updated_today_count']
                    ]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
                
                # Write recent updates
                pd.DataFrame(recent_updates).to_excel(writer, sheet_name='Recent Updates', index=False)
                
                # Write missing images
                pd.DataFrame(missing_images).to_excel(writer, sheet_name='Missing Images', index=False)
                
                # Write meat type distribution
                meat_type_data = []
                for meat_type, count in stats['meat_types'].items():
                    meat_type_data.append({'Meat Type': meat_type, 'Count': count})
                pd.DataFrame(meat_type_data).to_excel(writer, sheet_name='Meat Types', index=False)
            
            self.status_label.config(text=f"Report exported to {filename}", fg="green")
        except Exception as e:
            self.status_label.config(text=f"Error exporting report: {str(e)}", fg="red")
            logger.error(f"Error exporting report: {str(e)}")
    
    def on_close(self):
        """Handle window close event."""
        self.should_update = False
        self.root.destroy()
    
    def run(self):
        """Run the dashboard."""
        # Initial data refresh
        self.refresh_data()
        
        # Start the main event loop
        self.root.mainloop()


def main():
    """Main function to run the dashboard."""
    parser = argparse.ArgumentParser(description='Product image dashboard')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    args = parser.parse_args()
    
    supabase_url = args.url or os.getenv("SUPABASE_URL")
    supabase_key = args.key or os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be provided")
        sys.exit(1)
    
    dashboard = ImageDashboard(supabase_url, supabase_key)
    dashboard.run()


if __name__ == "__main__":
    main() 