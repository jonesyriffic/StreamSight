"""
Relevance reason generator for documents
"""
import os
import json
import logging
from models import User
import openai

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_client = openai.OpenAI(api_key=openai_api_key)

def generate_relevance_reasons(document):
    """
    Generate personalized relevance reasons for different team specializations
    
    Args:
        document: Document object with text and category
        
    Returns:
        dict: Dictionary with team specializations as keys and relevance reasons as values
    """
    try:
        # Prepare document info for better context
        document_info = {
            "title": document.filename,
            "category": document.category,
            "summary": document.summary or "Not available",
            "text_excerpt": document.text[:300] + "..." if document.text and len(document.text) > 300 else document.text
        }
        
        # Get all team specializations
        team_specializations = User.TEAM_CHOICES
        
        # Create a dictionary to store the relevance reasons
        relevance_reasons = {}
        
        for team in team_specializations:
            # Generate relevance reason for this team
            relevance_reason = generate_team_relevance(team, document_info)
            relevance_reasons[team] = relevance_reason
        
        return relevance_reasons
        
    except Exception as e:
        logger.error(f"Error generating relevance reasons: {str(e)}")
        return {}

def generate_team_relevance(team, document_info):
    """
    Generate relevance reason for a specific team
    
    Args:
        team: Team specialization string
        document_info: Document information dictionary
        
    Returns:
        str: Relevance reason for this team
    """
    try:
        # Craft prompt for generating relevance
        prompt = f"""
        Document Information:
        Title: {document_info['title']}
        Category: {document_info['category']}
        Summary: {document_info['summary']}
        Text excerpt: {document_info['text_excerpt']}
        
        Team specialization: {team}
        
        Generate a detailed explanation (2-3 sentences) on why this document is relevant specifically 
        for someone on the {team} team. Include:
        1. A specific insight or data point from the document that's relevant to their role
        2. How it could impact their work or decision-making
        3. A potential action item or takeaway for them
        
        Make it personalized to their role and don't mention the date or when it was published.
        
        Response format:
        {{
            "relevance_reason": "your explanation here"
        }}
        """
        
        # Call OpenAI API to generate the relevance reason
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI assistant that creates personalized document recommendations."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=200
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        return result.get("relevance_reason", "This document contains information relevant to your team's work.")
        
    except Exception as e:
        logger.error(f"Error generating relevance for team {team}: {str(e)}")
        return "This document may contain valuable insights for your team's work."