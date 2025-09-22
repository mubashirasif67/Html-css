"""
Feedback routes.

Handles user feedback collection and sentiment analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Feedback, User
from ..schemas import FeedbackCreate, FeedbackResponse
from ..dependencies import get_current_user
from textblob import TextBlob

router = APIRouter()


@router.post("/", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    feedback_data: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit user feedback."""
    # Analyze sentiment
    sentiment = "neutral"
    try:
        blob = TextBlob(feedback_data.feedback_text)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
    except Exception:
        # Fallback to neutral if analysis fails
        sentiment = "neutral"

    # Create feedback
    new_feedback = Feedback(
        user_id=current_user.id,
        feedback_text=feedback_data.feedback_text,
        sentiment=sentiment
    )

    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    return FeedbackResponse.model_validate(new_feedback)