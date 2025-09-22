"""
Tests for OCR service
"""

import pytest
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import os
from app.services.ocr_service import OCRService


@pytest.fixture
def ocr_service():
    """Create OCR service instance"""
    return OCRService()


@pytest.fixture
def sample_receipt_image():
    """Generate a sample receipt image for testing"""
    # Create a simple image with text
    img = Image.new('RGB', (400, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add receipt text
    text_lines = [
        "RECEIPT",
        "Date: 2024-01-15",
        "Item: Donation",
        "Amount: PKR 5,000",
        "Thank you!"
    ]
    
    y_position = 50
    for line in text_lines:
        draw.text((50, y_position), line, fill='black')
        y_position += 40
    
    # Save to temporary file
    temp_path = "/tmp/test_receipt.png"
    img.save(temp_path)
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.mark.asyncio
async def test_process_receipt(ocr_service, sample_receipt_image):
    """Test OCR receipt processing"""
    result = await ocr_service.process_receipt(sample_receipt_image)
    
    assert "detected_amount" in result
    assert "confidence" in result
    assert "currency" in result
    assert "raw_text" in result
    assert "processing_time" in result
    
    # Check if amount was detected (may vary based on OCR accuracy)
    if result["detected_amount"]:
        assert result["detected_amount"] > 0
        assert 0 <= result["confidence"] <= 1


def test_extract_amounts(ocr_service):
    """Test amount extraction from text"""
    test_texts = [
        ("Total Amount: Rs 1,000", [1000.0]),
        ("PKR 5,500.50", [5500.50]),
        ("Received ₨ 10,000", [10000.0]),
        ("Amount: 2500 rupees", [2500.0]),
    ]
    
    for text, expected in test_texts:
        amounts = ocr_service._extract_amounts(text)
        if expected:
            assert len(amounts) > 0
            assert amounts[0] in expected


def test_calculate_confidence(ocr_service):
    """Test confidence calculation"""
    # High confidence scenario
    amounts = [5000.0, 5000.0]
    text = "Receipt for PKR 5000 payment received"
    confidence = ocr_service._calculate_confidence(amounts, text)
    assert confidence > 0.5
    
    # Low confidence scenario
    amounts = []
    text = "Some random text"
    confidence = ocr_service._calculate_confidence(amounts, text)
    assert confidence == 0.0


def test_preprocess_image(ocr_service):
    """Test image preprocessing"""
    # Create a test image
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    processed = ocr_service._preprocess_image(img)
    
    # Check that preprocessing returns a valid image
    assert processed is not None
    assert len(processed.shape) == 2  # Should be grayscale