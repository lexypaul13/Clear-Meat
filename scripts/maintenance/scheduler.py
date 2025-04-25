#!/usr/bin/env python
"""
Image Update Scheduler
-------------------
This script schedules and automates product image updates at regular intervals.
Only runs jobs between 12:00 AM and 6:00 PM to avoid peak hours.

Usage: python scripts/scheduler.py --url SUPABASE_URL --key SUPABASE_KEY [--interval HOURS] [--batch-size SIZE]
"""

import os
import sys
import time
import argparse
import logging
import schedule
import subprocess
import datetime
import signal
import threading
from typing import Dict, Any, Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_INTERVAL = 24  # hours
DEFAULT_BATCH_SIZE = 50
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPTS_DIR, 'scheduler_config.json')

# Time window settings (24-hour format)
START_HOUR = 0  # 12:00 AM
END_HOUR = 18   # 6:00 PM

# Global variables
running_job = None
stop_event = threading.Event()


def load_config() -> Dict[str, Any]:
    """Load configuration from file if it exists."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
    
    return {}


def save_config(config: Dict[str, Any]):
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved")
    except Exception as e:
        logger.error(f"Error saving config: {str(e)}")


def is_within_time_window() -> bool:
    """Check if current time is within the allowed window (12:00 AM - 6:00 PM)."""
    current_hour = datetime.datetime.now().hour
    return START_HOUR <= current_hour < END_HOUR


def run_image_update(supabase_url: str, supabase_key: str, batch_size: int, max_workers: int = 5) -> Optional[subprocess.Popen]:
    """Run the image update script as a subprocess."""
    try:
        # Check if we're within the allowed time window
        if not is_within_time_window():
            logger.info(f"Outside of allowed time window ({START_HOUR}:00 - {END_HOUR}:00). Skipping job.")
            return None
            
        job_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"update_job_{job_id}.log"
        
        logger.info(f"Starting image update job {job_id}")
        logger.info(f"Logs will be written to {log_file}")
        
        # Path to the script
        script_path = os.path.join(SCRIPTS_DIR, 'fix_broken_images_bulk.py')
        
        # Open log file
        log_fd = open(log_file, 'w')
        
        # Command to run
        cmd = [
            sys.executable,
            script_path,
            '--url', supabase_url,
            '--key', supabase_key,
            '--batch-size', str(batch_size),
            '--max-workers', str(max_workers)
        ]
        
        # Run the process
        process = subprocess.Popen(
            cmd,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        logger.info(f"Process started with PID: {process.pid}")
        return process
    
    except Exception as e:
        logger.error(f"Failed to start image update job: {str(e)}")
        return None


def check_process(process: subprocess.Popen) -> bool:
    """Check if a process is still running."""
    if process is None:
        return False
    
    return process.poll() is None


def stop_process(process: subprocess.Popen):
    """Stop a running process."""
    if process and check_process(process):
        logger.info(f"Stopping process with PID: {process.pid}")
        try:
            process.terminate()
            # Wait for process to terminate
            for _ in range(5):  # 5 second timeout
                if process.poll() is not None:
                    break
                time.sleep(1)
            
            # If still running, kill it
            if process.poll() is None:
                process.kill()
                process.wait()
            
            logger.info("Process stopped")
        except Exception as e:
            logger.error(f"Error stopping process: {str(e)}")


def job(supabase_url: str, supabase_key: str, batch_size: int, max_workers: int = 5):
    """Scheduled job to run image updates."""
    global running_job
    
    # Check if outside of time window
    if not is_within_time_window():
        logger.info(f"Outside of allowed time window ({START_HOUR}:00 - {END_HOUR}:00). Skipping job.")
        return
    
    # Check if a job is already running
    if running_job and check_process(running_job):
        logger.info("A job is already running, skipping this run")
        return
    
    # Run image update
    running_job = run_image_update(supabase_url, supabase_key, batch_size, max_workers)
    
    # If job was skipped due to time window, don't start monitoring thread
    if running_job is None:
        return
    
    # Create a thread to monitor the process
    def monitor_process():
        while not stop_event.is_set() and check_process(running_job):
            # Check if we're still within the time window
            if not is_within_time_window():
                logger.info(f"Outside of allowed time window ({START_HOUR}:00 - {END_HOUR}:00). Stopping current job.")
                stop_process(running_job)
                break
                
            time.sleep(5)  # Check every 5 seconds
        
        if not stop_event.is_set() and running_job and running_job.poll() is not None:
            exit_code = running_job.returncode
            logger.info(f"Process completed with exit code {exit_code}")
    
    monitor_thread = threading.Thread(target=monitor_process)
    monitor_thread.daemon = True
    monitor_thread.start()


def list_jobs():
    """List all scheduled jobs."""
    jobs = schedule.get_jobs()
    if not jobs:
        logger.info("No scheduled jobs")
    else:
        for i, job in enumerate(jobs, 1):
            logger.info(f"Job {i}: Next run at {job.next_run}")


def signal_handler(sig, frame):
    """Handle process signals for graceful shutdown."""
    logger.info("Shutdown signal received")
    stop_event.set()
    
    # Stop any running job
    if running_job:
        stop_process(running_job)
    
    logger.info("Scheduler shutting down")
    sys.exit(0)


def main():
    """Main function to run the scheduler."""
    parser = argparse.ArgumentParser(description='Schedule product image updates')
    parser.add_argument('--url', help='Supabase URL')
    parser.add_argument('--key', help='Supabase API key')
    parser.add_argument('--interval', type=int, help='Update interval in hours')
    parser.add_argument('--batch-size', type=int, help='Batch size for processing')
    parser.add_argument('--max-workers', type=int, default=5, help='Maximum number of worker threads')
    parser.add_argument('--run-now', action='store_true', help='Run an update immediately')
    parser.add_argument('--status', action='store_true', help='Show scheduler status')
    parser.add_argument('--start-hour', type=int, help='Start hour of the allowed time window (24-hour format)')
    parser.add_argument('--end-hour', type=int, help='End hour of the allowed time window (24-hour format)')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Update config with command line arguments
    supabase_url = args.url or config.get('supabase_url') or os.getenv("SUPABASE_URL")
    supabase_key = args.key or config.get('supabase_key') or os.getenv("SUPABASE_KEY")
    interval = args.interval or config.get('interval', DEFAULT_INTERVAL)
    batch_size = args.batch_size or config.get('batch_size', DEFAULT_BATCH_SIZE)
    max_workers = args.max_workers or config.get('max_workers', 5)
    
    global START_HOUR, END_HOUR
    # Update time window if provided
    START_HOUR = args.start_hour if args.start_hour is not None else config.get('start_hour', START_HOUR)
    END_HOUR = args.end_hour if args.end_hour is not None else config.get('end_hour', END_HOUR)
    
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be provided")
        sys.exit(1)
    
    # Save updated configuration
    config.update({
        'supabase_url': supabase_url,
        'supabase_key': supabase_key,
        'interval': interval,
        'batch_size': batch_size,
        'max_workers': max_workers,
        'start_hour': START_HOUR,
        'end_hour': END_HOUR,
        'last_updated': datetime.datetime.now().isoformat()
    })
    save_config(config)
    
    # Show status if requested
    if args.status:
        logger.info(f"Scheduler Configuration:")
        logger.info(f"Update interval: {interval} hours")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Max workers: {max_workers}")
        logger.info(f"Allowed time window: {START_HOUR}:00 - {END_HOUR}:00")
        
        # Check if current time is within window
        if is_within_time_window():
            logger.info("Current time is within the allowed window")
        else:
            logger.info("Current time is outside the allowed window - jobs will not run now")
            
        list_jobs()
        if running_job and check_process(running_job):
            logger.info(f"A job is currently running (PID: {running_job.pid})")
        else:
            logger.info("No job is currently running")
        return
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Schedule the job to run at the specified interval
    schedule.every(interval).hours.do(
        job, supabase_url=supabase_url, supabase_key=supabase_key, 
        batch_size=batch_size, max_workers=max_workers
    )
    logger.info(f"Image update job scheduled to run every {interval} hours")
    logger.info(f"Allowed time window: {START_HOUR}:00 - {END_HOUR}:00")
    logger.info(f"Next run at {datetime.datetime.now() + datetime.timedelta(hours=interval)}")
    
    # Run immediately if requested
    if args.run_now:
        logger.info("Running image update job now")
        if is_within_time_window():
            job(supabase_url, supabase_key, batch_size, max_workers)
        else:
            logger.info(f"Outside of allowed time window ({START_HOUR}:00 - {END_HOUR}:00). Cannot run job now.")
    
    # Keep the script running
    while not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main() 