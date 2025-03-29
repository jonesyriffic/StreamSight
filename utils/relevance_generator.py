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
        # Prepare document info for better context - use more document text for better specificity
        document_info = {
            "title": document.friendly_name if document.friendly_name else document.filename,
            "category": document.category,
            "summary": document.summary or "Not available",
            "key_points": document.key_points or "Not available",
            "text_excerpt": document.text[:1000] + "..." if document.text and len(document.text) > 1000 else document.text
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
        # Team context information
        team_context = {
            "Digital Engagement": "Focus on chatbots, AI assistants, and social platforms",
            "Digital Product": "Responsible for self-service help centers and deflection funnels",
            "NextGen Products": "Incubator for upcoming trends, technologies, and next-gen services",
            "Product Insights": "Works with data analysis, Adobe analytics, and Salesforce CRM analytics",
            "Product Testing": "Handles user acceptance testing (UAT) and validation",
            "Service Technology": "Works with Salesforce Service Cloud, agent tooling, live chat, translation tools, and telephony"
        }
        
        # Get context for this team
        current_team_context = team_context.get(team, "Works on specialized product management areas")
        
        # Craft prompt for generating relevance
        prompt = f"""
        Document Information:
        Title: {document_info['title']}
        Category: {document_info['category']}
        Summary: {document_info['summary']}
        Key Points: {document_info['key_points']}
        Text excerpt: {document_info['text_excerpt']}
        
        Team specialization: {team}
        Team context: {current_team_context}
        
        Generate an EXTREMELY SPECIFIC and CONCISE explanation (MAXIMUM 2 VERY SHORT sentences) on why this document is relevant specifically 
        for someone on the {team} team who {current_team_context.lower()}. The TOTAL length must be UNDER 150 characters.
        
        Rules:
        1. Be HYPER-SPECIFIC - mention exact data, metrics, findings or technologies from the document
        2. Cite concrete numbers, tools, or methodologies from the document when possible
        3. Connect a specific insight directly to the team's work based on their context
        4. Use second-person language (e.g., "helps you", "enables your team to")
        5. NEVER use generic statements that could apply to any document
        6. NEVER exceed 2 short sentences or 150 characters total
        
        Make it personalized to their role (using "you" and "your") and don't mention the date.
        Focus on the MOST SPECIFIC and ACTIONABLE insight from the document for this particular team.
        
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
                {
                    "role": "system", 
                    "content": "You are an AI assistant that creates hyper-specific and personalized document recommendations based on actual document content. You focus on concrete details, metrics, methodologies, and specific findings from documents, not generic descriptions. You ALWAYS cite specific numbers, tools, technologies, or methodologies mentioned in the document. You always use second-person language (you/your) to make relevance reasons feel personalized. You respond in JSON format."
                },
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
            fallback_reason = "The market trends help you improve your help center design. You can apply these insights to enhance user navigation."
        elif "technology news" in category:
            fallback_reason = "This tech can enhance your help center UX. You can implement these ideas to boost your self-service features."
        else:
            fallback_reason = "These insights apply to your help center work. You can use them to prioritize your development roadmap."
            
    elif "Service Technology" in team:
        if "technology news" in category:
            fallback_reason = "These CRM updates impact your Salesforce work. You can implement these changes in your Service Cloud setup."
        else:
            fallback_reason = "These findings will improve your CRM processes. You can apply them to optimize your agent productivity."
            
    elif "Digital Engagement" in team:
        if "customer service" in category:
            fallback_reason = "These strategies will enhance your chatbots. You can use them to improve your AI response accuracy."
        else:
            fallback_reason = "These metrics will help optimize your digital channels. You can boost your social platform engagement."
            
    elif "Product Testing" in team:
        if "product management" in category:
            fallback_reason = "These testing methods will improve your UAT work. You can implement them in your validation framework."
        else:
            fallback_reason = "These insights apply to your validation procedures. You can enhance your test coverage strategy."
            
    elif "Product Insights" in team:
        if "industry insights" in category:
            fallback_reason = "These data approaches will enhance your analytics work. You can improve your Adobe dashboard designs."
        else:
            fallback_reason = "These frameworks apply to your customer insights work. You can strengthen your data-driven decisions."
            
    elif "NextGen Products" in team:
        if "industry insights" in category or "technology news" in category:
            fallback_reason = "These technologies apply to your innovation work. You can explore them in your emerging product designs."
        else:
            fallback_reason = "These strategies help with your trend analysis. You can identify new opportunities in service evolution."
    
    else:
        fallback_reason = "These insights directly apply to your work. You can use them to enhance your team's outcomes."
        
    # Return just the fallback reason string, not a dictionary
    return fallback_reason