import os
import tempfile
import logging
from PyPDF2 import PdfReader
from io import BytesIO

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyPDF2.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        String containing all text extracted from the PDF
    """
    try:
        logger.debug(f"Extracting text from PDF: {pdf_path}")
        
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            # Create PDF reader object
            reader = PdfReader(file)
            
            # Initialize an empty string to store text
            text = ""
            
            # Extract text from each page
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            
            logger.debug(f"Successfully extracted {len(text)} characters from {len(reader.pages)} pages")
            
            if not text.strip():
                logger.warning(f"Extracted text is empty for {pdf_path}")
                return "No readable text found in document"
                
            return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def get_pdf_metadata(pdf_path):
    """
    Extract metadata from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing PDF metadata
    """
    try:
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            metadata = reader.metadata
            
            result = {
                'title': metadata.get('/Title', ''),
                'author': metadata.get('/Author', ''),
                'subject': metadata.get('/Subject', ''),
                'creator': metadata.get('/Creator', ''),
                'producer': metadata.get('/Producer', ''),
                'page_count': len(reader.pages)
            }
            
            logger.debug(f"Extracted metadata from {pdf_path}: {result}")
            return result
    except Exception as e:
        logger.error(f"Error extracting PDF metadata: {str(e)}")
        return {
            'title': '',
            'author': '',
            'subject': '',
            'creator': '',
            'producer': '',
            'page_count': 0
        }
