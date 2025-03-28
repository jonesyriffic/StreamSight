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
                               "Create a concise executive summary followed by a bulleted list of 3-5 key actionable insights. "
                               "Focus on business implications, customer needs, and product strategy. "
                               "Your summary should be under 300 words and emphasize practical applications of the information."
                },
                {
                    "role": "user",
                    "content": f"Summarize this document:\n\n{doc_text}"
                }
            ],
            max_tokens=700
        )
        
        # Extract the generated summary
        ai_response = response.choices[0].message.content
        
        # Split into summary and key points (assuming summary comes first, then key points as bullets)
        parts = ai_response.split("\n\n", 1)  # Split on first double newline
        
        summary = parts[0]
        key_points = parts[1] if len(parts) > 1 else "No key points extracted."
        
        # Update the document in the database
        document.summary = summary
        document.key_points = key_points
        document.summary_generated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            "success": True,
            "summary": summary,
            "key_points": key_points
        }
    
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }