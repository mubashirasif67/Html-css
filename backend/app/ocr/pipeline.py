"""
OCR Pipeline for the Blessings Donation System.

This module provides the main OCR pipeline that combines image preprocessing,
text extraction, and amount detection for donation receipts.
"""

import os
import time
from typing import Dict, List, Optional, Tuple, Any
import structlog
import pytesseract
from PIL import Image
import cv2
import numpy as np

from ..config import settings
from .preprocessing import ImagePreprocessor
from .extraction import AmountExtractor, TextCleaner, ReceiptAnalyzer
from ..donations.schemas import OCRResult

logger = structlog.get_logger(__name__)


class OCRPipeline:
    """Complete OCR pipeline for processing donation receipts."""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.amount_extractor = AmountExtractor()
        self.text_cleaner = TextCleaner()
        self.receipt_analyzer = ReceiptAnalyzer()
        
        # Configure Tesseract
        self.tesseract_config = settings.tesseract_config
        
        # Supported file formats
        self.supported_formats = settings.ocr_supported_formats
    
    def process_image(self, image_path: str, enhance_for_amounts: bool = True) -> OCRResult:
        """
        Process an image through the complete OCR pipeline.
        
        Args:
            image_path: Path to the image file
            enhance_for_amounts: Whether to apply amount-specific enhancements
            
        Returns:
            OCRResult: Complete OCR processing results
        """
        start_time = time.time()
        
        try:
            logger.info("Starting OCR processing", image_path=image_path)
            
            # Validate input
            if not self._validate_image(image_path):
                raise ValueError("Invalid or unsupported image file")
            
            # Step 1: Preprocess image
            processed_image_path = self.preprocessor.preprocess_image(image_path)
            
            # Step 2: Extract text using Tesseract
            raw_text = self._extract_text_tesseract(processed_image_path)
            
            # Step 3: Clean and normalize text
            cleaned_text = self.text_cleaner.clean_text(raw_text)
            
            # Step 4: Analyze receipt and extract amounts
            receipt_analysis = self.receipt_analyzer.analyze_receipt(cleaned_text)
            
            # Step 5: Get text bounding boxes
            text_boxes = self._get_text_boxes(processed_image_path)
            
            # Step 6: Calculate processing metrics
            processing_time = time.time() - start_time
            confidence = receipt_analysis['confidence']
            
            # Create result
            result = OCRResult(
                detected_amount=receipt_analysis['best_amount'],
                currency="PKR",  # Default currency
                confidence=confidence,
                raw_text=cleaned_text,
                processing_time=processing_time,
                text_boxes=text_boxes
            )
            
            logger.info(
                "OCR processing completed",
                image_path=image_path,
                processing_time=processing_time,
                confidence=confidence,
                detected_amount=receipt_analysis['best_amount'],
                text_length=len(cleaned_text)
            )
            
            # Clean up temporary files
            self._cleanup_temp_files(processed_image_path, image_path)
            
            return result
            
        except Exception as e:
            logger.error("OCR processing failed", image_path=image_path, error=str(e))
            
            # Return error result
            processing_time = time.time() - start_time
            return OCRResult(
                detected_amount=None,
                currency="PKR",
                confidence=0.0,
                raw_text=f"OCR processing failed: {str(e)}",
                processing_time=processing_time,
                text_boxes=[]
            )
    
    def process_multiple_images(self, image_paths: List[str]) -> List[OCRResult]:
        """
        Process multiple images in batch.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            List[OCRResult]: Results for each image
        """
        results = []
        
        for image_path in image_paths:
            try:
                result = self.process_image(image_path)
                results.append(result)
            except Exception as e:
                logger.error("Batch OCR processing failed for image", 
                           image_path=image_path, error=str(e))
                # Add error result
                results.append(OCRResult(
                    detected_amount=None,
                    currency="PKR",
                    confidence=0.0,
                    raw_text=f"Processing failed: {str(e)}",
                    processing_time=0.0,
                    text_boxes=[]
                ))
        
        return results
    
    def _validate_image(self, image_path: str) -> bool:
        """Validate that the image file is supported and accessible."""
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                logger.error("Image file not found", image_path=image_path)
                return False
            
            # Check file extension
            file_ext = os.path.splitext(image_path)[1].lower().lstrip('.')
            if file_ext not in self.supported_formats:
                logger.error("Unsupported image format", 
                           format=file_ext, supported=self.supported_formats)
                return False
            
            # Try to load the image
            image = Image.open(image_path)
            image.verify()  # Verify it's a valid image
            
            # Check image dimensions
            image = Image.open(image_path)  # Reopen after verify
            width, height = image.size
            
            if width < 50 or height < 50:
                logger.error("Image too small for OCR", width=width, height=height)
                return False
            
            if width > 10000 or height > 10000:
                logger.error("Image too large for OCR", width=width, height=height)
                return False
            
            return True
            
        except Exception as e:
            logger.error("Image validation failed", image_path=image_path, error=str(e))
            return False
    
    def _extract_text_tesseract(self, image_path: str) -> str:
        """Extract text from image using Tesseract OCR."""
        try:
            # Load image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(
                image, 
                config=self.tesseract_config,
                lang='eng'  # English language
            )
            
            return text.strip()
            
        except Exception as e:
            logger.error("Tesseract text extraction failed", error=str(e))
            return ""
    
    def _get_text_boxes(self, image_path: str) -> List[Dict[str, Any]]:
        """Get bounding boxes for detected text."""
        try:
            image = Image.open(image_path)
            
            # Get detailed OCR data with bounding boxes
            data = pytesseract.image_to_data(
                image,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )
            
            boxes = []
            n_boxes = len(data['level'])
            
            for i in range(n_boxes):
                # Only include text with reasonable confidence
                conf = int(data['conf'][i])
                if conf > 30:  # Confidence threshold
                    text = data['text'][i].strip()
                    if text:  # Only include non-empty text
                        boxes.append({
                            'text': text,
                            'x': int(data['left'][i]),
                            'y': int(data['top'][i]),
                            'width': int(data['width'][i]),
                            'height': int(data['height'][i]),
                            'confidence': conf / 100.0  # Convert to 0-1 scale
                        })
            
            return boxes
            
        except Exception as e:
            logger.error("Text box extraction failed", error=str(e))
            return []
    
    def _cleanup_temp_files(self, processed_path: str, original_path: str):
        """Clean up temporary processed image files."""
        try:
            # Only delete processed file if it's different from original
            if processed_path != original_path and os.path.exists(processed_path):
                os.remove(processed_path)
                logger.debug("Cleaned up temporary file", file_path=processed_path)
        except Exception as e:
            logger.warning("Failed to clean up temporary file", 
                         file_path=processed_path, error=str(e))
    
    def test_ocr_accuracy(self, test_images_dir: str) -> Dict[str, Any]:
        """
        Test OCR accuracy on a directory of test images.
        
        Args:
            test_images_dir: Directory containing test images with known amounts
            
        Returns:
            Dict containing accuracy metrics
        """
        try:
            if not os.path.exists(test_images_dir):
                logger.error("Test images directory not found", dir=test_images_dir)
                return {"error": "Test directory not found"}
            
            results = []
            total_images = 0
            successful_detections = 0
            accurate_detections = 0
            
            # Process each image in the test directory
            for filename in os.listdir(test_images_dir):
                if not any(filename.lower().endswith(ext) for ext in self.supported_formats):
                    continue
                
                image_path = os.path.join(test_images_dir, filename)
                total_images += 1
                
                # Extract expected amount from filename (e.g., "receipt_5000.jpg")
                expected_amount = self._extract_expected_amount_from_filename(filename)
                
                # Process image
                result = self.process_image(image_path)
                
                # Evaluate result
                detection_success = result.detected_amount is not None
                if detection_success:
                    successful_detections += 1
                
                accuracy = 0.0
                if expected_amount and result.detected_amount:
                    # Calculate accuracy (allowing 5% tolerance)
                    diff_percent = abs(result.detected_amount - expected_amount) / expected_amount
                    accuracy = max(0, 1 - diff_percent)
                    
                    if diff_percent <= 0.05:  # Within 5% tolerance
                        accurate_detections += 1
                
                results.append({
                    'filename': filename,
                    'expected_amount': expected_amount,
                    'detected_amount': result.detected_amount,
                    'confidence': result.confidence,
                    'accuracy': accuracy,
                    'processing_time': result.processing_time
                })
            
            # Calculate overall metrics
            detection_rate = successful_detections / total_images if total_images > 0 else 0
            accuracy_rate = accurate_detections / total_images if total_images > 0 else 0
            avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0
            avg_processing_time = sum(r['processing_time'] for r in results) / len(results) if results else 0
            
            metrics = {
                'total_images': total_images,
                'successful_detections': successful_detections,
                'accurate_detections': accurate_detections,
                'detection_rate': detection_rate,
                'accuracy_rate': accuracy_rate,
                'average_confidence': avg_confidence,
                'average_processing_time': avg_processing_time,
                'detailed_results': results
            }
            
            logger.info(
                "OCR accuracy test completed",
                total_images=total_images,
                detection_rate=detection_rate,
                accuracy_rate=accuracy_rate
            )
            
            return metrics
            
        except Exception as e:
            logger.error("OCR accuracy test failed", error=str(e))
            return {"error": str(e)}
    
    def _extract_expected_amount_from_filename(self, filename: str) -> Optional[float]:
        """Extract expected amount from test image filename."""
        try:
            # Look for patterns like "receipt_5000.jpg" or "5000_receipt.png"
            import re
            
            # Pattern to find numbers in filename
            numbers = re.findall(r'\d+', filename)
            
            # Find the largest number (likely the amount)
            if numbers:
                amounts = [float(num) for num in numbers]
                # Return the largest number that's in reasonable range
                valid_amounts = [amt for amt in amounts if 10 <= amt <= 10_000_000]
                if valid_amounts:
                    return max(valid_amounts)
            
            return None
            
        except Exception as e:
            logger.warning("Failed to extract expected amount from filename", 
                         filename=filename, error=str(e))
            return None
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about the OCR pipeline configuration."""
        return {
            'tesseract_version': pytesseract.get_tesseract_version(),
            'tesseract_config': self.tesseract_config,
            'supported_formats': self.supported_formats,
            'confidence_threshold': settings.ocr_confidence_threshold,
            'preprocessing_enabled': True,
            'amount_extraction_enabled': True,
            'receipt_analysis_enabled': True
        }