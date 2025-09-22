"""
Image preprocessing for OCR in the Blessings Donation System.

This module provides image preprocessing functions to improve OCR accuracy
including noise reduction, deskewing, and contrast enhancement.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import structlog
from PIL import Image, ImageEnhance

logger = structlog.get_logger(__name__)


class ImagePreprocessor:
    """Image preprocessing pipeline for OCR optimization."""
    
    def __init__(self):
        self.debug_mode = False
    
    def preprocess_image(self, image_path: str, debug: bool = False) -> str:
        """
        Apply full preprocessing pipeline to an image.
        
        Args:
            image_path: Path to input image
            debug: Whether to save debug images
            
        Returns:
            str: Path to preprocessed image
        """
        try:
            logger.info("Starting image preprocessing", image_path=image_path)
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image from {image_path}")
            
            # Apply preprocessing steps
            processed = self._apply_preprocessing_pipeline(image)
            
            # Save preprocessed image
            output_path = image_path.replace('.', '_processed.')
            cv2.imwrite(output_path, processed)
            
            logger.info("Image preprocessing completed", output_path=output_path)
            return output_path
            
        except Exception as e:
            logger.error("Image preprocessing failed", error=str(e))
            # Return original path if preprocessing fails
            return image_path
    
    def _apply_preprocessing_pipeline(self, image: np.ndarray) -> np.ndarray:
        """Apply the complete preprocessing pipeline."""
        # Step 1: Convert to grayscale
        gray = self._convert_to_grayscale(image)
        
        # Step 2: Denoise
        denoised = self._denoise_image(gray)
        
        # Step 3: Enhance contrast
        enhanced = self._enhance_contrast(denoised)
        
        # Step 4: Deskew
        deskewed = self._deskew_image(enhanced)
        
        # Step 5: Binarize (threshold)
        binary = self._binarize_image(deskewed)
        
        # Step 6: Morphological operations
        morphed = self._apply_morphology(binary)
        
        # Step 7: Remove noise
        cleaned = self._remove_small_noise(morphed)
        
        return cleaned
    
    def _convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert image to grayscale."""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
    
    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Remove noise from the image."""
        # Use Non-local Means Denoising
        return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast using CLAHE."""
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(image)
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Correct skew in the image."""
        try:
            # Find skew angle using Hough Transform
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                # Calculate average angle
                angles = []
                for rho, theta in lines[:20]:  # Use first 20 lines
                    angle = np.degrees(theta) - 90
                    if abs(angle) < 45:  # Filter out vertical lines
                        angles.append(angle)
                
                if angles:
                    skew_angle = np.median(angles)
                    
                    # Rotate image to correct skew
                    if abs(skew_angle) > 0.5:  # Only correct if skew is significant
                        height, width = image.shape
                        center = (width // 2, height // 2)
                        rotation_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
                        
                        # Calculate new image dimensions
                        cos = np.abs(rotation_matrix[0, 0])
                        sin = np.abs(rotation_matrix[0, 1])
                        new_width = int((height * sin) + (width * cos))
                        new_height = int((height * cos) + (width * sin))
                        
                        # Adjust rotation matrix for new dimensions
                        rotation_matrix[0, 2] += (new_width / 2) - center[0]
                        rotation_matrix[1, 2] += (new_height / 2) - center[1]
                        
                        return cv2.warpAffine(image, rotation_matrix, (new_width, new_height), 
                                            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            return image
            
        except Exception as e:
            logger.warning("Deskewing failed, using original image", error=str(e))
            return image
    
    def _binarize_image(self, image: np.ndarray) -> np.ndarray:
        """Convert image to binary using adaptive thresholding."""
        # Try Otsu's thresholding first
        _, otsu = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Also try adaptive thresholding
        adaptive = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Choose the better result based on image statistics
        otsu_mean = np.mean(otsu)
        adaptive_mean = np.mean(adaptive)
        
        # Use the result that gives better contrast (closer to 127.5 mean)
        if abs(otsu_mean - 127.5) < abs(adaptive_mean - 127.5):
            return otsu
        else:
            return adaptive
    
    def _apply_morphology(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean up the binary image."""
        # Define kernels
        kernel_small = np.ones((2, 2), np.uint8)
        kernel_medium = np.ones((3, 3), np.uint8)
        
        # Remove small noise with opening
        opened = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel_small)
        
        # Fill small gaps with closing
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_medium)
        
        return closed
    
    def _remove_small_noise(self, image: np.ndarray) -> np.ndarray:
        """Remove small connected components that are likely noise."""
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(image, connectivity=8)
        
        # Create output image
        cleaned = np.zeros_like(image)
        
        # Keep components that are large enough
        min_area = 50  # Minimum area for a component to be kept
        
        for i in range(1, num_labels):  # Skip background (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_area:
                cleaned[labels == i] = 255
        
        return cleaned
    
    def crop_text_regions(self, image: np.ndarray) -> list:
        """
        Detect and crop text regions from the image.
        
        Args:
            image: Preprocessed binary image
            
        Returns:
            list: List of cropped text region images
        """
        try:
            # Find contours
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            text_regions = []
            
            # Filter contours by size and aspect ratio
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # Filter by area and dimensions
                if area > 100 and w > 20 and h > 10:
                    # Extract region
                    region = image[y:y+h, x:x+w]
                    text_regions.append({
                        'image': region,
                        'bbox': (x, y, w, h),
                        'area': area
                    })
            
            # Sort by area (largest first)
            text_regions.sort(key=lambda x: x['area'], reverse=True)
            
            return text_regions
            
        except Exception as e:
            logger.error("Text region cropping failed", error=str(e))
            return []
    
    def enhance_for_currency_detection(self, image: np.ndarray) -> np.ndarray:
        """
        Apply specific enhancements for currency amount detection.
        
        Args:
            image: Input image
            
        Returns:
            np.ndarray: Enhanced image optimized for currency detection
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Enhance contrast specifically for numbers
            clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
            
            # Use adaptive thresholding for better number recognition
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4
            )
            
            # Morphological operations to connect broken characters
            kernel = np.ones((2, 1), np.uint8)
            connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return connected
            
        except Exception as e:
            logger.error("Currency enhancement failed", error=str(e))
            return image
    
    def resize_for_ocr(self, image: np.ndarray, target_height: int = 64) -> np.ndarray:
        """
        Resize image to optimal size for OCR.
        
        Args:
            image: Input image
            target_height: Target height in pixels
            
        Returns:
            np.ndarray: Resized image
        """
        try:
            height, width = image.shape[:2]
            
            # Calculate scaling factor
            scale = target_height / height
            
            # Don't upscale too much
            if scale > 3.0:
                scale = 3.0
            
            # Don't downscale too much
            if scale < 0.5:
                scale = 0.5
            
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Resize using high-quality interpolation
            if scale > 1.0:
                # Upscaling - use cubic interpolation
                resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            else:
                # Downscaling - use area interpolation
                resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            return resized
            
        except Exception as e:
            logger.error("Image resizing failed", error=str(e))
            return image
    
    def detect_orientation(self, image: np.ndarray) -> int:
        """
        Detect image orientation and return rotation angle.
        
        Args:
            image: Input image
            
        Returns:
            int: Rotation angle (0, 90, 180, or 270)
        """
        try:
            # This is a simplified orientation detection
            # In a production system, you might use more sophisticated methods
            
            height, width = image.shape[:2]
            
            # If width >> height, might be rotated 90 degrees
            if width > height * 2:
                return 90
            
            # For now, assume correct orientation
            return 0
            
        except Exception as e:
            logger.error("Orientation detection failed", error=str(e))
            return 0