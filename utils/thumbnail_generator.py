"""
Thumbnail generator utilities for creating and managing document thumbnails
"""
import os
import uuid
import logging
import requests
from PIL import Image
import fitz  # PyMuPDF
from urllib.parse import urlparse
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define thumbnail dimensions
THUMBNAIL_WIDTH = 400
THUMBNAIL_HEIGHT = 300


def ensure_uploads_dir():
    """Ensure the uploads directory exists"""
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'thumbnails')
    os.makedirs(uploads_dir, exist_ok=True)
    return uploads_dir


def generate_thumbnail_from_pdf(pdf_path, document_id=None):
    """Generate a thumbnail from the first page of a PDF document
    
    Args:
        pdf_path (str): Path to the PDF file
        document_id (str, optional): Document ID for naming the thumbnail
        
    Returns:
        str: Path to the generated thumbnail, or None if generation failed
    """
    # Ensure document_id exists, or generate one
    if not document_id:
        document_id = str(uuid.uuid4())
    
    # Prepare output path
    thumbnails_dir = ensure_uploads_dir()
    thumbnail_filename = f"thumbnail_{document_id}.jpg"
    thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
    thumbnail_url = f"/static/thumbnails/{thumbnail_filename}"
    
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        
        # Get the first page
        if doc.page_count > 0:
            page = doc.load_page(0)  # First page
            
            # Set a zoom factor to get a higher resolution image
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            
            # Get the pixmap
            pix = page.get_pixmap(matrix=mat)
            
            # Save as an image
            pix.save(thumbnail_path)
            
            # Resize the image to standard dimensions
            with Image.open(thumbnail_path) as img:
                img = img.convert('RGB')  # Convert to RGB in case it's RGBA
                img.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT))
                img.save(thumbnail_path, "JPEG", quality=90)
            
            logger.info(f"Generated thumbnail for PDF: {thumbnail_path}")
            return thumbnail_url
            
        else:
            logger.warning("PDF has no pages")
            return None
            
    except Exception as e:
        logger.error(f"Error generating PDF thumbnail: {e}")
        return None


def generate_thumbnail_from_url(url, document_id=None):
    """Generate a thumbnail for a web link
    
    Args:
        url (str): Web URL 
        document_id (str, optional): Document ID for naming the thumbnail
        
    Returns:
        str: Path to the generated thumbnail, or None if generation failed
    """
    try:
        from playwright.sync_api import sync_playwright
        
        # Ensure document_id exists, or generate one
        if not document_id:
            document_id = str(uuid.uuid4())
        
        # Prepare output path
        thumbnails_dir = ensure_uploads_dir()
        thumbnail_filename = f"thumbnail_{document_id}.jpg"
        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
        thumbnail_url = f"/static/thumbnails/{thumbnail_filename}"
        
        # Use playwright to capture a screenshot
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": THUMBNAIL_WIDTH, "height": THUMBNAIL_HEIGHT})
            page.goto(url, wait_until="networkidle")
            page.screenshot(path=thumbnail_path)
            browser.close()
            
        logger.info(f"Generated thumbnail for URL: {thumbnail_path}")
        return thumbnail_url
        
    except ImportError:
        logger.warning("Playwright not installed, falling back to placeholder thumbnail")
        return "/static/images/web_placeholder.svg"
    except Exception as e:
        logger.error(f"Error generating web thumbnail: {e}")
        return None


def generate_thumbnail_from_youtube(video_id, document_id=None):
    """Get the thumbnail for a YouTube video
    
    Args:
        video_id (str): YouTube video ID
        document_id (str, optional): Document ID for naming the thumbnail
        
    Returns:
        str: URL of the YouTube thumbnail
    """
    # YouTube provides thumbnails at predictable URLs
    # We'll use the highest quality available
    thumbnail_options = [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",  # High quality
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",      # Medium quality
        f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",      # Low quality
        f"https://img.youtube.com/vi/{video_id}/default.jpg"         # Lowest quality
    ]
    
    # Try each thumbnail URL in order
    for thumbnail_url in thumbnail_options:
        try:
            response = requests.head(thumbnail_url)
            if response.status_code == 200:
                # If we want to save a local copy
                if document_id:
                    try:
                        thumbnails_dir = ensure_uploads_dir()
                        thumbnail_filename = f"thumbnail_{document_id}.jpg"
                        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                        local_thumbnail_url = f"/static/thumbnails/{thumbnail_filename}"
                        
                        # Download the image
                        img_response = requests.get(thumbnail_url, stream=True)
                        if img_response.status_code == 200:
                            with open(thumbnail_path, 'wb') as f:
                                for chunk in img_response:
                                    f.write(chunk)
                            return local_thumbnail_url
                    except Exception as e:
                        logger.error(f"Error saving YouTube thumbnail locally: {e}")
                
                # Return the YouTube URL if we didn't save locally
                return thumbnail_url
                
        except Exception as e:
            logger.error(f"Error checking YouTube thumbnail {thumbnail_url}: {e}")
    
    # If all fails, return a placeholder
    return "/static/images/youtube_placeholder.svg"


def save_uploaded_thumbnail(file, document_id):
    """Save an uploaded thumbnail file
    
    Args:
        file: Uploaded file object
        document_id (str): Document ID to associate with the thumbnail
        
    Returns:
        str: Path to the saved thumbnail
    """
    try:
        # Prepare output path
        thumbnails_dir = ensure_uploads_dir()
        thumbnail_filename = f"thumbnail_{document_id}.jpg"
        thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
        thumbnail_url = f"/static/thumbnails/{thumbnail_filename}"
        
        # Save the uploaded file
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            file.save(temp.name)
            
            # Resize the image to standard dimensions
            with Image.open(temp.name) as img:
                img = img.convert('RGB')  # Convert to RGB in case it's RGBA
                img.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT))
                img.save(thumbnail_path, "JPEG", quality=90)
                
        logger.info(f"Saved uploaded thumbnail: {thumbnail_path}")
        return thumbnail_url
        
    except Exception as e:
        logger.error(f"Error saving uploaded thumbnail: {e}")
        return None


def generate_document_thumbnail(document):
    """Generate a thumbnail for a document based on its content type
    
    Args:
        document: Document object
        
    Returns:
        str: Path to the generated thumbnail, or None if generation failed
    """
    from models import Document
    
    # Skip if document already has a custom thumbnail
    if document.custom_thumbnail:
        return document.thumbnail_url
        
    # Generate based on content type
    if document.content_type == Document.TYPE_PDF:
        # Generate thumbnail from PDF
        return generate_thumbnail_from_pdf(document.filepath, document.id)
        
    elif document.content_type == Document.TYPE_WEBLINK:
        # Generate thumbnail from web link
        return generate_thumbnail_from_url(document.source_url, document.id)
        
    elif document.content_type == Document.TYPE_YOUTUBE:
        # Generate thumbnail from YouTube video
        return generate_thumbnail_from_youtube(document.youtube_video_id, document.id)
        
    # Default case - use PDF placeholder
    return "/static/images/pdf_placeholder.svg"