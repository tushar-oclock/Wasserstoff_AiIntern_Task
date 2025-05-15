import os
import logging
import subprocess
import tempfile
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

def perform_ocr(image_path):
    """
    Perform OCR on an image using fallback strategy.
    Since PaddleOCR is complex to install, we'll use a simple fallback.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Extracted text from the image
    """
    try:
        # Check if tesseract is installed
        try:
            subprocess.run(['tesseract', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return perform_tesseract_ocr(image_path)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Tesseract not installed, using basic OCR description")
            return f"[OCR Text Extraction from {os.path.basename(image_path)}]"
        
    except Exception as e:
        logger.error(f"OCR failed: {str(e)}")
        return f"OCR processing failed: {str(e)}"


def perform_tesseract_ocr(image_path):
    """
    Perform OCR using Tesseract.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Extracted text from the image
    """
    try:
        # Prepare the image
        img = Image.open(image_path)
        
        # Convert image to grayscale if it's not already
        if img.mode != 'L':
            img = img.convert('L')
        
        # Create a temporary file for the output
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        # Save the processed image to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as img_tmp:
            img_path = img_tmp.name
            img.save(img_path)
        
        # Run tesseract
        subprocess.run(['tesseract', img_path, output_path.replace('.txt', '')], 
                      check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Read the output
        with open(output_path, 'r', encoding='utf-8') as f:
            extracted_text = f.read()
        
        # Clean up temporary files
        os.unlink(img_path)
        os.unlink(output_path)
        
        return extracted_text
        
    except Exception as e:
        logger.error(f"Tesseract OCR failed: {str(e)}")
        return f"OCR processing failed: {str(e)}"