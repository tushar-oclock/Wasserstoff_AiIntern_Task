import os
import logging
import json
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
import PyPDF2

from backend.app.services.ocr_service import perform_ocr

logger = logging.getLogger(__name__)

def process_document(file_path, doc_id, original_filename, processed_folder):
    """
    Process an uploaded document to extract text content.
    Supports PDF, images, and text files.
    
    Args:
        file_path: Path to the uploaded file
        doc_id: Unique ID for the document
        original_filename: Original filename of the document
        processed_folder: Folder to store processed results
        
    Returns:
        dict: Document details including ID, text content, and metadata
    """
    # Create processed folder if it doesn't exist
    os.makedirs(processed_folder, exist_ok=True)
    
    file_ext = os.path.splitext(original_filename)[1].lower()
    
    # Document metadata to return
    doc_details = {
        'id': doc_id,
        'filename': original_filename,
        'file_type': file_ext[1:] if file_ext else 'unknown',
        'original_path': file_path
    }
    
    extracted_text = ""
    page_texts = []
    page_count = 0
    
    try:
        # Process based on file type
        if file_ext in ['.pdf']:
            extracted_text, page_texts, page_count = process_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
            extracted_text, page_count = process_image(file_path)
        elif file_ext in ['.txt', '.md', '.csv']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                extracted_text = f.read()
                page_count = 1
                page_texts = [extracted_text]
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Save the processed text
        processed_path = os.path.join(processed_folder, f"{doc_id}_processed.json")
        with open(processed_path, 'w', encoding='utf-8') as f:
            json.dump({
                'id': doc_id,
                'filename': original_filename,
                'full_text': extracted_text,
                'page_texts': page_texts,
                'page_count': page_count
            }, f, ensure_ascii=False, indent=2)
        
        # Update document details
        doc_details.update({
            'text': extracted_text,
            'page_texts': page_texts,
            'page_count': page_count,
            'processed_path': processed_path
        })
        
        logger.info(f"Successfully processed document: {original_filename}")
        return doc_details
        
    except Exception as e:
        logger.error(f"Error processing document {original_filename}: {str(e)}")
        raise


def process_pdf(file_path):
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        tuple: (full_text, list_of_page_texts, page_count)
    """
    try:
        # Try with PyMuPDF first (better text extraction)
        doc = fitz.open(file_path)
        page_count = len(doc)
        page_texts = []
        full_text = ""
        
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            page_texts.append(page_text)
            full_text += page_text + "\n\n"
        
        doc.close()
        
        # If no text was extracted, the PDF might be scanned
        if not full_text.strip():
            return process_scanned_pdf(file_path)
            
        return full_text, page_texts, page_count
        
    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed, trying PyPDF2: {str(e)}")
        
        # Fallback to PyPDF2
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                page_count = len(reader.pages)
                page_texts = []
                full_text = ""
                
                for page_num in range(page_count):
                    page = reader.pages[page_num]
                    page_text = page.extract_text() or ""
                    page_texts.append(page_text)
                    full_text += page_text + "\n\n"
                
                # If no text was extracted, the PDF might be scanned
                if not full_text.strip():
                    return process_scanned_pdf(file_path)
                    
                return full_text, page_texts, page_count
                
        except Exception as e2:
            logger.error(f"PyPDF2 extraction also failed: {str(e2)}")
            raise ValueError(f"Could not extract text from PDF: {str(e2)}")


def process_scanned_pdf(file_path):
    """
    Process a scanned PDF using OCR.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        tuple: (full_text, list_of_page_texts, page_count)
    """
    logger.info(f"PDF appears to be scanned, using OCR: {file_path}")
    
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        page_texts = []
        full_text = ""
        
        for page_num in range(page_count):
            # Convert PDF page to image
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            
            img_path = f"{file_path}_page_{page_num}.png"
            pix.save(img_path)
            
            # Perform OCR on the image
            page_text = perform_ocr(img_path)
            page_texts.append(page_text)
            full_text += page_text + "\n\n"
            
            # Remove temporary image file
            os.remove(img_path)
        
        doc.close()
        return full_text, page_texts, page_count
        
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        raise ValueError(f"Could not perform OCR on PDF: {str(e)}")


def process_image(file_path):
    """
    Process an image file using OCR.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        tuple: (extracted_text, page_count)
    """
    try:
        extracted_text = perform_ocr(file_path)
        return extracted_text, 1
    except Exception as e:
        logger.error(f"Image OCR processing failed: {str(e)}")
        raise ValueError(f"Could not perform OCR on image: {str(e)}")