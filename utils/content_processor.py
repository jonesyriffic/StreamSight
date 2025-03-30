"""
Utility module for processing different content types (PDF, web links, YouTube videos)
"""
import os
import uuid
import logging
import json
from datetime import datetime
from openai import OpenAI

from utils.pdf_processor import extract_text_from_pdf
from utils.web_scraper import extract_text_from_url, is_valid_url
from utils.youtube_processor import process_youtube_url, extract_video_id
from utils.document_ai import generate_document_summary

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# Available document categories
DOCUMENT_CATEGORIES = [
    "Industry Insights",
    "Technology News",
    "Product Management",
    "Customer Service"
]

def process_pdf_upload(uploaded_file, filename, category, user_id, db, Document):
    """
    Process PDF file upload
    
    Args:
        uploaded_file: File object from request.files
        filename: Sanitized filename
        category: Document category (or 'auto' to auto-detect)
        user_id: User ID of uploader
        db: Database session
        Document: Document model class
        
    Returns:
        tuple: (document, status_message, status_code)
    """
    try:
        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Save the file
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Use the document ID in the saved filename to ensure uniqueness
        saved_filename = f"{doc_id}_{filename}"
        filepath = os.path.join(uploads_dir, saved_filename)
        
        uploaded_file.save(filepath)
        
        # Extract text from PDF
        text = extract_text_from_pdf(filepath)
        
        if not text or len(text.strip()) < 50:
            return None, "Could not extract meaningful text from PDF. Please check if the PDF contains text and not just images.", 400
        
        # Detect category if auto is selected
        if category == 'auto':
            detected_category = detect_document_category(text, filename)
            logger.info(f"Auto-detected category for {filename}: {detected_category}")
            category = detected_category
            
        # Create document record
        document = Document(
            id=doc_id,
            filename=filename,
            friendly_name=os.path.splitext(filename)[0],  # Use filename without extension as friendly name
            filepath=filepath,
            text=text,
            category=category,
            user_id=user_id,
            content_type=Document.TYPE_PDF,
            file_available=True
        )
        
        db.session.add(document)
        db.session.commit()
        
        return document, "PDF document uploaded successfully.", 200
        
    except Exception as e:
        logger.error(f"Error processing PDF upload: {str(e)}")
        db.session.rollback()
        return None, f"Error processing PDF: {str(e)}", 500

def process_weblink(url, category, user_id, db, Document):
    """
    Process web link upload
    
    Args:
        url: URL of the webpage
        category: Document category
        user_id: User ID of uploader
        db: Database session
        Document: Document model class
        
    Returns:
        tuple: (document, status_message, status_code)
    """
    try:
        # Validate URL
        if not is_valid_url(url):
            return None, "Please enter a valid URL.", 400
        
        # Extract content from URL
        title, content, status = extract_text_from_url(url)
        
        if not status or not content:
            return None, "Could not extract content from this URL. Please try a different webpage.", 400
        
        if len(content.strip()) < 100:
            return None, "The webpage does not contain enough text content to be processed.", 400
        
        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Detect category if auto is selected
        if category == 'auto':
            detected_category = detect_document_category(content, title)
            logger.info(f"Auto-detected category for weblink {title}: {detected_category}")
            category = detected_category
            
        # Create document record
        document = Document(
            id=doc_id,
            filename=title,  # Use page title as filename
            friendly_name=title,  # Use page title as friendly name
            filepath=url,  # Store URL in filepath for reference
            text=content,
            category=category,
            user_id=user_id,
            content_type=Document.TYPE_WEBLINK,
            source_url=url,  # Store original URL
            file_available=True
        )
        
        db.session.add(document)
        db.session.commit()
        
        return document, "Web link added successfully.", 200
        
    except Exception as e:
        logger.error(f"Error processing web link: {str(e)}")
        db.session.rollback()
        return None, f"Error processing web link: {str(e)}", 500

