import os
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
import uuid
import json

from backend.app.config import (
    SESSION_SECRET, UPLOAD_FOLDER, PROCESSED_FOLDER, 
    MAX_CONTENT_LENGTH
)
from backend.app.core.file_utils import allowed_file, create_upload_folders
from backend.app.services.document_processor import process_document
from backend.app.services.vector_store import (
    initialize_vector_store, add_document, 
    search_documents, get_all_documents
)
from backend.app.services.llm_service import generate_document_responses, synthesize_themes
from backend.app.services.theme_identifier import identify_themes

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the app
app = Flask(__name__, 
            template_folder=os.path.join(os.getcwd(), 'templates'),
            static_folder=os.path.join(os.getcwd(), 'static'))
app.secret_key = SESSION_SECRET
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload settings
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create necessary folders
create_upload_folders(UPLOAD_FOLDER, PROCESSED_FOLDER)

# Initialize the vector store
initialize_vector_store()

@app.route('/')
def index():
    """Render the main page of the application."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
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
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{doc_id}_{filename}")
                file.save(file_path)
                
                # Process document to extract text
                doc_details = process_document(file_path, doc_id, filename, app.config['PROCESSED_FOLDER'])
                
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

@app.route('/documents', methods=['GET'])
def get_documents():
    """Retrieve all documents from the vector store."""
    try:
        documents = get_all_documents()
        return jsonify({'documents': documents})
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/query', methods=['POST'])
def query_documents():
    """Process a query against all documents, identify themes, and return results."""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
    
    query = data['query']
    selected_docs = data.get('documentIds', [])  # Optional list of document IDs to limit the query
    
    try:
        # First, test the Groq API connection
        from backend.app.services.llm_service import test_groq_connection
        connection_ok, connection_msg = test_groq_connection()
        
        if not connection_ok:
            logger.error(f"Groq API connection failed: {connection_msg}")
            return jsonify({
                'error': f"API Connection Error: {connection_msg}",
                'document_responses': [],
                'themes': [],
                'synthesized_response': {
                    'synthesized_response': f"Could not process query due to API connection issues: {connection_msg}",
                    'themes_analysis': []
                }
            }), 200  # Return 200 so frontend can display the error message
        
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
        error_msg = str(e)
        
        # Return a more user-friendly error
        if 'api key' in error_msg.lower() or 'authentication' in error_msg.lower():
            return jsonify({
                'error': 'API key error. Please check your GROQ_API_KEY in the .env file.',
                'hint': 'Make sure you have added a valid GROQ_API_KEY to your .env file and restarted the application.'
            }), 200  # Return 200 so frontend shows the message
        else:
            return jsonify({'error': error_msg}), 200  # Return 200 so frontend shows the message

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file size too large error."""
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors."""
    return jsonify({'error': 'Server error, please try again later'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)