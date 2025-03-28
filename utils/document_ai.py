"""
Document AI module for handling AI operations on documents
"""
import os
import logging
import re
from datetime import datetime
from openai import OpenAI
from models import db, Document
from utils.relevance_generator import generate_relevance_reasons

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

def generate_friendly_name(filename):
    """
    Generate a user-friendly name for a document based on its filename
    
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
            # Get a better title using OpenAI
            response = openai.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating concise, descriptive document titles. "
                                   "Given a filename, create a professional, clear title that would make sense in a "
                                   "document library for product managers. Keep it under 6 words if possible. "
                                   "Don't use phrases like 'Report on' or 'Analysis of' unless necessary. "
                                   "Don't include dates unless they seem important to the content."
                    },
                    {
                        "role": "user",
                        "content": f"Create a user-friendly title for this document filename: {filename}"
                    }
                ],
                max_tokens=50
            )
            
            # Extract the generated title
            friendly_name = response.choices[0].message.content.strip()
            
            # Remove any quotation marks that might have been added
            friendly_name = friendly_name.strip('"\'').strip()
            
            return friendly_name
        
        # If the name is already decent, just capitalize words properly
        return ' '.join(word.capitalize() for word in name.split())
        
    except Exception as e:
        logger.error(f"Error generating friendly name: {str(e)}")
        # Fall back to the original filename without extension if there's an error
        return re.sub(r'\.[^.]+$', '', filename).replace('_', ' ').replace('-', ' ')

def generate_document_summary(document_id):
    """
    Generate a summary and key points for a document using OpenAI API
    
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
        if not document or not document.text:
            raise ValueError(f"Document with ID {document_id} not found or has no text content")
        
        # Get document text - limit to first 15000 characters to stay within OpenAI context limits
        doc_text = document.text[:15000]
        
        # Generate summary using OpenAI's API
        response = openai.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert document summarizer for a professional audience of product managers. "
                               "Format your response with two clearly separated sections in this exact order:\n\n"
                               "1. Key Points: A bulleted list of exactly 4-5 key points from the document\n"
                               "2. Summary: A concise summary of no more than 2 short paragraphs (100-150 words total)\n\n"
                               "Use these exact section headers: 'Key Points:' and 'Summary:'\n\n"
                               "For Key Points:\n"
                               "- Start each point with a bullet point (- )\n"
                               "- Put a clear title in **bold** at the beginning of each point\n" 
                               "- Keep each point focused on a key fact or insight from the document\n"
                               "- Make points brief and direct - one sentence per point is ideal\n\n"
                               "Example format for a key point:\n"
                               "- **Market Growth:** Customer satisfaction increased 24% over the last quarter.\n\n"
                               "Focus on highlighting factual information from the document rather than making recommendations. "
                               "The summary should be objective and concise, capturing the most important information."
                },
                {
                    "role": "user",
                    "content": f"Summarize this document and extract key insights:\n\n{doc_text}"
                }
            ],
            max_tokens=700
        )
        
        # Extract the generated summary
        ai_response = response.choices[0].message.content
        
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
                    
                    # Process markdown bold formatting
                    if "**" in clean_line:
                        # Parse and format bold sections
                        bold_count = clean_line.count("**")
                        if bold_count >= 2 and bold_count % 2 == 0:
                            # Replace pairs of ** with <strong> and </strong>
                            formatted_line = clean_line
                            is_open = True
                            for _ in range(bold_count // 2):
                                if is_open:
                                    formatted_line = formatted_line.replace("**", "<strong>", 1)
                                    is_open = False
                                else:
                                    formatted_line = formatted_line.replace("**", "</strong>", 1)
                                    is_open = True
                            
                            # Format title-description pattern if present (Title: Description)
                            if ":" in formatted_line and "<strong>" in formatted_line:
                                parts = formatted_line.split(":", 1)
                                if "</strong>" in parts[0]:
                                    title = parts[0].strip()
                                    description = parts[1].strip() if len(parts) > 1 else ""
                                    formatted_line = f"{title}:<span class='insight-description'>{description}</span>"
                            
                            bullet_items.append(f"<li class='insight-item'>{formatted_line}</li>")
                        else:
                            # If markdown is malformed, just use the raw line
                            bullet_items.append(f"<li class='insight-item'>{clean_line}</li>")
                    else:
                        # No markdown, use line as-is
                        bullet_items.append(f"<li class='insight-item'>{clean_line}</li>")
            
            if bullet_items:
                key_points_html = f"<div class='key-points-section'><h3>Key Points</h3><ul class='key-points-list'>{' '.join(bullet_items)}</ul></div>"
            else:
                key_points_html = "<div class='key-points-section'><h3>Key Points</h3><p>No key points extracted from document.</p></div>"
            
            # Format summary as HTML
            summary_content = summary_text.replace(summary_marker, "").strip()
            if summary_content:
                # Format with paragraphs
                formatted_summary = summary_content.replace("\n\n", "</p><p>")
                # Handle single newlines inside paragraphs
                formatted_summary = formatted_summary.replace("\n", "<br>")
                summary_html = f"<div class='summary-section'><h3>Summary</h3><p>{formatted_summary}</p></div>"
            else:
                summary_html = "<div class='summary-section'><h3>Summary</h3><p>No summary information available.</p></div>"
            
            # Removed relevance section
        else:
            # Fallback for unstructured responses
            key_points_html = "<div class='key-points-section'><h3>Key Points</h3><p>Unable to extract key points from document.</p></div>"
            summary_html = f"<div class='summary-section'><h3>Summary</h3><p>{ai_response}</p></div>"
        
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
        
        # Update the document in the database
        document.summary = summary_html
        document.key_points = key_points_html
        
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
            "summary": summary_html,
            "key_points": key_points_html,
            "generated_at": document.summary_generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        
        # Return all the data
        return response_data
    
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        # Check for API-specific errors
        if "OpenAI API" in str(e) or "API key" in str(e):
            return {
                "success": False,
                "error": "There was an issue connecting to the AI service. Please try again later or contact your administrator.",
                "technical_error": str(e)
            }
        return {
            "success": False,
            "error": "Failed to generate summary for this document.",
            "technical_error": str(e)
        }