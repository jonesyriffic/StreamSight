import os
import json
import logging
from openai import OpenAI
from collections import defaultdict

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
MODEL = "gpt-4o"

def search_documents(query, document_repository, category_filter="all"):
    """
    Search through documents using OpenAI to find relevant information.
    
    Args:
        query: User search query
        document_repository: Document repository with methods to access documents
        category_filter: Category to filter documents by (or 'all')
        
    Returns:
        List of search results with document info and relevance scores
    """
    try:
        logger.debug(f"Searching for: '{query}' with category filter: {category_filter}")
        
        # Get documents filtered by category if needed
        if category_filter and category_filter.lower() != "all":
            documents = document_repository['get_documents_by_category'](category_filter)
        else:
            documents = document_repository['get_all_documents']()
        
        if not documents:
            logger.warning("No documents found for search")
            return []
        
        # For each document, check relevance and extract snippets
        results = []
        for doc in documents:
            # For very large documents, we might need to chunk them
            # For simplicity, we'll use a basic approach here
            doc_text = doc['text'][:9000]  # Limit text to avoid token limits
            
            # Create a prompt for evaluating document relevance
            prompt = f"""
            You are a search assistant helping find relevant information in documents.
            
            SEARCH QUERY: "{query}"
            
            DOCUMENT TEXT:
            {doc_text}
            
            First, evaluate if this document contains information relevant to the search query.
            Then, if relevant, extract up to 3 key passages (with page numbers if possible) that best answer the query.
            
            Respond with JSON in this format:
            {{
                "is_relevant": true/false,
                "relevance_score": 0-10,
                "passages": [
                    {{
                        "text": "exact passage from document",
                        "location": "approximate page or section information"
                    }}
                ],
                "summary": "brief summary of how this document relates to the query"
            }}
            """
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            # Parse response
            try:
                result_content = json.loads(response.choices[0].message.content)
                
                # Only include relevant documents
                if result_content.get("is_relevant", False) and result_content.get("relevance_score", 0) > 3:
                    results.append({
                        "document": {
                            "id": doc["id"],
                            "filename": doc["filename"],
                            "category": doc["category"]
                        },
                        "relevance_score": result_content.get("relevance_score", 0),
                        "passages": result_content.get("passages", []),
                        "summary": result_content.get("summary", "")
                    })
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenAI response: {e}")
        
        # Sort results by relevance score (highest first)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        logger.debug(f"Search returned {len(results)} relevant results")
        return results
    
    except Exception as e:
        logger.error(f"Error during document search: {str(e)}")
        raise Exception(f"Failed to search documents: {str(e)}")

def categorize_content(text):
    """
    Categorize document content using OpenAI.
    
    Args:
        text: Text from document to categorize
        
    Returns:
        Category string (one of: "Industry Insights", "Technology News", 
        "Product Management", or "Customer Service")
    """
    try:
        # Truncate text if too long
        text_sample = text[:8000]  # Only use first 8000 chars to avoid token limits
        
        prompt = f"""
        Categorize the following document into ONE of these categories:
        - Industry Insights
        - Technology News
        - Product Management
        - Customer Service
        
        Document Text:
        {text_sample}
        
        Respond with JSON in this format:
        {{
            "category": "Category Name",
            "confidence": 0-1,
            "explanation": "brief explanation of categorization"
        }}
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        # Parse response
        result = json.loads(response.choices[0].message.content)
        
        logger.debug(f"Categorized document as: {result.get('category')} with confidence {result.get('confidence')}")
        return result.get("category", "Uncategorized")
    
    except Exception as e:
        logger.error(f"Error categorizing content: {str(e)}")
        return "Uncategorized"
