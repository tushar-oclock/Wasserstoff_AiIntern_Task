import os
import logging
import json
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Import Groq client
from groq import Groq

# Import local services
from backend.app.services.vector_store import search_documents, get_document_text, get_document_by_id
from backend.app.services.theme_identifier import identify_themes
from backend.app.config import GROQ_API_KEY, MODEL

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

def test_groq_connection():
    """Test connection to Groq API with a simple query."""
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        return True, "Connection successful"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Groq API connection test failed: {error_msg}")
        
        if 'auth' in error_msg.lower() or 'api key' in error_msg.lower() or '401' in error_msg:
            return False, "Authentication error: Please check your GROQ_API_KEY"
        elif 'timeout' in error_msg.lower() or 'connection' in error_msg.lower():
            return False, "Connection timeout: Unable to reach Groq API"
        else:
            return False, f"API error: {error_msg}"

def generate_document_responses(query: str, selected_doc_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Generate responses to a query from each relevant document.
    
    Args:
        query: User query
        selected_doc_ids: Optional list of document IDs to limit the search
    
    Returns:
        List of document responses with citations
    """
    try:
        # Get all documents if no specific ones are selected
        if not selected_doc_ids:
            from backend.app.services.vector_store import get_all_documents
            all_docs = get_all_documents()
            selected_doc_ids = [doc['id'] for doc in all_docs]
        
        # Prepare document responses
        document_responses = []
        
        for doc_id in selected_doc_ids:
            try:
                # Get document metadata
                doc_metadata = get_document_by_id(doc_id)
                if not doc_metadata:
                    logger.warning(f"Document not found: {doc_id}")
                    continue
                
                # Ensure doc_metadata is a dict to handle None safety
                if isinstance(doc_metadata, dict):
                    doc_metadata_safe = doc_metadata
                else:
                    doc_metadata_safe = {'id': doc_id, 'filename': f'Document {doc_id}'}
                    
                # Get document text
                doc_text = get_document_text(doc_id)
                if not doc_text:
                    logger.warning(f"No text content for document: {doc_id}")
                    continue
                
                # Generate response using LLM
                response_with_citations = query_document_with_llm(
                    query=query,
                    doc_text=doc_text,
                    doc_metadata=doc_metadata_safe  # Use safe version
                )
                
                document_responses.append(response_with_citations)
                
            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {str(e)}")
                # Include error in the response
                # Get safe document metadata even in error case
                doc_meta = get_document_by_id(doc_id)
                filename = doc_meta.get('filename', 'Unknown') if isinstance(doc_meta, dict) else 'Unknown'
                
                document_responses.append({
                    'id': doc_id,
                    'filename': filename,
                    'response': f"Error processing document: {str(e)}",
                    'citations': [],
                    'error': str(e)
                })
        
        return document_responses
    
    except Exception as e:
        logger.error(f"Failed to generate document responses: {str(e)}")
        raise


def query_document_with_llm(query: str, doc_text: str, doc_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Query a document using LLM and generate a response with citations.
    
    Args:
        query: User query
        doc_text: Document text content
        doc_metadata: Document metadata
    
    Returns:
        Document response with citations
    """
    try:
        # Prepare prompt for LLM
        system_prompt = """
        You are a document analysis assistant. You'll analyze a document to answer a query.
        Provide a comprehensive response based only on the document's content.
        
        Include specific citations in your response using the format [Page X, Paragraph Y] or [Section Z].
        If the exact location cannot be determined, use [Document] as a general citation.
        
        Provide fact-based responses with no speculation or external knowledge.
        If the document doesn't contain information to answer the query, state this clearly.
        
        Format your response in valid JSON with the following structure:
        {
            "response": "Your detailed answer here with embedded citations",
            "citations": [
                {"text": "Cited text excerpt", "location": "Page X, Paragraph Y"},
                ...
            ]
        }
        """
        
        # Further limit text to avoid token limit errors
        # Llama3 8b model has a limit of about 6000 tokens per minute
        # A rough estimate is that 1 token ≈ 4 characters, so we need to limit content significantly
        max_chars = 10000  # This should be about 2500 tokens, leaving room for the rest of the prompt
        
        # Prepare user prompt with document info and query
        user_prompt = f"""
        DOCUMENT INFORMATION:
        Title: {doc_metadata.get('filename', 'Unnamed Document')}
        ID: {doc_metadata.get('id', 'Unknown')}
        Pages: {doc_metadata.get('page_count', 'Unknown')}
        
        DOCUMENT CONTENT:
        {doc_text[:max_chars]}
        [Note: Document content has been truncated to fit within token limits. Analysis is based on this excerpt only.]
        
        USER QUERY:
        {query}
        
        Please analyze this document excerpt and provide a concise response to the query with proper citations.
        Keep your response brief and focused. Do not add unnecessary information.
        """
        
        # Call LLM with the prompt
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        # Extract and parse response
        response_text = response.choices[0].message.content
        # Handle potential JSON parsing errors
        try:
            response_data = json.loads(response_text if response_text else "{}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response_text}")
            # Attempt to extract JSON from text response
            if response_text:
                json_match = re.search(r'({.*})', response_text.replace('\n', ' '), re.DOTALL)
                if json_match:
                    try:
                        response_data = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        response_data = {
                            "response": f"Error parsing response: {response_text[:100] if response_text and len(response_text) > 100 else response_text}...",
                            "citations": []
                        }
                else:
                    response_data = {
                        "response": response_text,
                        "citations": []
                    }
            else:
                response_data = {
                    "response": "No response generated",
                    "citations": []
                }
        
        # Format the response
        return {
            'id': doc_metadata.get('id'),
            'filename': doc_metadata.get('filename', 'Unknown'),
            'response': response_data.get('response', ''),
            'citations': response_data.get('citations', [])
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to query document with LLM: {error_msg}")
        
        # Check if it's a connection error
        if 'Connection' in error_msg or 'timeout' in error_msg.lower() or 'network' in error_msg.lower():
            # Generate a simpler response that doesn't need API connection
            logger.info("Connection issue detected, creating fallback document analysis")
            
            # Extract first 500 chars of document for the response
            doc_preview = doc_text[:500] + "..." if len(doc_text) > 500 else doc_text
            
            return {
                'id': doc_metadata.get('id'),
                'filename': doc_metadata.get('filename', 'Unknown'),
                'response': f"This document contains information that might be relevant to your query. Here's a preview: {doc_preview}",
                'citations': [{"text": doc_preview, "location": "Document preview"}],
                'error': "Connection issue - displaying document preview only"
            }
        
        # For API rate limit errors, provide a helpful message
        if 'rate_limit' in error_msg.lower() or 'too large' in error_msg.lower():
            return {
                'id': doc_metadata.get('id'),
                'filename': doc_metadata.get('filename', 'Unknown'),
                'response': f"The document is too large for processing with the current API limitations. Try a smaller document or upgrade the API tier.",
                'citations': [],
                'error': error_msg
            }
            
        # For general errors
        return {
            'id': doc_metadata.get('id'),
            'filename': doc_metadata.get('filename', 'Unknown'),
            'response': f"Error querying document: {error_msg}",
            'citations': [],
            'error': error_msg
        }


def synthesize_themes(themes: List[Dict[str, Any]], document_responses: List[Dict[str, Any]], original_query: str) -> Dict[str, Any]:
    """
    Synthesize the final response based on identified themes.
    
    Args:
        themes: List of identified themes
        document_responses: List of individual document responses
        original_query: Original user query
    
    Returns:
        Synthesized response with themes and citations
    """
    try:
        # Prepare document responses summary for the prompt
        # Limit to even fewer characters to ensure we stay well under token limits
        max_response_chars = 300  # Reduce from 500 to 300 chars
        doc_responses_summary = ""
        for idx, resp in enumerate(document_responses):
            # Only include the first 5 documents if there are many
            if idx >= 5:
                doc_responses_summary += f"\n[Additional {len(document_responses) - 5} documents omitted to stay within token limits]\n"
                break
            
            doc_responses_summary += f"\nDOCUMENT {idx+1}: {resp.get('filename', 'Unknown')}\n"
            response_text = resp.get('response', '')
            if len(response_text) > max_response_chars:
                response_text = response_text[:max_response_chars] + "... [truncated]"
            doc_responses_summary += f"Response: {response_text}\n"
            doc_responses_summary += f"Document ID: {resp.get('id', 'Unknown')}\n"
        
        # Prepare themes summary for the prompt
        themes_summary = ""
        for theme in themes:
            themes_summary += f"\nTHEME: {theme.get('name', 'Unknown')}\n"
            themes_summary += f"Description: {theme.get('description', '')}\n"
            themes_summary += f"Supporting Documents: {', '.join(theme.get('supporting_docs', []))}\n"
        
        # Prepare the prompt for LLM
        system_prompt = """
        You are a research synthesis assistant. Your task is to create a comprehensive synthesized response
        based on identified themes across multiple documents.
        
        For each theme, provide:
        1. A clear explanation of the theme
        2. Evidence supporting the theme with citations to specific documents
        3. How the theme relates to the original query
        
        Format your response in valid JSON with the following structure:
        {
            "synthesized_response": "Your comprehensive answer covering all identified themes",
            "themes_analysis": [
                {
                    "theme_name": "Theme Name",
                    "explanation": "Detailed explanation of this theme",
                    "supporting_evidence": "Evidence with document citations [DOC001, DOC002]",
                    "relevance_to_query": "How this theme relates to the original query"
                },
                ...
            ]
        }
        
        Ensure your response is well-structured, factual, and based only on the provided document information.
        """
        
        user_prompt = f"""
        ORIGINAL QUERY:
        {original_query}
        
        IDENTIFIED THEMES:
        {themes_summary}
        
        DOCUMENT RESPONSES:
        {doc_responses_summary}
        
        Please synthesize a comprehensive response that addresses the original query by analyzing the identified themes
        across all documents. Include specific document citations where appropriate.
        """
        
        # Call LLM with the prompt
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        # Extract and parse response
        response_text = response.choices[0].message.content
        # Handle potential JSON parsing errors
        try:
            response_data = json.loads(response_text if response_text else "{}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response_text}")
            response_data = {
                "synthesized_response": response_text if response_text else "Error generating response",
                "themes_analysis": []
            }
        
        return response_data
    
    except Exception as e:
        logger.error(f"Failed to synthesize themes: {str(e)}")
        
        # Check if it's a connection error
        if 'Connection' in str(e):
            # Create a fallback synthesized response that doesn't require API call
            fallback_response = {
                "synthesized_response": "Unable to synthesize themes due to connection issues. Here's a summary of the documents:",
                "themes_analysis": [],
                "error": str(e)
            }
            
            # Add document summaries directly
            summary_text = "Document Summaries:\n\n"
            for idx, doc in enumerate(document_responses):
                doc_name = doc.get('filename', f'Document {idx+1}')
                summary_text += f"• {doc_name}: {doc.get('response', 'No response')[:200]}...\n\n"
            
            fallback_response["synthesized_response"] += "\n\n" + summary_text
            logger.info("Created fallback synthesis response due to connection error")
            return fallback_response
        
        # For other errors
        return {
            "synthesized_response": f"Error synthesizing themes: {str(e)}",
            "themes_analysis": [],
            "error": str(e)
        }