"""
Utility module for scraping web content
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_valid_url(url):
    """Check if the URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"Error validating URL: {str(e)}")
        return False

def extract_text_from_url(url):
    """
    Extract text content from a web page
    
    Args:
        url: URL of the webpage to scrape
        
    Returns:
        tuple: (title, content, status)
            - title: title of the webpage
            - content: text content of the webpage
            - status: True if successful, False otherwise
    """
    try:
        if not is_valid_url(url):
            logger.error(f"Invalid URL format: {url}")
            return None, None, False
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.title.text.strip() if soup.title else "Untitled Webpage"
        
        # Remove scripts, styles, and other non-content elements
        for element in soup(['script', 'style', 'meta', 'noscript', 'header', 'footer', 'nav']):
            element.decompose()
        
        # Get text from paragraph elements first (prioritize main content)
        paragraphs = soup.find_all('p')
        paragraph_text = ' '.join([p.get_text().strip() for p in paragraphs])
        
        # If not enough content from paragraphs, get text from the entire body
        if len(paragraph_text) < 200:
            body = soup.find('body')
            content = body.get_text() if body else soup.get_text()
            
            # Clean the content
            content = re.sub(r'\s+', ' ', content).strip()
        else:
            content = paragraph_text
        
        # Extract metadata (if available)
        meta_description = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
        if meta_tag and meta_tag.get('content'):
            meta_description = meta_tag.get('content').strip()
            
        # Combine meta description with content if available
        if meta_description and not content.startswith(meta_description):
            content = f"{meta_description}\n\n{content}"
        
        return title, content, True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {str(e)}")
        return None, None, False
    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}")
        return None, None, False