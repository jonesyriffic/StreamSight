"""
Text processing utilities for the application
"""
import re
import humanize
from datetime import datetime

# HTML tag cleaning pattern
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

def clean_html(text):
    """
    Remove HTML tags from text
    
    Args:
        text: Text that might contain HTML tags
        
    Returns:
        Cleaned text without HTML tags
    """
    if not text:
        return ""
    return HTML_TAG_PATTERN.sub('', text)

def format_timestamp(timestamp):
    """
    Format timestamp as a human-readable relative time
    
    Args:
        timestamp: Datetime object
        
    Returns:
        String with relative time (e.g., "2 days ago")
    """
    if not timestamp:
        return "Unknown date"
    
    # Convert to relative time using humanize
    return humanize.naturaltime(datetime.utcnow() - timestamp)