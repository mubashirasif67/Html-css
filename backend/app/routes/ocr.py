"""
OCR routes for receipt processing.

Provides endpoints for uploading and processing receipt images.
"""
from fastapi import APIRouter, File, UploadFile, HTTPException, status
from ..services.ocr_service import ocr_service
from ..schemas import OCRResult

router = APIRouter()


@router.post("/upload_receipt", response_model=OCRResult)
async def upload_receipt(receipt_image: UploadFile = File(...)):
    """Upload and process receipt image with OCR."""
    if not receipt_image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read image bytes
        image_bytes = await receipt_image.read()

        # Process with OCR
        result = ocr_service.process_receipt(image_bytes)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")