import os
import logging
import json
import chromadb
from typing import List, Dict, Optional, Any

from backend.app.config import CHROMA_PERSIST_DIRECTORY, COLLECTION_NAME, METADATA_FILE
from backend.app.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)

# Initialize global client and collection variables
_client = None
_collection = None
_documents_metadata = {}  # In-memory store for document metadata

def initialize_vector_store():
    """
    Initialize ChromaDB client and collection.
    """
    global _client, _collection, _documents_metadata
    
    try:
        # Initialize client with persistence using new format
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)
        
        # Create a default embedding function
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        default_ef = DefaultEmbeddingFunction()
        
        try:
            _collection = _client.get_collection(name=COLLECTION_NAME)
            logger.info(f"Using existing collection '{COLLECTION_NAME}'")
        except Exception:
            _collection = _client.create_collection(name=COLLECTION_NAME)
            logger.info(f"Created new collection '{COLLECTION_NAME}'")
        
        # Load document metadata if exists
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                _documents_metadata = json.load(f)
                logger.info(f"Loaded metadata for {len(_documents_metadata)} documents")
                
        return True
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}")
        raise


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks for better semantic search.
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # Split by newlines first to preserve paragraph structure
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If paragraph is too big for a chunk, split it further
        if len(paragraph) > chunk_size:
            words = paragraph.split(' ')
            current_paragraph = ""
            
            for word in words:
                if len(current_paragraph) + len(word) + 1 > chunk_size:
                    # Add current paragraph to the current chunk
                    if len(current_chunk) + len(current_paragraph) + 1 > chunk_size:
                        chunks.append(current_chunk)
                        current_chunk = current_paragraph
                    else:
                        current_chunk += ' ' + current_paragraph if current_chunk else current_paragraph
                    current_paragraph = word
                else:
                    current_paragraph += ' ' + word if current_paragraph else word
                    
            # Add the last part of the paragraph
            if current_paragraph:
                if len(current_chunk) + len(current_paragraph) + 1 > chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = current_paragraph
                else:
                    current_chunk += ' ' + current_paragraph if current_chunk else current_paragraph
        else:
            # If adding this paragraph would exceed chunk size, start a new chunk
            if len(current_chunk) + len(paragraph) + 1 > chunk_size:
                chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                current_chunk += '\n' + paragraph if current_chunk else paragraph
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    # If we need to create overlapping chunks
    if overlap > 0 and len(chunks) > 1:
        overlapped_chunks = []
        for i in range(len(chunks)):
            if i == 0:
                overlapped_chunks.append(chunks[i])
            else:
                # Get the end of the previous chunk to create overlap
                prev_chunk = chunks[i-1]
                overlap_text = prev_chunk[-overlap:] if len(prev_chunk) > overlap else prev_chunk
                overlapped_chunks.append(overlap_text + chunks[i])
        return overlapped_chunks
    
    return chunks


def add_document(doc_details: Dict[str, Any]) -> bool:
    """
    Add a document to the vector store.
    
    Args:
        doc_details: Document details including ID, text content, and metadata
        
    Returns:
        bool: True if successful
    """
    global _collection, _documents_metadata
    
    if not _collection:
        initialize_vector_store()
    
    try:
        doc_id = doc_details['id']
        text = doc_details.get('text', '')
        
        # Store document metadata
        _documents_metadata[doc_id] = {
            'id': doc_id,
            'filename': doc_details.get('filename', ''),
            'file_type': doc_details.get('file_type', ''),
            'page_count': doc_details.get('page_count', 0),
            'processed_path': doc_details.get('processed_path', '')
        }
        
        # Save metadata to file
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(_documents_metadata, f, ensure_ascii=False, indent=2)
        
        # Split text into chunks
        chunks = _split_text(text)
        
        # If no chunks, create one empty chunk to at least index the document
        if not chunks:
            chunks = [""]
        
        # Add chunks to collection - ensure collection is available
        if _collection:
            # Add chunks to collection
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
            
            # Convert metadata to a format compatible with ChromaDB
            metadatas = []
            for i in range(len(chunks)):
                metadatas.append({
                    'doc_id': doc_id,
                    'chunk_index': str(i),
                    'filename': doc_details.get('filename', ''),
                    'page_count': str(doc_details.get('page_count', 0))
                })
            
            _collection.add(
                ids=ids,
                documents=chunks,
                metadatas=metadatas
            )
        
        logger.info(f"Added document {doc_id} with {len(chunks)} chunks")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add document to vector store: {str(e)}")
        raise


