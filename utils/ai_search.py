import os
import json
import time
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

# Maximum context size for the AI response generation
MAX_CONTEXT_SIZE = 15000  # Characters

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
        start_time = time.time()
        logger.debug(f"Searching for: '{query}' with category filter: '{category_filter}'")
        
        # Get documents filtered by category if needed
        if category_filter and category_filter.lower() != "all":
            documents = document_repository['get_documents_by_category'](category_filter)
        else:
            documents = document_repository['get_all_documents']()
        
        if not documents:
            logger.warning("No documents found for search")
            return []
        
        # Log the number of documents to be searched
        doc_count = len(documents)
        logger.info(f"Searching through {doc_count} documents")
        
        # Estimate search time based on number of documents - rough estimate
        estimated_time_per_doc = 1.5  # seconds per document for AI processing
        total_estimated_time = doc_count * estimated_time_per_doc
        logger.info(f"Estimated search time: {total_estimated_time:.1f} seconds")
        
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
                            "friendly_name": doc.get("friendly_name"),
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
        
        # Calculate and log elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Search completed in {elapsed_time:.2f} seconds, found {len(results)} relevant results")
        
        # Add timing information to the results
        search_info = {
            "elapsed_time": round(elapsed_time, 2),
            "documents_searched": doc_count,
            "results_found": len(results)
        }
        
        # Add metadata to results
        return {
            "results": results,
            "search_info": search_info
        }
    
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

def generate_search_response(query, search_results):
    """
    Generate a comprehensive AI response to a search query based on document search results.
    
    Args:
        query: Original search query from the user
        search_results: List of document search results containing relevant passages
        
    Returns:
        String containing the generated response or an indication of insufficient information
    """
    try:
        logger.debug(f"Generating AI response for query: '{query}'")
        
        # If there are no results, inform that we don't have relevant information
        if not search_results or len(search_results["results"]) == 0:
            return "I don't have enough information in the document library to answer this question confidently. Please try a different query or check back later when more documents are available."
        
        # Extract relevant passages from all documents and combine into context
        context_parts = []
        
        # For each result, extract the relevant passages and document info
        for result in search_results["results"]:
            doc_info = f"\nDocument: {result['document'].get('friendly_name') or result['document']['filename']} (Category: {result['document']['category']})"
            context_parts.append(doc_info)
            
            for passage in result["passages"]:
                passage_text = f"- {passage['text']} [{passage.get('location', 'Unknown location')}]"
                context_parts.append(passage_text)
        
        # Combine context parts but limit to avoid token overflow
        context = "\n".join(context_parts)
        if len(context) > MAX_CONTEXT_SIZE:
            context = context[:MAX_CONTEXT_SIZE] + "... [additional content truncated]"
        
        # Create prompt for generating the response
        prompt = f"""
        You are a helpful AI assistant that provides answers based on information in documents.
        
        USER QUERY: "{query}"
        
        RELEVANT INFORMATION FROM DOCUMENTS:
        {context}
        
        Provide a clear, concise answer to the query based ONLY on the information in these documents.
        When the information is insufficient to fully answer the query, acknowledge the limitations.
        If you need to make assumptions, clearly state them.
        Format your response for readability with bullet points where appropriate.
        When quoting information, indicate the source document.
        DO NOT make up information that isn't present in the provided documents.
        """
        
        # Call OpenAI API for answer generation
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=800
        )
        
        ai_response = response.choices[0].message.content.strip()
        logger.debug(f"Generated AI response of {len(ai_response)} characters")
        
        return ai_response
    
    except Exception as e:
        logger.error(f"Error generating search response: {str(e)}")
        return "Sorry, I encountered an error while trying to generate a response. Please try again."
