import os
import tempfile
import logging
from PyPDF2 import PdfReader
from io import BytesIO

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyPDF2 with optimizations for large files.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        String containing all text extracted from the PDF
    """
    try:
        logger.debug(f"Extracting text from PDF: {pdf_path}")
        
        # Get file size for logging
        file_size = os.path.getsize(pdf_path)
        logger.info(f"Processing PDF file size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
        
        # For large PDFs, use a more memory-efficient approach
        is_large_file = file_size > 50 * 1024 * 1024  # 50MB threshold
        
        if is_large_file:
            logger.info(f"Large PDF detected, using memory-efficient processing")
            return extract_text_from_large_pdf(pdf_path)
            
        # Standard processing for smaller files
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            try:
                # Create PDF reader object
                reader = PdfReader(file)
                total_pages = len(reader.pages)
                logger.info(f"PDF has {total_pages} pages")
                
                # Initialize an empty string to store text
                text = ""
                
                # Extract text from each page with progress logging
                for page_num in range(total_pages):
                    if page_num % 10 == 0 and page_num > 0:
                        logger.info(f"Processed {page_num}/{total_pages} pages...")
                    page = reader.pages[page_num]
                    extracted = page.extract_text()
                    text += extracted + "\n\n"
                
                logger.info(f"Successfully extracted {len(text)} characters from {total_pages} pages")
                
                if not text.strip():
                    logger.warning(f"Extracted text is empty for {pdf_path}")
                    return "No readable text found in document"
                    
                return text
            except Exception as inner_e:
                logger.error(f"Error in standard processing: {str(inner_e)}")
                # If standard processing fails, try the large file approach as a fallback
                logger.info("Trying large file approach as fallback")
                return extract_text_from_large_pdf(pdf_path)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_large_pdf(pdf_path):
    """
    Extract text from a large PDF file using a more memory-efficient approach.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        String containing text extracted from the PDF, potentially truncated
    """
    try:
        logger.info(f"Using large file text extraction for: {pdf_path}")
        
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            # Create PDF reader object
            reader = PdfReader(file)
            total_pages = len(reader.pages)
            logger.info(f"Large PDF has {total_pages} pages")
            
            # For very large PDFs, we may need to limit the number of pages processed
            max_pages = min(100, total_pages)  # Process up to 100 pages
            logger.info(f"Will process up to {max_pages} pages from this document")
            
            # Process text in chunks to avoid memory issues
            chunks = []
            
            # Extract text from each page
            for page_num in range(max_pages):
                if page_num % 5 == 0 and page_num > 0:
                    logger.info(f"Processed {page_num}/{max_pages} pages of large document...")
                try:
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        chunks.append(page_text)
                except Exception as page_error:
                    logger.warning(f"Error extracting text from page {page_num}: {str(page_error)}")
                    continue
            
            # Combine text chunks
            text = "\n\n".join(chunks)
            
            logger.info(f"Successfully extracted {len(text)} characters from {len(chunks)} pages of large document")
            
            if not text.strip():
                logger.warning(f"Extracted text is empty for large PDF {pdf_path}")
                return "No readable text found in document (large file processing)"
            
            if total_pages > max_pages:
                logger.info(f"Note: Only processed {max_pages} of {total_pages} total pages due to file size")
                text += f"\n\n[Note: This is a partial extraction from a {total_pages}-page document. Only the first {max_pages} pages were processed due to file size constraints.]"
                
            return text
    except Exception as e:
        logger.error(f"Error in large file extraction: {str(e)}")
        raise Exception(f"Failed to extract text from large PDF: {str(e)}")

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
