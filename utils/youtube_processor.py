"""
Utility module for processing YouTube videos and extracting transcripts
"""
import re
import logging
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

logger = logging.getLogger(__name__)

def extract_video_id(url):
    """
    Extract YouTube video ID from URL
    
    Supports standard YouTube URLs:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    
    Args:
        url: YouTube video URL
        
    Returns:
        str: YouTube video ID or None if not found
    """
    try:
        # Standard YouTube URL pattern
        if 'youtube.com/watch' in url:
            parsed_url = urlparse(url)
            return parse_qs(parsed_url.query).get('v', [None])[0]
            
        # Shortened YouTube URL pattern
        elif 'youtu.be/' in url:
            parsed_url = urlparse(url)
            return parsed_url.path.lstrip('/')
            
        # YouTube Shorts pattern
        elif 'youtube.com/shorts/' in url:
            parsed_url = urlparse(url)
            return parsed_url.path.replace('/shorts/', '')
            
        # Extract ID from embed code
        elif 'youtube.com/embed/' in url:
            parsed_url = urlparse(url)
            return parsed_url.path.replace('/embed/', '')
            
        # Direct video ID input (if it's just the ID)
        elif re.match(r'^[A-Za-z0-9_-]{11}$', url):
            return url
            
        # Couldn't identify the format
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error extracting YouTube video ID: {str(e)}")
        return None

def get_video_info(video_id):
    """
    Get YouTube video information (title, description, thumbnail)
    
    Uses YouTube oEmbed API to get publicly available video information
    without requiring API key
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        dict: Video information or None if error
            - title: Video title
            - author_name: Channel name
            - thumbnail_url: URL of video thumbnail
    """
    try:
        # Use oEmbed API to get basic info without API key
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return {
            'title': data.get('title', 'Untitled YouTube Video'),
            'author_name': data.get('author_name', 'Unknown Channel'),
            'thumbnail_url': data.get('thumbnail_url', None)
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching YouTube video info for ID {video_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error processing YouTube video info for ID {video_id}: {str(e)}")
        return None

def get_video_transcript(video_id, languages=['en', 'en-US']):
    """
    Get transcript from YouTube video
    
    Args:
        video_id: YouTube video ID
        languages: List of preferred languages in order of preference
        
    Returns:
        tuple: (transcript_text, status)
            - transcript_text: Full transcript text or error message
            - status: True if successful, False if error
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to find transcript in preferred languages
        transcript = None
        for lang in languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except:
                continue
                
        # If preferred language not found, use first available
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript()
            except:
                # No generated transcript found either, try getting any available transcript
                try:
                    available_transcripts = list(transcript_list._manually_created_transcripts.values())
                    if available_transcripts:
                        transcript = available_transcripts[0]
                except:
                    pass
            
        # If we still don't have a transcript, return failure
        if not transcript:
            message = "No transcript available for this video."
            logger.warning(f"{message} Video ID: {video_id}")
            return message, False
            
        # Process transcript
        try:
            transcript_data = transcript.fetch()
            full_text = ""
            
            # Combine transcript segments into full text
            for item in transcript_data:
                if isinstance(item, dict):
                    text = item.get('text', '').strip()
                    if text:
                        full_text += text + " "
                elif hasattr(item, 'text'):  # Handle different return types
                    text = item.text.strip()
                    if text:
                        full_text += text + " "
                    
            return full_text.strip(), True
        except Exception as e:
            message = f"Error processing transcript data: {str(e)}"
            logger.error(f"{message} Video ID: {video_id}")
            return message, False
        
    except TranscriptsDisabled:
        message = "Transcripts are disabled for this video."
        logger.warning(f"{message} Video ID: {video_id}")
        return message, False
        
    except Exception as e:
        message = f"Error retrieving transcript: {str(e)}"
        logger.error(f"{message} Video ID: {video_id}")
        return message, False

def process_youtube_url(url):
    """
    Process YouTube URL and extract all relevant information
    
    Args:
        url: YouTube video URL
        
    Returns:
        dict: Result object with the following fields:
            - success: True if successfully processed, False otherwise
            - video_id: YouTube video ID if extracted
            - title: Video title
            - author: Channel name
            - thumbnail_url: URL to video thumbnail
            - transcript: Video transcript text
            - has_transcript: True if transcript was obtained
            - error: Error message if processing failed
    """
    result = {
        'success': False,
        'video_id': None,
        'title': None,
        'author': None,
        'thumbnail_url': None,
        'transcript': None,
        'has_transcript': False,
        'error': None
    }
    
    try:
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            result['error'] = f"Could not extract video ID from URL: {url}"
            return result
            
        result['video_id'] = video_id
        
        # Get video information
        video_info = get_video_info(video_id)
        if not video_info:
            result['error'] = f"Could not retrieve video information for ID: {video_id}"
            return result
            
        result['title'] = video_info.get('title')
        result['author'] = video_info.get('author_name')
        result['thumbnail_url'] = video_info.get('thumbnail_url')
        
        # Try to get transcript
        transcript_text, transcript_status = get_video_transcript(video_id)
        result['transcript'] = transcript_text
        result['has_transcript'] = transcript_status
        
        # Mark as success if we at least got the video info
        result['success'] = True
        
        return result
        
    except Exception as e:
        error_message = f"Error processing YouTube URL: {str(e)}"
        logger.error(error_message)
        result['error'] = error_message
        return result