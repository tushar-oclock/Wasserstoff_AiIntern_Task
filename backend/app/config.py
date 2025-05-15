import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Session secret for Flask
SESSION_SECRET = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# API Keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# File storage paths
UPLOAD_FOLDER = os.path.join(os.getcwd(), "backend/data/uploads")
PROCESSED_FOLDER = os.path.join(os.getcwd(), "backend/data/processed")
CHROMA_PERSIST_DIRECTORY = os.path.join(os.getcwd(), "backend/data/chroma_db")
METADATA_FILE = os.path.join(os.getcwd(), "backend/data/document_metadata.json")

# Vector store settings
COLLECTION_NAME = "document_collection"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# LLM settings
MODEL = "llama3-8b-8192"  # Groq LLM model

# Max upload size (32MB)
MAX_CONTENT_LENGTH = 32 * 1024 * 1024

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'md', 'csv', 'tiff', 'bmp', 'gif'}