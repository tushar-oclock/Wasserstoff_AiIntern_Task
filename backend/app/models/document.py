from typing import List, Dict, Any, Optional

class Document:
    """Data structure representing a document in the system."""
    
    def __init__(self, doc_id: str, filename: str, text: str, page_count: int = 0, metadata: Optional[Dict[str, Any]] = None):
        self.doc_id = doc_id
        self.filename = filename
        self.text = text
        self.page_count = page_count
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary representation."""
        return {
            'id': self.doc_id,
            'filename': self.filename,
            'page_count': self.page_count,
            'metadata': self.metadata
        }


class DocumentResponse:
    """Data structure representing a response from a document to a query."""
    
    def __init__(self, doc_id: str, filename: str, response_text: str, citations: Optional[List[Dict[str, str]]] = None):
        self.doc_id = doc_id
        self.filename = filename
        self.response_text = response_text
        self.citations = citations or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document response to dictionary representation."""
        return {
            'id': self.doc_id,
            'filename': self.filename,
            'response': self.response_text,
            'citations': self.citations
        }


class Theme:
    """Data structure representing an identified theme across documents."""
    
    def __init__(self, theme_id: str, name: str, description: str, supporting_docs: Optional[List[str]] = None):
        self.theme_id = theme_id
        self.name = name
        self.description = description
        self.supporting_docs = supporting_docs or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary representation."""
        return {
            'id': self.theme_id,
            'name': self.name,
            'description': self.description,
            'supporting_documents': self.supporting_docs
        }