def process_youtube_video(url, category, user_id, db, Document):
    """
    Process YouTube video upload
    
    Args:
        url: URL of the YouTube video
        category: Document category
        user_id: User ID of uploader
        db: Database session
        Document: Document model class
        
    Returns:
        tuple: (document, status_message, status_code)
    """
    try:
        # Process YouTube URL
        result = process_youtube_url(url)
        
        if not result['success']:
            return None, f"Could not process YouTube URL: {result.get('error', 'Unknown error')}", 400
        
        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Check if we have a transcript
        transcript_text = None
        if result['has_transcript']:
            transcript_text = result['transcript']
        else:
            # Create a placeholder text using video title and author
            logger.info(f"No transcript available for video: {result['video_id']}. Using metadata as placeholder.")
            transcript_text = f"Video Title: {result['title']}\n\nChannel: {result['author']}\n\n"
            transcript_text += "This video does not have an available transcript. When insights are generated, they will be based on the video's title and metadata."
        
        # Detect category if auto is selected
        if category == 'auto':
            # For YouTube videos without transcript, we'll base categorization on title and available info
            if result['has_transcript']:
                detected_category = detect_document_category(transcript_text, result['title'])
            else:
                # If no transcript is available, use a shorter context for category detection
                sample_text = f"Video Title: {result['title']}\nChannel: {result['author']}"
                detected_category = detect_document_category(sample_text, result['title'])
                
            logger.info(f"Auto-detected category for YouTube video '{result['title']}': {detected_category}")
            category = detected_category
            
        # Create document record
        document = Document(
            id=doc_id,
            filename=result['title'] or "YouTube Video",  # Use video title as filename
            friendly_name=result['title'] or "YouTube Video",  # Use video title as friendly name
            filepath=url,  # Store URL in filepath for reference
            text=transcript_text,  # Store transcript as text
            category=category,
            user_id=user_id,
            content_type=Document.TYPE_YOUTUBE,
            source_url=url,  # Store original URL
            youtube_video_id=result['video_id'],  # Store video ID for embedding
            thumbnail_url=result['thumbnail_url'],  # Store thumbnail URL
            file_available=True
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Log if no transcript was available
        if not result['has_transcript']:
            logger.warning(f"Added YouTube video without transcript: {doc_id} ({result['title']})")
            return document, "YouTube video added successfully, but no transcript was available. AI insights will be limited.", 200
        else:
            return document, "YouTube video added successfully.", 200
        
    except Exception as e:
        logger.error(f"Error processing YouTube video: {str(e)}")
        db.session.rollback()
        return None, f"Error processing YouTube video: {str(e)}", 500

def detect_document_category(text, filename=None):
    """
    Auto-detect the document category based on its content
    
    Args:
        text: Document text content
        filename: Optional document filename for additional context
        
    Returns:
        str: Detected category name from DOCUMENT_CATEGORIES list
    """
    try:
        # Prepare a sample of the document text (first 2000 chars)
        text_sample = text[:2000] if text else ""
        
        if not text_sample:
            logger.warning("No text provided for category detection")
            return DOCUMENT_CATEGORIES[0]  # Default to first category
        
        # Create a prompt for the AI to classify the document
        prompt = f"""Classify this document into exactly one of these categories:
{', '.join(DOCUMENT_CATEGORIES)}

Document title/filename: {filename or 'Unknown'}

Document text sample:
{text_sample}

Respond with a single JSON object with a "category" field containing your classification:
"""

        # Use OpenAI to classify the document
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            messages=[
                {"role": "system", "content": "You are a document classification expert for a professional audience."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=100
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        category = result.get("category")
        
        # Validate the category against our list
        if category in DOCUMENT_CATEGORIES:
            logger.info(f"Auto-detected category: {category}")
            return category
        
        # If category not in list, find the closest match
        for valid_category in DOCUMENT_CATEGORIES:
            if valid_category.lower() in category.lower():
                logger.info(f"Using closest category match: {valid_category}")
                return valid_category
        
        # Default to first category if no match
        logger.warning(f"Could not match detected category '{category}' to available categories")
        return DOCUMENT_CATEGORIES[0]
        
    except Exception as e:
        logger.error(f"Error in category detection: {str(e)}")
        return DOCUMENT_CATEGORIES[0]  # Default to first category on error

def generate_content_summary(document, db, openai_api_key=None, is_async=False):
    """
    Generate summary and key points for a document
    
    Args:
        document: Document object
        db: Database session
        openai_api_key: OpenAI API key (optional)
        is_async: Whether to run in async mode
        
    Returns:
        bool: Success status
    """
    try:
        # Skip if document has no text
        if not document.text or len(document.text.strip()) < 100:
            return False
            
        # Call document_ai's generate_document_summary function with the document ID
        from utils.document_ai import generate_document_summary
        
        # Generate summary and key points
        result = generate_document_summary(document.id)
        
        if not result or not result.get('success', False):
            logger.error(f"Failed to generate summary: {result.get('error', 'Unknown error')}")
            return False
            
        # The document is updated directly in the generate_document_summary function
        # No need to update it here again
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating content summary: {str(e)}")
        db.session.rollback()
        return False