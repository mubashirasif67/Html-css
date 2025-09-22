"""
Feedback API endpoint with sentiment analysis
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging

from app.database import get_db
from app.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackCreate(BaseModel):
    """Schema for feedback creation"""
    category: str = Field(..., max_length=50)
    subject: str = Field(..., max_length=200)
    message: str = Field(..., min_length=10, max_length=2000)
    rating: Optional[int] = Field(None, ge=1, le=5)


class FeedbackResponse(BaseModel):
    """Schema for feedback response"""
    id: int
    sentiment: str
    sentiment_score: float
    category: str
    created_at: datetime
    message: str = "Thank you for your feedback!"


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = None
):
    """
    Submit feedback and get sentiment analysis
    
    Request Body:
    ```json
    {
        "category": "service",
        "subject": "Distribution Process",
        "message": "The distribution was well organized and efficient.",
        "rating": 5
    }
    ```
    
    Returns sentiment analysis result
    """
    try:
        # Simple sentiment analysis (in production, use a proper ML model)
        sentiment_score = 0.5  # Neutral by default
        
        # Basic keyword-based sentiment analysis
        positive_keywords = ["good", "great", "excellent", "amazing", "helpful", "efficient", "thank"]
        negative_keywords = ["bad", "poor", "terrible", "slow", "inefficient", "problem", "issue"]
        
        message_lower = feedback_data.message.lower()
        
        positive_count = sum(1 for word in positive_keywords if word in message_lower)
        negative_count = sum(1 for word in negative_keywords if word in message_lower)
        
        # Calculate sentiment score
        if positive_count + negative_count > 0:
            sentiment_score = positive_count / (positive_count + negative_count)
        
        # Consider rating if provided
        if feedback_data.rating:
            rating_score = (feedback_data.rating - 1) / 4  # Normalize to 0-1
            sentiment_score = (sentiment_score + rating_score) / 2
        
        # Determine sentiment category
        if sentiment_score >= 0.7:
            sentiment = "positive"
        elif sentiment_score <= 0.3:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Store feedback (simplified - in production, create a Feedback model)
        logger.info(f"Feedback received: {sentiment} ({sentiment_score:.2f}) - {feedback_data.subject}")
        
        return FeedbackResponse(
            id=1,  # In production, this would be the actual DB ID
            sentiment=sentiment,
            sentiment_score=round(sentiment_score, 2),
            category=feedback_data.category,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing feedback"
        )