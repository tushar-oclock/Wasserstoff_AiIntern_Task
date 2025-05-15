import logging
import json
import re
import uuid
from typing import List, Dict, Any, Optional

# Import Groq client
from groq import Groq

# Import config
from backend.app.config import GROQ_API_KEY, MODEL

logger = logging.getLogger(__name__)

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

def identify_themes(document_responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identify common themes across document responses.
    
    Args:
        document_responses: List of responses from individual documents
        
    Returns:
        List of identified themes with supporting document IDs
    """
    try:
        # Prepare document responses summary for the prompt
        # Limit response size to avoid token limit issues
        max_response_chars = 500  # Limit each response to 500 characters
        docs_summary = ""
        for idx, resp in enumerate(document_responses):
            docs_summary += f"\nDOCUMENT {idx+1}: {resp.get('filename', 'Unknown')}\n"
            response_text = resp.get('response', '')
            if len(response_text) > max_response_chars:
                response_text = response_text[:max_response_chars] + "... [truncated]"
            docs_summary += f"Response: {response_text}\n"
            docs_summary += f"Document ID: {resp.get('id', 'Unknown')}\n"
            docs_summary += "--------------------------------------------------\n"
        
        # Prepare the prompt for LLM
        system_prompt = """
        You are a theme identification expert. Your task is to analyze multiple document responses
        and identify common themes across them.
        
        For each identified theme:
        1. Provide a clear, concise name
        2. Write a detailed description
        3. List all document IDs that support this theme
        
        Format your response in valid JSON with the following structure:
        {
            "themes": [
                {
                    "id": "unique_id",
                    "name": "Theme Name",
                    "description": "Detailed description of this theme",
                    "supporting_docs": ["DOC001", "DOC002", ...]
                },
                ...
            ]
        }
        
        Ensure themes are truly present across multiple documents where possible.
        If no common themes exist, identify the most important individual themes.
        Aim to identify 2-5 significant themes.
        """
        
        user_prompt = f"""
        Please analyze the following document responses and identify common themes across them:
        
        {docs_summary}
        
        Identify meaningful themes that connect these documents. For each theme, provide a name,
        description, and list of document IDs that support it.
        """
        
        # Call LLM with the prompt
        response = groq_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        # Extract and parse response
        response_text = response.choices[0].message.content
        # Handle potential JSON parsing errors
        try:
            themes_data = json.loads(response_text if response_text else "{}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {response_text}")
            # Attempt to extract JSON from text response
            if response_text:
                json_match = re.search(r'({.*})', response_text.replace('\n', ' '), re.DOTALL)
                if json_match:
                    try:
                        themes_data = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        themes_data = {"themes": []}
                else:
                    themes_data = {"themes": []}
            else:
                themes_data = {"themes": []}
        
        # Return the identified themes
        if "themes" in themes_data and themes_data["themes"]:
            # Ensure each theme has an ID
            for theme in themes_data["themes"]:
                if "id" not in theme or not theme["id"]:
                    theme["id"] = str(uuid.uuid4())
            logger.info(f"Successfully identified {len(themes_data['themes'])} themes")
            return themes_data["themes"]
        else:
            logger.warning("No themes identified in the response")
            # Log the actual response to debug
            logger.error(f"Full LLM response: {response_text}")
            # Log document content for debugging
            logger.info(f"Document count: {len(document_responses)}")
            
            # Create a fallback theme when none are identified
            fallback_theme = [{
                "id": str(uuid.uuid4()),
                "name": "Document Analysis",
                "description": "Analysis of document content related to the query.",
                "supporting_docs": [resp.get('id') for resp in document_responses if resp.get('id')]
            }]
            
            logger.info("Created fallback theme as no themes were identified")
            return fallback_theme
    
    except Exception as e:
        logger.error(f"Failed to identify themes: {str(e)}")
        # Return empty themes list on error
        return []