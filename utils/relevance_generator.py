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
        
        Generate an EXTREMELY CONCISE explanation (MAXIMUM 2 VERY SHORT sentences) on why this document is relevant specifically 
        for someone on the {team} team. The TOTAL length must be UNDER 150 characters. Include:
        1. One key insight from the document that's relevant to their role
        2. One brief impact or action item for their work
        
        NEVER exceed 2 short sentences. Keep it extremely brief. Make it personalized to their role and don't mention the date.
        
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
        
        # If we have a valid response, return just the relevance_reason string (not the full JSON object)
        if relevance and len(relevance) > 20:
            return relevance
            
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
            fallback_reason = "Market trends inform help center roadmap. Apply insights to improve user navigation."
        elif "technology news" in category:
            fallback_reason = "New tech enhances help center UX. Implement ideas to boost self-service features."
        else:
            fallback_reason = "Strategic insights for help centers. Use to prioritize development initiatives."
            
    elif "Service Technology" in team:
        if "technology news" in category:
            fallback_reason = "CRM updates impact Salesforce work. Implement these changes in your Service Cloud setup."
        else:
            fallback_reason = "Insights improve CRM processes. Apply to optimize agent productivity workflows."
            
    elif "Digital Engagement" in team:
        if "customer service" in category:
            fallback_reason = "Strategies enhance chatbots. Use to improve AI response accuracy and customer satisfaction."
        else:
            fallback_reason = "Metrics optimize digital channels. Implement to boost social platform engagement."
            
    elif "Product Testing" in team:
        if "product management" in category:
            fallback_reason = "Testing methods improve UAT. Implement these approaches in your validation framework."
        else:
            fallback_reason = "Insights for validation procedures. Apply to enhance your test coverage strategy."
            
    elif "Product Insights" in team:
        if "industry insights" in category:
            fallback_reason = "Data approaches enhance analytics. Use to improve your Adobe dashboards."
        else:
            fallback_reason = "Frameworks for customer insights. Apply to strengthen data-driven decisions."
            
    elif "NextGen Products" in team:
        if "industry insights" in category or "technology news" in category:
            fallback_reason = "Technologies for innovation work. Explore these trends in your emerging products."
        else:
            fallback_reason = "Strategies for trend analysis. Use to identify opportunities in service evolution."
    
    else:
        fallback_reason = "Insights relevant to your work. Apply to enhance team outcomes."
        
    # Return just the fallback reason string, not a dictionary
    return fallback_reason