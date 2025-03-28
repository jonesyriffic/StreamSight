"""
Document AI module for handling AI operations on documents
"""
import os
import logging
from datetime import datetime
from openai import OpenAI
from models import db, Document

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

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
                               "Format your response with two clearly separated sections:\n\n"
                               "1. Executive Summary: A concise paragraph-based summary of the document (200-300 words)\n"
                               "2. Key Insights: A bulleted list of 3-5 key actionable points\n\n"
                               "Always use 'Key Insights:' as the section header for the second part.\n\n"
                               "For Key Insights:\n"
                               "- Start each insight with a bullet point (- )\n"
                               "- Put an actionable title in **bold** at the beginning of each point\n" 
                               "- Elaborate with 1-2 sentences after the bold title\n"
                               "- Keep each insight focused on a single idea\n\n"
                               "Example format for a key insight:\n"
                               "- **Improve Customer Onboarding:** Streamline the first-time user experience to reduce drop-off rates by 15%.\n\n"
                               "Focus on business implications, customer needs, and product strategy. "
                               "Ensure insights are practical and directly applicable to product management work."
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
        
        # Process response to separate summary and key points
        # Look for common section markers in AI responses
        if "Key Insights:" in ai_response or "Key Points:" in ai_response or "Key Takeaways:" in ai_response:
            # Find the marker that exists in the text
            markers = ["Key Insights:", "Key Points:", "Key Takeaways:"]
            marker = next((m for m in markers if m in ai_response), None)
            
            if marker:
                parts = ai_response.split(marker)
                summary = parts[0].strip()
                key_points = marker + parts[1].strip()
                
                # Format summary with paragraphs
                summary = "<p>" + summary.replace("\n\n", "</p><p>") + "</p>"
                summary = summary.replace("\n", "<br>")
                
                # Format key points as a proper HTML list
                key_points_text = key_points.replace(marker, "").strip()
                bullet_items = []
                
                # Process each line that starts with - or * or numbered items
                for line in key_points_text.split("\n"):
                    line = line.strip()
                    if line and (line.startswith("- ") or line.startswith("* ") or (len(line) > 2 and line[0].isdigit() and line[1] == ".")):
                        if line.startswith("- "):
                            line = line[2:]
                        elif line.startswith("* "):
                            line = line[2:]
                        elif len(line) > 2 and line[0].isdigit() and line[1] == ".":
                            line = line[line.find(".")+1:].strip()
                        
                        if line:  # Only add non-empty lines
                            # Process markdown bold formatting (**text**)
                            formatted_line = line
                            
                            # Convert markdown bold to HTML bold
                            if "**" in formatted_line:
                                bold_count = formatted_line.count("**")
                                if bold_count >= 2 and bold_count % 2 == 0:
                                    # Replace pairs of ** with <strong> and </strong>
                                    is_open = True
                                    for _ in range(bold_count // 2):
                                        if is_open:
                                            formatted_line = formatted_line.replace("**", "<strong>", 1)
                                            is_open = False
                                        else:
                                            formatted_line = formatted_line.replace("**", "</strong>", 1)
                                            is_open = True
                            
                            # Add additional formatting for insights that follow the title: description pattern
                            if ":" in formatted_line and "<strong>" in formatted_line:
                                parts = formatted_line.split(":", 1)
                                if "</strong>" in parts[0]:
                                    # Format as title + description
                                    title = parts[0].strip()
                                    description = parts[1].strip()
                                    formatted_line = f"{title}:<span class='insight-description'>{description}</span>"
                            
                            bullet_items.append(f"<li class='insight-item'>{formatted_line}</li>")
                
                # If no properly formatted bullet points were found, try a different approach
                if not bullet_items:
                    # Just split by newlines and make each non-empty line a bullet point
                    for line in key_points_text.split("\n"):
                        line = line.strip()
                        if line:
                            # Process markdown bold formatting (**text**)
                            formatted_line = line
                            
                            # Convert markdown bold to HTML bold
                            if "**" in formatted_line:
                                bold_count = formatted_line.count("**")
                                if bold_count >= 2 and bold_count % 2 == 0:
                                    # Replace pairs of ** with <strong> and </strong>
                                    is_open = True
                                    for _ in range(bold_count // 2):
                                        if is_open:
                                            formatted_line = formatted_line.replace("**", "<strong>", 1)
                                            is_open = False
                                        else:
                                            formatted_line = formatted_line.replace("**", "</strong>", 1)
                                            is_open = True
                            
                            # Format title-description pattern if present
                            if ":" in formatted_line and "<strong>" in formatted_line:
                                parts = formatted_line.split(":", 1)
                                if "</strong>" in parts[0]:
                                    title = parts[0].strip()
                                    description = parts[1].strip()
                                    formatted_line = f"{title}:<span class='insight-description'>{description}</span>"
                                    
                            bullet_items.append(f"<li class='insight-item'>{formatted_line}</li>")
                
                key_points = "<ul class='key-points-list'>" + "".join(bullet_items) + "</ul>"
            else:
                # Fallback if we can't find the markers but have newlines
                parts = ai_response.split("\n\n", 1)
                summary = "<p>" + parts[0].replace("\n", "<br>") + "</p>"
                
                if len(parts) > 1:
                    key_points_text = parts[1].strip()
                    bullet_items = []
                    
                    for line in key_points_text.split("\n"):
                        line = line.strip()
                        if line:
                            # Process markdown formatting here too
                            formatted_line = line
                            
                            # Convert markdown bold to HTML bold
                            if "**" in formatted_line:
                                bold_count = formatted_line.count("**")
                                if bold_count >= 2 and bold_count % 2 == 0:
                                    is_open = True
                                    for _ in range(bold_count // 2):
                                        if is_open:
                                            formatted_line = formatted_line.replace("**", "<strong>", 1)
                                            is_open = False
                                        else:
                                            formatted_line = formatted_line.replace("**", "</strong>", 1)
                                            is_open = True
                            
                            # Format title-description pattern if present
                            if ":" in formatted_line and "<strong>" in formatted_line:
                                parts = formatted_line.split(":", 1)
                                if "</strong>" in parts[0]:
                                    title = parts[0].strip()
                                    description = parts[1].strip()
                                    formatted_line = f"{title}:<span class='insight-description'>{description}</span>"
                                    
                            bullet_items.append(f"<li class='insight-item'>{formatted_line}</li>")
                    
                    key_points = "<ul class='key-points-list'>" + "".join(bullet_items) + "</ul>"
                else:
                    key_points = "<p>No key points extracted.</p>"
        else:
            # Simple fallback for unstructured responses
            summary = "<p>" + ai_response.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
            key_points = "<p>No distinct key points identified in the AI response.</p>"
        
        # Update the document in the database
        document.summary = summary
        document.key_points = key_points
        document.summary_generated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            "success": True,
            "summary": summary,
            "key_points": key_points,
            "generated_at": document.summary_generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    
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