def search_documents(query: str, doc_ids: Optional[List[str]] = None, n_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for documents matching a query.
    
    Args:
        query: Search query
        doc_ids: Optional list of document IDs to filter the search
        n_results: Number of results to return
        
    Returns:
        List of matching document chunks with metadata
    """
    global _collection
    
    if not _collection:
        initialize_vector_store()
    
    try:
        # Ensure we have a working collection
        if _collection is None:
            logger.error("Collection is not initialized")
            return []
            
        # Prepare where clause if filtering by document IDs
        where_clause = None
        if doc_ids and len(doc_ids) > 0:
            where_clause = {"doc_id": {"$in": doc_ids}}
        
        # Perform search
        results = _collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_clause
        )
        
        # Format results
        formatted_results = []
        if results is not None and 'ids' in results and results['ids'] and len(results['ids']) > 0:
            for i, doc_id in enumerate(results['ids'][0]):
                if i < len(results['documents'][0]) and i < len(results['metadatas'][0]):
                    chunk_text = results['documents'][0][i]
                    metadata = results['metadatas'][0][i]
                    
                    formatted_results.append({
                        'id': doc_id,
                        'doc_id': metadata.get('doc_id', ''),
                        'filename': metadata.get('filename', ''),
                        'chunk_index': metadata.get('chunk_index', 0),
                        'text': chunk_text,
                        'score': results['distances'][0][i] if 'distances' in results and i < len(results['distances'][0]) else None
                    })
        
        return formatted_results
        
    except Exception as e:
        logger.error(f"Failed to search documents: {str(e)}")
        return []


def get_all_documents() -> List[Dict[str, Any]]:
    """
    Get metadata for all documents in the store.
    
    Returns:
        List of document metadata
    """
    global _documents_metadata
    
    try:
        # Initialize documents metadata if it doesn't exist yet
        if not hasattr(globals(), '_documents_metadata') or _documents_metadata is None:
            _documents_metadata = {}
            # Try to load from file if it exists
            if os.path.exists(METADATA_FILE):
                try:
                    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                        _documents_metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load document metadata: {str(e)}")
        
        return list(_documents_metadata.values())
    except Exception as e:
        logger.error(f"Failed to get all documents: {str(e)}")
        return []


def get_document_text(doc_id: str) -> str:
    """
    Get the full text of a document by ID.
    
    Args:
        doc_id: Document ID
        
    Returns:
        Full text of the document
    """
    global _collection, _documents_metadata
    
    if not _collection:
        initialize_vector_store()
    
    try:
        doc_meta = get_document_by_id(doc_id)
        if doc_meta and isinstance(doc_meta, dict):
            processed_path = doc_meta.get('processed_path', '')
            
            if processed_path and os.path.exists(processed_path):
                with open(processed_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('full_text', '')
        
        # Fallback to getting text from collection
        if _collection:
            results = _collection.get(
                where={"doc_id": doc_id}
            )
            
            if results and 'documents' in results and results['documents']:
                return ' '.join(results['documents'])
        
        return ""
        
    except Exception as e:
        logger.error(f"Failed to get document text: {str(e)}")
        return ""


def get_document_by_id(doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Get document metadata by ID.
    
    Args:
        doc_id: Document ID
        
    Returns:
        Document metadata or None if not found
    """
    global _documents_metadata
    
    # Initialize documents metadata if it doesn't exist yet
    if not hasattr(globals(), '_documents_metadata') or _documents_metadata is None:
        _documents_metadata = {}
        # Try to load from file if it exists
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    _documents_metadata = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load document metadata: {str(e)}")
                _documents_metadata = {}
    
    if doc_id in _documents_metadata:
        return _documents_metadata[doc_id]
    
    return None