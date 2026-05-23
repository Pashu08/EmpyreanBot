"""
utils/logging.py - Error Logging Utilities
Handles file-based error logging with rotation.
"""

import os
import datetime

print("[DEBUG] logging.py: Loading logging utilities...")


MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB


def rotate_log_file(log_path):
    """
    Rotate log file if it exceeds max size.
    Renames the current log to _old.log and starts a new one.
    
    Args:
        log_path (str): Path to the log file
    """
    if os.path.exists(log_path) and os.path.getsize(log_path) > MAX_LOG_SIZE:
        old_log = log_path.replace(".log", "_old.log")
        if os.path.exists(old_log):
            os.remove(old_log)
        os.rename(log_path, old_log)


def log_error_to_file(error_message):
    """
    Append an error message to bot_errors.log.
    Rotates the file if it exceeds 5 MB.
    
    Args:
        error_message (str): Error message to log
    """
    log_path = "bot_errors.log"
    try:
        rotate_log_file(log_path)
        with open(log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {error_message}\n")
    except:
        pass  # Fail silently if logging fails

print("[DEBUG] logging.py: Logging utilities loaded successfully")