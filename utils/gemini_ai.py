"""
Gemini AI module for handling AI operations on documents
This module replaces OpenAI with Google's Gemini AI.
"""
import os
import logging
import re
import json
from datetime import datetime
import google.generativeai as genai
from models import db, Document
from utils.relevance_generator_gemini import generate_relevance_reasons

# Initialize Gemini client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

logger = logging.getLogger(__name__)

# Model configuration
GEMINI_MODEL = "gemini-1.5-pro"

def generate_friendly_name(filename):
    """
    Generate a user-friendly name for a document based on its filename using Gemini
    
    Args:
        filename: Original filename of the document
        
    Returns:
        str: User-friendly name for the document
    """
    try:
        # Remove file extensions
        name = re.sub(r'\.[^.]+$', '', filename)
        
        # Replace underscores and hyphens with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Remove any UUID patterns that might be in the filename
        name = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '', name, flags=re.IGNORECASE)
        
        # Clean up any extra spaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        # If the name is still complex or unclear, use AI to generate a better title
        if len(name) > 30 or re.search(r'\d{6,}', name) or name.count(' ') < 1:
            # Get a better title using Gemini
            model = genai.GenerativeModel(GEMINI_MODEL)
            
            prompt = f"""
            You are an expert at creating concise, descriptive document titles.
            Given a filename, create a professional, clear title that would make sense in a 
            document library for product managers. Keep it under 6 words if possible.
            Don't use phrases like 'Report on' or 'Analysis of' unless necessary.
            Don't include dates unless they seem important to the content.
            
            Create a user-friendly title for this document filename: {filename}
            """
            
            response = model.generate_content(prompt)
            
            # Extract the generated title
            friendly_name = response.text.strip()
            
            # Remove any quotation marks that might have been added
            friendly_name = friendly_name.strip('"\'').strip()
            
            return friendly_name
        
        # If the name is already decent, just capitalize words properly
        return ' '.join(word.capitalize() for word in name.split())
        
    except Exception as e:
        logger.error(f"Error generating friendly name with Gemini: {str(e)}")
        # Fall back to the original filename without extension if there's an error
        return re.sub(r'\.[^.]+$', '', filename).replace('_', ' ').replace('-', ' ')

