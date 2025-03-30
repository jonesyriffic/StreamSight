"""
AI search module for searching through documents using Gemini API
"""
import os
import json
import time
import logging
import re
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Initialize Gemini client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Model configuration
GEMINI_MODEL = "gemini-1.5-pro"

# Maximum context size for the AI response generation
MAX_CONTEXT_SIZE = 15000  # Characters

def search_documents(query, document_repository, category_filter="all"):
    """
    Search through documents using Gemini to find relevant information.
    
    Args:
        query: User search query
        document_repository: Document repository with methods to access documents
        category_filter: Category to filter documents by (or 'all')
        
    Returns:
        List of search results with document info and relevance scores
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
            return []
        
        # Log the number of documents to be searched
        doc_count = len(documents)
        logger.info(f"Searching through {doc_count} documents with Gemini")
        
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
            
            # Initialize Gemini model
            model = genai.GenerativeModel(
                GEMINI_MODEL,
                generation_config={
                    "temperature": 0.2,
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
                logger.error(f"Failed to parse Gemini response: {e}")
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
                        
                        if relevance_score > 3:
                            results.append({
                                "document": {
                                    "id": doc["id"],
                                    "filename": doc["filename"],
                                    "friendly_name": doc.get("friendly_name"),
                                    "category": doc["category"]
                                },
                                "relevance_score": relevance_score,
                                "passages": [],  # Unable to extract passages
                                "summary": summary
                            })
                except Exception as parsing_error:
                    logger.error(f"Secondary parsing attempt failed: {parsing_error}")
                    # Skip this document if we can't parse the response
        
        # Sort results by relevance score (highest first)
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Calculate and log elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Search completed in {elapsed_time:.2f} seconds. Found {len(results)} relevant documents.")
        
        # Format the return value to match what the app.py is expecting
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
    Generate an AI response based on search results using Gemini
    
    Args:
        query: Original search query
        search_result: Results from search_documents
        
    Returns:
        str: AI-generated response based on search results
    """
    try:
        results = search_result.get('results', [])
        
        if not results:
            return "I couldn't find any relevant documents matching your query. Please try refining your search terms or browse the document library."
        
        # Extract relevant information from search results
        document_info = []
        for i, result in enumerate(results[:3]):  # Consider up to 3 top results
            doc = result.get('document', {})
            passages = result.get('passages', [])
            
            # Collect relevant text passages
            passage_texts = []
            for passage in passages:
                if passage.get('text'):
                    passage_texts.append(passage.get('text'))
            
            document_info.append({
                "title": doc.get('friendly_name') or doc.get('filename', f"Document {i+1}"),
                "category": doc.get('category', 'Unknown'),
                "relevance": result.get('relevance_score', 0),
                "passages": passage_texts
            })
        
        # Build prompt for Gemini API
        prompt = f"""
        You are a helpful document search assistant. Based on the user's query and the document search results,
        provide a clear, concise answer that synthesizes information from the relevant documents.

        User query: "{query}"
        
        Search results:
        """
        
        for i, doc in enumerate(document_info):
            prompt += f"\nDocument {i+1}: {doc['title']} (Category: {doc['category']})\n"
            
            if doc['passages']:
                prompt += "Relevant passages:\n"
                for j, passage in enumerate(doc['passages']):
                    prompt += f"- {passage}\n"
            else:
                prompt += "No specific passages highlighted.\n"
        
        prompt += """
        Guidelines for your response:
        1. Provide a clear, conversational answer to the user's query
        2. Reference specific information from the documents where relevant
        3. If there are conflicting pieces of information, acknowledge them
        4. If the search results don't directly answer the query, provide the closest relevant information
        5. Keep your response to 3-4 concise paragraphs maximum
        6. Use professional but friendly language
        """
        
        # Initialize Gemini model
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024,
            }
        )
        
        # Call Gemini API to generate the summary
        response = model.generate_content(prompt)
        
        # Process and return response
        ai_response = response.text.strip()
        
        # If response is too short, enhance it
        if len(ai_response) < 100 and len(document_info) > 0:
            enhancement_prompt = f"""
            Please elaborate on your answer to the query: "{query}"
            
            You need to provide more details based on the document content. Include specific information 
            from the documents, and make your response more comprehensive while keeping it concise.
            Your response should be at least 3-4 sentences.
            """
            
            enhancement_response = model.generate_content(enhancement_prompt)
            enhanced_text = enhancement_response.text.strip()
            
            if len(enhanced_text) > len(ai_response):
                ai_response = enhanced_text
        
        logger.info(f"Generated search response: {len(ai_response)} characters")
        return ai_response
        
    except Exception as e:
        logger.error(f"Error generating search response with Gemini: {str(e)}")
        return "I couldn't generate a complete response based on the search results. Please review the document excerpts below for relevant information."