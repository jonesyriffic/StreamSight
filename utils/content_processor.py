"""
Utility module for processing different content types (PDF, web links, YouTube videos)
"""
import os
import uuid
import logging
from datetime import datetime

from utils.pdf_processor import extract_text_from_pdf
from utils.web_scraper import extract_text_from_url, is_valid_url
from utils.youtube_processor import process_youtube_url, extract_video_id
from utils.document_ai import generate_document_summary

logger = logging.getLogger(__name__)

def process_pdf_upload(uploaded_file, filename, category, user_id, db, Document):
    """
    Process PDF file upload
    
    Args:
        uploaded_file: File object from request.files
        filename: Sanitized filename
        category: Document category
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
        
        # Check if we have a transcript
        if not result['has_transcript']:
            return None, "Could not retrieve transcript for this video. Please try a different video that has captions available.", 400
        
        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())
        
        # Create document record
        document = Document(
            id=doc_id,
            filename=result['title'] or "YouTube Video",  # Use video title as filename
            friendly_name=result['title'] or "YouTube Video",  # Use video title as friendly name
            filepath=url,  # Store URL in filepath for reference
            text=result['transcript'],  # Store transcript as text
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
        
        return document, "YouTube video added successfully.", 200
        
    except Exception as e:
        logger.error(f"Error processing YouTube video: {str(e)}")
        db.session.rollback()
        return None, f"Error processing YouTube video: {str(e)}", 500

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
            
        # Generate summary based on document type
        content_prefix = ""
        if document.content_type == document.TYPE_WEBLINK:
            content_prefix = f"Web page: {document.source_url}\n\n"
        elif document.content_type == document.TYPE_YOUTUBE:
            content_prefix = f"YouTube video transcript: {document.source_url}\n\n"
            
        # Combine prefix with document text
        combined_text = content_prefix + document.text
            
        # Generate summary
        summary_html, key_points_html, summary_status = generate_document_summary(
            combined_text,
            include_key_points=True,
            openai_api_key=openai_api_key
        )
        
        if not summary_status:
            return False
            
        # Update document with summary
        document.summary = summary_html
        document.key_points = key_points_html
        document.summary_generated_at = datetime.utcnow()
        
        # Save the summary
        db.session.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Error generating content summary: {str(e)}")
        db.session.rollback()
        return False