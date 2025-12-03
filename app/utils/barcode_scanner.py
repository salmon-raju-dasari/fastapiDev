import cv2
import numpy as np
from PIL import Image
from pyzxing import BarCodeReader
import base64
import io
import tempfile
import os
from typing import List, Dict, Optional


class BarcodeScanner:
    """Advanced barcode scanner with CLAHE and sharpening for noisy cameras"""
    
    def __init__(self):
        self.reader = BarCodeReader()
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Apply CLAHE and sharpening to improve barcode detection on noisy images"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply sharpening kernel
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(sharpened, None, 10, 7, 21)
        
        return denoised
    
    def decode_from_base64(self, base64_image: str) -> List[Dict[str, str]]:
        """Decode barcodes from base64 image with preprocessing"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_image:
                base64_image = base64_image.split(',')[1]
            
            # Decode base64 to image
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to numpy array
            image_np = np.array(image)
            
            # Preprocess image
            preprocessed = self.preprocess_image(image_np)
            
            # Save preprocessed image to temp file for pyzxing
            temp_path = os.path.join(tempfile.gettempdir(), "barcode_temp.jpg")
            cv2.imwrite(temp_path, preprocessed)
            
            # Decode barcodes (supports multiple barcodes per frame)
            results = self.reader.decode(temp_path, try_harder=True)
            
            if results:
                if isinstance(results, list):
                    return [{"format": r.get("format", "UNKNOWN"), "data": r.get("raw", "")} for r in results]
                else:
                    return [{"format": results.get("format", "UNKNOWN"), "data": results.get("raw", "")}]
            
            return []
        except Exception as e:
            print(f"Error decoding barcode: {e}")
            return []
    
    def decode_from_file(self, file_path: str) -> List[Dict[str, str]]:
        """Decode barcodes from image file with preprocessing"""
        try:
            # Read image
            image = cv2.imread(file_path)
            
            # Preprocess image
            preprocessed = self.preprocess_image(image)
            
            # Save preprocessed image
            temp_path = os.path.join(tempfile.gettempdir(), "barcode_preprocessed.jpg")
            cv2.imwrite(temp_path, preprocessed)
            
            # Decode barcodes
            results = self.reader.decode(temp_path, try_harder=True)
            
            if results:
                if isinstance(results, list):
                    return [{"format": r.get("format", "UNKNOWN"), "data": r.get("raw", "")} for r in results]
                else:
                    return [{"format": results.get("format", "UNKNOWN"), "data": results.get("raw", "")}]
            
            return []
        except Exception as e:
            print(f"Error decoding barcode from file: {e}")
            return []


# Singleton instance
scanner = BarcodeScanner()
