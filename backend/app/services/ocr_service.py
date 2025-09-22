"""
OCR Service for processing donation receipts
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
import time
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class OCRService:
    """Service for OCR processing of receipts"""
    
    def __init__(self):
        """Initialize OCR service"""
        self.currency_patterns = [
            r'(?:Rs\.?|PKR|₨)\s*([0-9,]+(?:\.[0-9]{2})?)',  # Rs, PKR, ₨ followed by amount
            r'([0-9,]+(?:\.[0-9]{2})?)\s*(?:Rs\.?|PKR|₨)',  # Amount followed by currency
            r'(?:Rupees?|rupees?)\s*([0-9,]+(?:\.[0-9]{2})?)',  # Rupees/rupees
            r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)',  # Generic number with commas
        ]
    
    async def process_receipt(self, image_path: str) -> Dict[str, Any]:
        """
        Process a receipt image and extract amount
        
        Args:
            image_path: Path to the receipt image
            
        Returns:
            Dictionary with detected amount, confidence, text, and bounding boxes
        """
        start_time = time.time()
        
        try:
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            # Preprocess the image
            processed_image = self._preprocess_image(image)
            
            # Extract text using OCR
            ocr_result = self._extract_text_with_boxes(processed_image)
            raw_text = ocr_result['text']
            boxes = ocr_result['boxes']
            
            # Find currency amounts
            detected_amounts = self._extract_amounts(raw_text)
            
            # Calculate confidence
            confidence = self._calculate_confidence(detected_amounts, raw_text)
            
            # Get the most likely amount
            final_amount = detected_amounts[0] if detected_amounts else None
            
            processing_time = time.time() - start_time
            
            logger.info(f"OCR completed in {processing_time:.2f}s - Amount: {final_amount}, Confidence: {confidence}")
            
            return {
                "detected_amount": final_amount,
                "confidence": confidence,
                "currency": "PKR",
                "raw_text": raw_text[:1000],  # Limit text length
                "boxes": boxes[:20],  # Limit number of boxes
                "processing_time": round(processing_time, 2)
            }
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            return {
                "detected_amount": None,
                "confidence": 0.0,
                "currency": "PKR",
                "raw_text": str(e),
                "boxes": [],
                "processing_time": time.time() - start_time
            }
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess image for better OCR results
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=30)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Deskew image
        deskewed = self._deskew(thresh)
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        morph = cv2.morphologyEx(deskewed, cv2.MORPH_CLOSE, kernel)
        morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
        
        # Resize if too small
        height, width = morph.shape
        if width < 1000:
            scale = 1000 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            morph = cv2.resize(morph, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        return morph
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Deskew image to correct rotation
        
        Args:
            image: Input image
            
        Returns:
            Deskewed image
        """
        # Find all white pixels
        coords = np.column_stack(np.where(image > 0))
        
        # Skip deskewing if not enough points
        if len(coords) < 100:
            return image
        
        # Calculate the skew angle
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Rotate only if significant skew
        if abs(angle) > 0.5:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                image, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            return rotated
        
        return image
    
    def _extract_text_with_boxes(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Extract text with bounding boxes using pytesseract
        
        Args:
            image: Preprocessed image
            
        Returns:
            Dictionary with text and bounding boxes
        """
        # Get detailed OCR data
        custom_config = r'--oem 3 --psm 6'
        data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
        
        # Extract text
        text = pytesseract.image_to_string(image, config=custom_config)
        
        # Extract bounding boxes for words with confidence > 30
        boxes = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 30 and data['text'][i].strip():
                box = {
                    'text': data['text'][i],
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'confidence': data['conf'][i]
                }
                boxes.append(box)
        
        return {
            'text': text,
            'boxes': boxes
        }
    
    def _extract_amounts(self, text: str) -> List[float]:
        """
        Extract currency amounts from text
        
        Args:
            text: OCR extracted text
            
        Returns:
            List of detected amounts sorted by likelihood
        """
        amounts = []
        
        for pattern in self.currency_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                try:
                    # Get the amount string
                    amount_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    
                    # Clean the amount string
                    amount_str = amount_str.replace(',', '').replace(' ', '')
                    
                    # Convert to float
                    amount = float(amount_str)
                    
                    # Filter out unlikely amounts
                    if 10 <= amount <= 10000000:  # Between 10 and 10 million
                        amounts.append(amount)
                        
                except (ValueError, AttributeError):
                    continue
        
        # Remove duplicates and sort by frequency
        from collections import Counter
        amount_counts = Counter(amounts)
        sorted_amounts = [amount for amount, _ in amount_counts.most_common()]
        
        return sorted_amounts
    
    def _calculate_confidence(self, amounts: List[float], text: str) -> float:
        """
        Calculate confidence score for detected amounts
        
        Args:
            amounts: List of detected amounts
            text: Original OCR text
            
        Returns:
            Confidence score between 0 and 1
        """
        if not amounts:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Increase confidence if amounts are found
        if len(amounts) > 0:
            confidence += 0.2
        
        # Check for currency indicators
        currency_indicators = ['rs', 'pkr', 'rupee', '₨', 'amount', 'total', 'paid']
        text_lower = text.lower()
        
        indicator_count = sum(1 for indicator in currency_indicators if indicator in text_lower)
        confidence += min(indicator_count * 0.1, 0.3)
        
        # Check text quality (length indicates good OCR)
        if len(text) > 50:
            confidence = min(confidence + 0.1, 1.0)
        
        # Multiple consistent amounts increase confidence
        if len(amounts) > 1 and len(set(amounts[:3])) == 1:
            confidence = min(confidence + 0.2, 1.0)
        
        return round(confidence, 2)