"""
OCR service using pytesseract with OpenCV preprocessing.

This module handles image preprocessing, text extraction, and
amount detection from receipt images using regex patterns.
"""
import cv2
import numpy as np
import pytesseract
import re
from PIL import Image
import io
from typing import Optional, Tuple, List, Dict
from ..schemas import OCRResult
import logging

logger = logging.getLogger(__name__)


class OCRService:
    """Service for processing receipt images with OCR."""

    # Currency patterns for amount detection
    CURRENCY_PATTERNS = [
        r'Rs\.?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'PKR\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'₨\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:Rs|PKR|₨)',
    ]

    @staticmethod
    def preprocess_image(image_bytes: bytes) -> np.ndarray:
        """Preprocess image for better OCR accuracy."""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Could not decode image")

            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Morphological operations to remove noise
            kernel = np.ones((2, 2), np.uint8)
            morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            # Deskew image (simple rotation correction)
            coords = np.column_stack(np.where(morph > 0))
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            (h, w) = morph.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(morph, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

            # Resize for better OCR
            height, width = deskewed.shape
            if height < 500:
                scale_factor = 500 / height
                new_width = int(width * scale_factor)
                deskewed = cv2.resize(deskewed, (new_width, 500))

            return deskewed

        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            # Fallback: convert bytes to grayscale PIL image
            pil_img = Image.open(io.BytesIO(image_bytes)).convert('L')
            return np.array(pil_img)

    @staticmethod
    def extract_amount(text: str) -> Tuple[Optional[float], float]:
        """Extract monetary amount from OCR text using regex."""
        max_confidence = 0.0
        detected_amount = None

        for pattern in OCRService.CURRENCY_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean the amount string
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                    confidence = 0.9  # High confidence for matched patterns

                    if amount > detected_amount or detected_amount is None:
                        detected_amount = amount
                        max_confidence = confidence

                except ValueError:
                    continue

        # If no pattern matched, try to find any number that looks like currency
        if detected_amount is None:
            number_matches = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b', text)
            for match in number_matches:
                try:
                    amount = float(match.replace(',', ''))
                    if 10 <= amount <= 1000000:  # Reasonable range for donations
                        confidence = 0.5
                        if confidence > max_confidence:
                            detected_amount = amount
                            max_confidence = confidence
                except ValueError:
                    continue

        return detected_amount, max_confidence

    @staticmethod
    def get_bounding_boxes(image: np.ndarray, text: str) -> List[Dict]:
        """Get bounding boxes for detected text regions."""
        boxes = []
        try:
            # Get detailed OCR data with bounding boxes
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            for i, confidence in enumerate(data['conf']):
                if int(confidence) > 30:  # Only confident detections
                    box = {
                        'text': data['text'][i],
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'confidence': int(confidence)
                    }
                    boxes.append(box)
        except Exception as e:
            logger.error(f"Error getting bounding boxes: {e}")

        return boxes

    def process_receipt(self, image_bytes: bytes) -> OCRResult:
        """Main method to process receipt image and extract amount."""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_bytes)

            # Extract text using pytesseract
            raw_text = pytesseract.image_to_string(processed_img)

            # Extract amount and confidence
            detected_amount, confidence = self.extract_amount(raw_text)

            # Get bounding boxes
            boxes = self.get_bounding_boxes(processed_img, raw_text)

            return OCRResult(
                detected_amount=detected_amount,
                currency="PKR",
                confidence=confidence,
                raw_text=raw_text,
                boxes=boxes if boxes else None
            )

        except Exception as e:
            logger.error(f"Error processing receipt: {e}")
            # Return low confidence result on error
            return OCRResult(
                detected_amount=None,
                currency="PKR",
                confidence=0.0,
                raw_text="Error processing image",
                boxes=None
            )


# Global OCR service instance
ocr_service = OCRService()