def generate_document_summary(document_id):
    """
    Generate a summary and key points for a document using Gemini API
    
    Args:
        document_id: ID of the document to summarize
        
    Returns:
        dict: Dictionary containing the summary and key points
        
    Raises:
        Exception: If document not found or AI processing fails
    """
    try:
        # Get the document from the database
        document = Document.query.get(document_id)
        if not document:
            raise ValueError(f"Document with ID {document_id} not found")
        
        if not document.text:
            raise ValueError(f"Document with ID {document_id} has no text content")
        
        # Get document text - limit to first 15000 characters to stay within context limits
        doc_text = document.text[:15000]
        
        # Prepare the prompt based on content type
        system_content = "You are an expert document summarizer for a professional audience of product managers. "
        user_content = f"Summarize this document and extract key insights:\n\n{doc_text}"
        
        # Adjust prompt based on content type
        if document.content_type == 'youtube':
            # Check if this is a YouTube video without a transcript
            if "This video does not have an available transcript" in doc_text:
                # Special handling for YouTube videos without transcripts
                video_id = document.youtube_video_id
                video_url = document.source_url
                video_title = document.friendly_name or document.filename
                
                system_content = "You are an expert content analyzer for product managers. "
                system_content += "You're analyzing a YouTube video with limited information (just title and metadata). "
                system_content += "Format your response with two clearly separated sections in this exact order:\n\n"
                system_content += "1. Key Points: A bulleted list of 3-4 likely key points based on the video title and context\n"
                system_content += "2. Summary: A brief description of what the video likely contains based on its title\n\n"
                
                user_content = f"This is a YouTube video titled '{video_title}' (URL: {video_url}, ID: {video_id}).\n\n"
                user_content += "No transcript is available for this video. Based on the title and information provided, "
                user_content += "create a summary and likely key points that would be valuable for product managers. "
                user_content += "Be clear this is based on limited information without access to the full video content."
            else:
                # Regular YouTube video with transcript
                system_content += "You're analyzing a transcript from a YouTube video. "
                user_content = f"Summarize this YouTube video transcript and extract key insights:\n\n{doc_text}"
        elif document.content_type == 'weblink':
            # Web link content
            system_content += "You're analyzing content from a web page. "
            user_content = f"Summarize this web page content and extract key insights:\n\n{doc_text}"
        
        # Add formatting instructions to system content
        system_content += "Format your response with two clearly separated sections in this exact order:\n\n"
        system_content += "1. Key Points: A bulleted list of exactly 4-5 key points from the document\n"
        system_content += "2. Summary: A concise summary of no more than 2 short paragraphs (100-150 words total)\n\n"
        system_content += "Use these exact section headers: 'Key Points:' and 'Summary:'\n\n"
        system_content += "For Key Points:\n"
        system_content += "- Start each point with a bullet point (- )\n"
        system_content += "- Put a clear title in **bold** at the beginning of each point\n" 
        system_content += "- Keep each point focused on a key fact or insight from the document\n"
        system_content += "- Make points brief and direct - one sentence per point is ideal\n\n"
        system_content += "Example format for a key point:\n"
        system_content += "- **Market Growth:** Customer satisfaction increased 24% over the last quarter.\n\n"
        system_content += "Focus on highlighting factual information from the document rather than making recommendations. "
        system_content += "The summary should be objective and concise, capturing the most important information."
        
        # Create full prompt for Gemini (combining system and user content)
        full_prompt = f"{system_content}\n\n{user_content}"
        
        # Initialize Gemini model
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Generate summary using Gemini API
        response = model.generate_content(full_prompt)
        
        # Extract the generated summary
        ai_response = response.text
        
        # Process response to separate key points and summary
        # Look for section markers in AI responses
        key_points_marker = next((m for m in ["Key Points:", "Key Insights:", "Key Takeaways:"] if m in ai_response), None)
        summary_marker = "Summary:" if "Summary:" in ai_response else None
        
        # Initialize formatted sections
        key_points_html = ""
        summary_html = ""
        
        # Extract and format each section based on their markers
        if key_points_marker and summary_marker:
            # Split the text into sections
            key_points_pos = ai_response.find(key_points_marker)
            summary_pos = ai_response.find(summary_marker)
            
            # Extract key points (from key_points_marker to summary_marker)
            key_points_text = ai_response[key_points_pos:summary_pos].strip()
            
            # Extract summary (from summary_marker to end)
            summary_text = ai_response[summary_pos:].strip()
                
            # Format key points as HTML
            key_points_content = key_points_text.replace(key_points_marker, "").strip()
            bullet_items = []
            
            for line in key_points_content.split("\n"):
                line = line.strip()
                if line and (line.startswith("- ") or line.startswith("* ")):
                    # Remove the bullet character
                    if line.startswith("- "):
                        clean_line = line[2:]
                    else:
                        clean_line = line[2:]
                    
                    # Skip empty lines
                    if not clean_line:
                        continue
                    
                    # Use regex to properly handle bold formatting
                    formatted_line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', clean_line)
                    
                    # Format title-description pattern if present (Title: Description)
                    if ":" in formatted_line and "<strong>" in formatted_line:
                        parts = formatted_line.split(":", 1)
                        if "</strong>" in parts[0]:
                            title = parts[0].strip()
                            description = parts[1].strip() if len(parts) > 1 else ""
                            formatted_line = f"{title}:<span class='insight-description'>{description}</span>"
                    
                    bullet_items.append(f"<li class='insight-item'>{formatted_line}</li>")
            
            if bullet_items:
                key_points_html = f"""<div class='key-points-section document-insights-section'>
                    <h3 class='document-insights-heading'>Key Points</h3>
                    <ul class='key-points-list document-insights-list'>
                        {' '.join(bullet_items)}
                    </ul>
                </div>"""
            else:
                key_points_html = """<div class='key-points-section document-insights-section'>
                    <h3 class='document-insights-heading'>Key Points</h3>
                    <p class='document-insights-text'>No key points extracted from document.</p>
                </div>"""
            
            # Format summary as HTML
            summary_content = summary_text.replace(summary_marker, "").strip()
            if summary_content:
                # Process markdown for bold formatting first
                summary_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', summary_content)
                
                # Format with paragraphs
                formatted_summary = ""
                paragraphs = summary_content.split("\n\n")
                for paragraph in paragraphs:
                    if paragraph.strip():
                        # Handle single newlines inside paragraphs
                        paragraph = paragraph.replace("\n", "<br>")
                        formatted_summary += f"<p class='document-insights-paragraph'>{paragraph}</p>"
                
                summary_html = f"""<div class='summary-section document-insights-section'>
                    <h3 class='document-insights-heading'>Summary</h3>
                    <div class='document-insights-content'>{formatted_summary}</div>
                </div>"""
            else:
                summary_html = """<div class='summary-section document-insights-section'>
                    <h3 class='document-insights-heading'>Summary</h3>
                    <p class='document-insights-text'>No summary information available.</p>
                </div>"""
        else:
            # Fallback for unstructured responses
            key_points_html = """<div class='key-points-section document-insights-section'>
                <h3 class='document-insights-heading'>Key Points</h3>
                <p class='document-insights-text'>Unable to extract key points from document.</p>
            </div>"""
            summary_html = f"""<div class='summary-section document-insights-section'>
                <h3 class='document-insights-heading'>Summary</h3>
                <p class='document-insights-paragraph'>{ai_response}</p>
            </div>"""
        
        # Combine all sections in the desired order
        document_insights = f"""
        <div class="document-insights">
            {key_points_html}
            {summary_html}
            <div class="insights-footer">
                <small class="text-muted">Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</small>
            </div>
        </div>
        """
        
        # Extract plain text summary for card display
        # Use regex to remove HTML tags for the plain text summary
        summary_plain_text = ""
        
        # Extract the plain text from the AI response directly
        if key_points_marker and summary_marker:
            # Get the summary part of the response
            summary_start = ai_response.find(summary_marker)
            summary_part = ai_response[summary_start:].replace(summary_marker, "").strip()
            
            # Clean HTML and markdown from summary for plain text
            summary_plain_text = re.sub(r'\*\*(.*?)\*\*', r'\1', summary_part)  # Remove markdown
            summary_plain_text = re.sub(r'<.*?>', '', summary_plain_text)  # Remove any HTML
        else:
            # Fallback to using AI response without HTML
            summary_plain_text = re.sub(r'<.*?>', '', ai_response)
        
        # Update the document in the database
        document.summary = summary_plain_text  # Plain text version for card views
        document.key_points = document_insights  # Store HTML version for detailed document view
        
        # Generate team-specific relevance reasons using our relevance generator
        team_relevance_reasons = generate_relevance_reasons(document)
        
        # Update the document with the generated relevance reasons
        document.relevance_reasons = team_relevance_reasons
        
        document.summary_generated_at = datetime.utcnow()
        db.session.commit()
        
        # Create response object
        response_data = {
            "success": True,
            "document_insights": document_insights,
            "summary": summary_html,  # HTML version for detailed view
            "summary_plain": summary_plain_text,  # Plain text version for cards
            "key_points": key_points_html,
            "generated_at": document.summary_generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        # Return all the data
        return response_data
    
    except Exception as e:
        logger.error(f"Error generating summary with Gemini: {str(e)}")
        # Check for API-specific errors
        if "Gemini API" in str(e) or "API key" in str(e):
            return {
                "success": False,
                "error": "There was an issue connecting to the Gemini AI service. Please try again later or contact your administrator.",
                "technical_error": str(e)
            }
        return {
            "success": False,
            "error": "Failed to generate summary for this document.",
            "technical_error": str(e)
        }