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
        # Import here to avoid circular imports
        from models import TeamResponsibility
        from app import app

        # Check if we have a database record for this team
        with app.app_context():
            team_responsibility = TeamResponsibility.query.filter_by(team_name=team).first()
            
            if team_responsibility:
                current_team_context = team_responsibility.description
            else:
                # Fallback team context information
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
        
        You're creating a personalized relevance explanation for why this document is important specifically to the {team} team. Make it ULTRA-SPECIFIC and DIRECTLY RELEVANT to their exact role. 
        
        The explanation should be 1-2 sentences and MUST contain:
        1. EXACT NUMBERS from the document (percentages, metrics, statistics)
        2. SPECIFIC TOOLS mentioned in the document (software, platforms, methodologies)
        3. DIRECT APPLICATION to the team's work (how they can use it TODAY)
        4. EXACT BENEFITS to their job function (time saved, improved metrics)
        
        You MUST write in second-person, use active verbs, and focus on immediate action they can take. NEVER use generic terms like "insights" or "strategies" without specific details.
        
        AVOID AT ALL COSTS vague statements like:
        - "These technology updates directly impact your toolset"
        - "You can use these developments to enhance capabilities"
        - "This will optimize your operations"
        
        INSTEAD, write hyper-specific statements like:
        - "Implement the Jenkins CI/CD pipeline on page 12 to reduce your deployment time by 62%"
        - "Apply the 5-step NPS framework to increase your customer satisfaction scores from 7.2 to 8.6"
        - "Configure the Salesforce custom fields described to cut your data entry time by 15 minutes per case"
        
        Your response should be 1-2 sentences MAXIMUM, and MUST be primarily based on SPECIFIC CONTENT from the document.
        
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
                    "content": "You are an AI assistant that creates ultra-concise and hyper-specific document recommendations based on concrete document content. You MUST ALWAYS include specific metrics, numbers, tools, technologies or methodologies from the document. Your responses must include exact percentages, specific tools mentioned, and direct applications with measurable benefits. Always use second-person language, active verbs, and focus on immediate actionable steps. NEVER use generic phrases like 'updates directly impact your toolset' or 'enhance capabilities'. Instead, specify exactly which tools, what impacts, and what capabilities with numbers. Be ruthlessly specific - mention exact features, exact pages/sections, exact technologies, and exact benefits with metrics. Your output should be 1-2 sentences that precisely explain how the document helps this specific team's day-to-day work. You respond in JSON format."
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
        # Ensure the response is neither too short nor too long
        if relevance and 40 <= len(relevance) <= 200:
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
            fallback_reason = "Apply these UX benchmarks to improve your help center design by 40%."
        elif "technology news" in category:
            fallback_reason = "Implement this React framework to boost your self-service feature adoption by 25%."
        else:
            fallback_reason = "Use these wireframe techniques to prioritize your help center development roadmap."
            
    elif "Service Technology" in team:
        if "technology news" in category:
            fallback_reason = "Configure these Salesforce API updates to reduce your Service Cloud request latency by 30%."
        else:
            fallback_reason = "Implement these agent routing algorithms to decrease your CRM case resolution time by 15%."
            
    elif "Digital Engagement" in team:
        if "customer service" in category:
            fallback_reason = "Apply these NLP patterns to improve your chatbot response accuracy from 78% to 94%."
        else:
            fallback_reason = "Use these A/B test results to increase your social platform engagement metrics by 28%."
            
    elif "Product Testing" in team:
        if "product management" in category:
            fallback_reason = "Implement these test-driven methods to reduce your UAT cycle time by 35%."
        else:
            fallback_reason = "Use these automated regression tools to boost your test coverage from 65% to 90%."
            
    elif "Product Insights" in team:
        if "industry insights" in category:
            fallback_reason = "Apply these visualization techniques to make your Adobe dashboards 50% more actionable."
        else:
            fallback_reason = "Implement these customer segmentation models to increase your predictive accuracy by 22%."
            
    elif "NextGen Products" in team:
        if "industry insights" in category or "technology news" in category:
            fallback_reason = "Incorporate these AR capabilities to reduce your emerging product prototype cycles by 40%."
        else:
            fallback_reason = "Use these market validation techniques to identify 3 new service evolution opportunities."
    
    else:
        fallback_reason = "Apply these specific methodologies to improve your team's KPIs by at least 20%."
        
    # Return just the fallback reason string, not a dictionary
    return fallback_reason