"""
AI search module for searching through documents using Gemini API
"""
import os
import json
import time
import logging
import re
import concurrent.futures
from functools import partial
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Initialize Gemini client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Model configuration
GEMINI_MODEL = "gemini-1.5-pro"

# Maximum context size for the AI response generation
MAX_CONTEXT_SIZE = 15000  # Characters

# Performance optimization configuration
ENABLE_PARALLEL_SEARCH = True  # Process documents in parallel for faster search
DOCUMENT_TEXT_LIMIT = 6000     # Reduced from 9000 to make processing faster
RELEVANCE_THRESHOLD = 3        # Minimum relevance score to include in results

def process_document(doc, query):
    """
    Process a single document for search relevance.
    This function is designed to be run in parallel.
    
    Args:
        doc: Document to process
        query: Search query
        
    Returns:
        Dictionary with search result or None if not relevant
    """
    try:
        # For very large documents, we might need to chunk them
        doc_text = doc['text'][:DOCUMENT_TEXT_LIMIT]  # Limit text to avoid token limits
        
        # Create a prompt for evaluating document relevance - Optimized for speed
        prompt = f"""
        You are a search assistant helping find relevant information in documents.
        
        SEARCH QUERY: "{query}"
        
        DOCUMENT TEXT:
        {doc_text}
        
        First, evaluate if this document contains information relevant to the search query.
        Then, if relevant, extract up to 2 key passages that best answer the query.
        
        Be concise! Respond with JSON in this format:
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
        
        # Initialize Gemini model
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                "temperature": 0.1,  # Lower temperature for more deterministic results
            }
        )
        
        # Call Gemini API
        response = model.generate_content(prompt)
        
        # Parse response - Gemini might not return perfectly formatted JSON
        try:
            # Try to extract JSON object
            response_text = response.text
            
            # Look for JSON object pattern
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                result_content = json.loads(json_str)
            else:
                # Attempt to parse the entire response as JSON
                result_content = json.loads(response_text)
            
            # Only include relevant documents
            if result_content.get("is_relevant", False) and result_content.get("relevance_score", 0) > RELEVANCE_THRESHOLD:
                return {
                    "document": {
                        "id": doc["id"],
                        "filename": doc["filename"],
                        "friendly_name": doc.get("friendly_name"),
                        "category": doc["category"]
                    },
                    "relevance_score": result_content.get("relevance_score", 0),
                    "passages": result_content.get("passages", []),
                    "summary": result_content.get("summary", "")
                }
            
            # Not relevant, return None
            return None
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try a more forgiving approach
            try:
                # Check if response has the necessary relevance information
                if "is_relevant" in response_text and "true" in response_text.lower():
                    # Extract relevance score if possible
                    score_match = re.search(r'relevance_score"?\s*:\s*(\d+)', response_text)
                    relevance_score = int(score_match.group(1)) if score_match else 5
                    
                    # Extract summary if possible
                    summary_match = re.search(r'summary"?\s*:\s*"([^"]+)"', response_text)
                    summary = summary_match.group(1) if summary_match else "Relevant document found"
                    
                    if relevance_score > RELEVANCE_THRESHOLD:
                        return {
                            "document": {
                                "id": doc["id"],
                                "filename": doc["filename"],
                                "friendly_name": doc.get("friendly_name"),
                                "category": doc["category"]
                            },
                            "relevance_score": relevance_score,
                            "passages": [],  # Unable to extract passages
                            "summary": summary
                        }
                
                # Not relevant or couldn't extract information, return None
                return None
                
            except Exception:
                # Skip this document if we can't parse the response
                return None
    
    except Exception as e:
        logger.error(f"Error processing document {doc.get('id', 'unknown')}: {str(e)}")
        return None

def search_documents(query, document_repository, category_filter="all"):
    """
    Search through documents using Gemini to find relevant information.
    Optimized for faster performance using parallel processing.
    
    Args:
        query: User search query
        document_repository: Document repository with methods to access documents
        category_filter: Category to filter documents by (or 'all')
        
    Returns:
        Dictionary with search results and metadata
    """
    try:
        start_time = time.time()
        logger.debug(f"Searching with Gemini for: '{query}' with category filter: '{category_filter}'")
        
        # Get documents filtered by category if needed
        if category_filter and category_filter.lower() != "all":
            documents = document_repository['get_documents_by_category'](category_filter)
        else:
            documents = document_repository['get_all_documents']()
        
        if not documents:
            logger.warning("No documents found for search")
            return {
                'results': [],
                'search_info': {
                    'elapsed_time': 0,
                    'results_found': 0,
                    'documents_searched': 0,
                    'query': query
                }
            }
        
        # Log the number of documents to be searched
        doc_count = len(documents)
        logger.info(f"Searching through {doc_count} documents with Gemini")
        
        # Process documents - either in parallel or sequentially
        results = []
        if ENABLE_PARALLEL_SEARCH and doc_count > 1:
            # Parallel processing of documents
            logger.info(f"Using parallel processing for {doc_count} documents")
            
            # Create a partial function with the query parameter pre-filled
            process_func = partial(process_document, query=query)
            
            # Use a thread pool to process documents in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, doc_count)) as executor:
                # Start processing all documents
                future_to_doc = {executor.submit(process_func, doc): doc for doc in documents}
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_doc):
                    result = future.result()
                    if result:  # Only include non-None results (i.e., relevant documents)
                        results.append(result)
                        
                        # Log progress for long searches
                        if doc_count > 10 and len(results) % 5 == 0:
                            elapsed_so_far = time.time() - start_time
                            logger.info(f"Search progress: Found {len(results)} relevant documents so far in {elapsed_so_far:.2f} seconds")
        else:
            # Sequential processing for small document sets or when parallel is disabled
            logger.info("Using sequential document processing")
            for doc in documents:
                result = process_document(doc, query)
                if result:  # Only include non-None results
                    results.append(result)
        
        # Sort results by relevance score (highest first)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Calculate and log elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Search completed in {elapsed_time:.2f} seconds. Found {len(results)} relevant documents.")
        
        # Format the return value
        response = {
            'results': results,
            'search_info': {
                'elapsed_time': round(elapsed_time, 2),
                'results_found': len(results),
                'documents_searched': doc_count,
                'query': query
            }
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error searching documents with Gemini: {str(e)}")
        # Return an empty result in the expected format
        return {
            'results': [],
            'search_info': {
                'elapsed_time': 0,
                'results_found': 0,
                'documents_searched': 0,
                'query': query
            }
        }

def generate_search_response(query, search_result):
    """
    Generate an AI response based on search results using Gemini.
    Optimized for faster response generation.
    
    Args:
        query: Original search query
        search_result: Results from search_documents
        
    Returns:
        str: AI-generated response based on search results
    """
    try:
        start_time = time.time()
        results = search_result.get('results', [])
        
        if not results:
            return "I couldn't find any relevant documents matching your query. Please try refining your search terms or browse the document library."
        
        # Extract relevant information from search results - limit to top 2 for faster processing
        document_info = []
        for i, result in enumerate(results[:2]):  # Consider up to 2 top results for faster processing
            doc = result.get('document', {})
            passages = result.get('passages', [])
            
            # Only take most relevant passages to limit context size
            passage_texts = []
            for passage in passages[:2]:  # Limit to 2 passages per document
                if passage.get('text'):
                    # Limit passage length to keep context size manageable
                    passage_text = passage.get('text', '')
                    if len(passage_text) > 500:  # Truncate very long passages
                        passage_text = passage_text[:500] + "..."
                    passage_texts.append(passage_text)
            
            document_info.append({
                "title": doc.get('friendly_name') or doc.get('filename', f"Document {i+1}"),
                "category": doc.get('category', 'Unknown'),
                "relevance": result.get('relevance_score', 0),
                "passages": passage_texts
            })
        
        # Build prompt for Gemini API - optimized for speed
        prompt = f"""
        You are a helpful document search assistant responding to: "{query}"
        
        Based on these document excerpts, provide a clear, concise answer that synthesizes the information:
        """
        
        for i, doc in enumerate(document_info):
            prompt += f"\nDocument {i+1}: {doc['title']}\n"
            
            if doc['passages']:
                for j, passage in enumerate(doc['passages']):
                    prompt += f"- {passage}\n"
            else:
                summary = results[i].get('summary', '')
                if summary:
                    prompt += f"- {summary}\n"
        
        prompt += """
        Guidelines:
        1. Be clear and direct in your answer, citing specific relevant information
        2. Keep your response to 2-3 short paragraphs
        3. Be professional but conversational
        4. Don't waste words on unnecessary lead-ins
        """
        
        # Initialize Gemini model - optimized settings for speed
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                "temperature": 0.1,  # Lower temperature for more deterministic and faster results
                "max_output_tokens": 768,  # Shorter response limit for faster generation
                "top_p": 0.95,  # Slightly more focused sampling for faster generation
            }
        )
        
        # Call Gemini API to generate the summary
        response = model.generate_content(prompt)
        
        # Process and return response
        ai_response = response.text.strip()
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        logger.info(f"Generated search response in {elapsed_time:.2f} seconds: {len(ai_response)} characters")
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error generating search response with Gemini: {str(e)}")
        return "I couldn't generate a complete response based on the search results. Please review the document excerpts below for relevant information."