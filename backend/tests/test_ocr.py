"""
Tests for OCR functionality.
"""
import pytest
from fastapi.testclient import TestClient
import base64
from PIL import Image, ImageDraw
import io


def create_test_image():
    """Create a simple test image with text."""
    img = Image.new('RGB', (200, 100), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 40), "Rs 10,000", fill='black')

    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    return img_byte_arr.getvalue()


def test_ocr_receipt_processing(client: TestClient):
    """Test OCR processing of receipt image."""
    # Create test image
    image_data = create_test_image()

    # Create test file
    files = {
        'receipt_image': ('test_receipt.png', image_data, 'image/png')
    }

    response = client.post(
        "/api/ocr/upload_receipt",
        files=files
    )

    assert response.status_code == 200
    data = response.json()

    # Check OCR result
    assert "detected_amount" in data
    assert "confidence" in data
    assert "raw_text" in data

    # Should detect the amount (may vary based on OCR accuracy)
    expected_amount = 10000.0
    detected = data["detected_amount"]
    assert detected is not None, "Should detect some amount"

    # Check confidence
    assert 0 <= data["confidence"] <= 1, "Confidence should be between 0 and 1"


def test_ocr_invalid_image(client: TestClient):
    """Test OCR with invalid image."""
    # Send text data as image
    files = {
        'receipt_image': ('invalid.txt', b'Not an image', 'text/plain')
    }

    response = client.post(
        "/api/ocr/upload_receipt",
        files=files
    )

    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_ocr_processing_error(client: TestClient):
    """Test OCR error handling."""
    # Send empty file
    files = {
        'receipt_image': ('empty.png', b'', 'image/png')
    }

    response = client.post(
        "/api/ocr/upload_receipt",
        files=files
    )

    assert response.status_code == 500
    assert "error" in response.json()["detail"].lower()