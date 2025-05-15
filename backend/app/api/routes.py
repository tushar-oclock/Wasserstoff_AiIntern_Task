from flask import Blueprint, request, jsonify
import logging
import uuid
from werkzeug.utils import secure_filename
import os

from backend.app.core.file_utils import allowed_file
from backend.app.services.document_processor import process_document
from backend.app.services.vector_store import (
    add_document, get_all_documents
)
from backend.app.services.llm_service import generate_document_responses, synthesize_themes
from backend.app.services.theme_identifier import identify_themes
from backend.app.config import UPLOAD_FOLDER, PROCESSED_FOLDER

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__)

@api.route('/upload', methods=['POST'])
def upload_file():
    """Handle document uploads, process them, and store in vector database."""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    uploaded_docs = []
    errors = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            try:
                # Generate a unique ID for the document
                doc_id = str(uuid.uuid4())
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, f"{doc_id}_{filename}")
                file.save(file_path)
                
                # Process document to extract text
                doc_details = process_document(file_path, doc_id, filename, PROCESSED_FOLDER)
                
                # Add to vector store
                add_document(doc_details)
                
                uploaded_docs.append({
                    'id': doc_id,
                    'filename': filename,
                    'status': 'Success',
                    'pages': doc_details.get('page_count', 'N/A')
                })
                
            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                errors.append({'filename': file.filename, 'error': str(e)})
        else:
            if file and file.filename:
                errors.append({'filename': file.filename, 'error': 'Invalid file type'})
            else:
                errors.append({'filename': 'Unknown', 'error': 'Invalid file'})
    
    return jsonify({
        'success': len(uploaded_docs) > 0,
        'documents': uploaded_docs,
        'errors': errors
    })

@api.route('/documents', methods=['GET'])
def get_documents_list():
    """Retrieve all documents from the vector store."""
    try:
        documents = get_all_documents()
        return jsonify({'documents': documents})
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/query', methods=['POST'])
def query_documents():
    """Process a query against all documents, identify themes, and return results."""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    query = data['query']
    selected_docs = data.get('documentIds', [])  # Optional list of document IDs to limit the query
    
    try:
        # Get document responses for the query
        document_responses = generate_document_responses(query, selected_docs)
        
        # Identify themes from the responses
        themes = identify_themes(document_responses)
        
        # Synthesize a final answer with identified themes
        final_response = synthesize_themes(themes, document_responses, query)
        
        return jsonify({
            'document_responses': document_responses,
            'themes': themes,
            'synthesized_response': final_response
        })
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({'error': str(e)}), 500