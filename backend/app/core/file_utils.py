import os
import logging
from typing import List, Set

from backend.app.config import ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    """
    Check if a file has an allowed extension.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        bool: True if the file extension is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_upload_folders(*folders: str) -> None:
    """
    Create folders for uploaded and processed files.
    
    Args:
        *folders: Folder paths to create
    """
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        logger.info(f"Created folder: {folder}")


def get_file_extension(filename: str) -> str:
    """
    Get the extension of a file.
    
    Args:
        filename: Name of the file
        
    Returns:
        str: File extension without the dot
    """
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def delete_file(file_path: str) -> bool:
    """
    Delete a file from the file system.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if the file was deleted successfully
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {str(e)}")
        return False 