"""
Relevance reason generator for documents
"""
import os
import json
import logging
from models import User
import openai

# Alias for backward compatibility
def get_document_relevance_reasons(document_info):
    """
    Generate personalized relevance reasons for different team specializations
    based on document info rather than document object
    
    Args:
        document_info: Dictionary with document information (id, title, category, summary, text_excerpt)
        
    Returns:
        dict: Dictionary with team specializations as keys and relevance reasons as values
    """
    try:
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
        logger.error(f"Error generating relevance reasons from document info: {str(e)}")
        return {}

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
        
        Generate a VERY CONCISE explanation (MAXIMUM 2 sentences) on why this document is relevant specifically 
        for someone on the {team} team. Include:
        1. A specific insight from the document that's relevant to their role
        2. A brief impact or action item for their work
        
        Keep it extremely brief, no more than 2 sentences total. Make it personalized to their role and don't mention the date or when it was published.
        
        Respond with a JSON object in this format:
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
                {"role": "system", "content": "You are an AI assistant that creates personalized document recommendations. You respond in JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=200
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        relevance = result.get("relevance_reason")
        
        # If we have a valid response, return the JSON object with the relevance_reason
        if relevance and len(relevance) > 20:
            return result
            
        # Otherwise, fall back to the category-specific messages
        return get_team_specific_fallback(team, document_info)
        
    except Exception as e:
        logger.error(f"Error generating relevance for team {team}: {str(e)}")
        # Provide more specific fallback messages
        return get_team_specific_fallback(team, document_info)

def get_team_specific_fallback(team, document_info):
    """
    Generate a specific fallback message based on team and document category
    
    Args:
        team: Team specialization string
        document_info: Document information dictionary
        
    Returns:
        str: Team-specific relevance fallback
    """
    category = document_info.get("category", "").lower()
    fallback_reason = ""
    
    if "Digital Product" in team:
        if "industry insights" in category:
            fallback_reason = "Contains market trends to inform your help center product roadmap decisions."
        elif "technology news" in category:
            fallback_reason = "Highlights technologies to enhance your help center user experience."
        else:
            fallback_reason = "Offers strategic insights for your help center development initiatives."
            
    elif "Service Technology" in team:
        if "technology news" in category:
            fallback_reason = "Presents CRM updates relevant to your Salesforce implementation work."
        else:
            fallback_reason = "Contains insights to improve your Salesforce CRM processes."
            
    elif "Digital Engagement" in team:
        if "customer service" in category:
            fallback_reason = "Offers strategies to enhance your chatbot and social platform experiences."
        else:
            fallback_reason = "Provides engagement metrics to optimize your digital channel initiatives."
            
    elif "Product Testing" in team:
        if "product management" in category:
            fallback_reason = "Includes testing methodologies to improve your UAT processes."
        else:
            fallback_reason = "Contains insights applicable to your product validation procedures."
            
    elif "Product Insights" in team:
        if "industry insights" in category:
            fallback_reason = "Features data approaches to enhance your Adobe and Salesforce analysis."
        else:
            fallback_reason = "Presents frameworks relevant to your customer insight initiatives."
            
    elif "NextGen Products" in team:
        if "industry insights" in category or "technology news" in category:
            fallback_reason = "Explores technologies directly relevant to your future industry innovation work."
        else:
            fallback_reason = "Provides strategies aligned with your emerging industry trend analysis."
    
    else:
        fallback_reason = "Contains information relevant to your specialized work areas."
        
    # Return the fallback reason in the same format as the AI-generated reason
    return {"relevance_reason": fallback_reason}