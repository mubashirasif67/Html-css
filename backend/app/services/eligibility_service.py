"""
Eligibility prediction service using trained ML model.

This module loads the pre-trained eligibility model and provides
inference capabilities for determining employee eligibility.
"""
import joblib
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class EligibilityService:
    """Service for predicting employee eligibility."""

    def __init__(self, model_path: str = "/app/ml/models/eligibility_model.joblib"):
        """Initialize the service with model path."""
        self.model_path = model_path
        self.model = None
        self.load_model()

    def load_model(self):
        """Load the trained model from disk."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("Eligibility model loaded successfully")
            else:
                logger.warning(f"Model not found at {self.model_path}. Using rule-based fallback.")
                self.model = None
        except Exception as e:
            logger.error(f"Error loading eligibility model: {e}")
            self.model = None

    def predict_eligibility(self, features: Dict) -> Tuple[float, str]:
        """Predict eligibility score and decision for an employee."""
        if self.model is None:
            # Fallback to rule-based system
            return self._rule_based_prediction(features)

        try:
            # Prepare features for model input
            feature_order = ['grade', 'family_size', 'income_estimate', 'previous_aid_count']
            feature_values = [features.get(key, 0) for key in feature_order]

            # Make prediction
            score = self.model.predict_proba([feature_values])[0][1]  # Probability of eligible

            # Determine decision based on threshold
            decision = "eligible" if score >= 0.5 else "ineligible"

            return score, decision

        except Exception as e:
            logger.error(f"Error predicting eligibility: {e}")
            return self._rule_based_prediction(features)

    def _rule_based_prediction(self, features: Dict) -> Tuple[float, str]:
        """Fallback rule-based eligibility prediction."""
        grade = features.get('grade', 10)
        family_size = features.get('family_size', 1)
        income_estimate = features.get('income_estimate', 50000)
        previous_aid_count = features.get('previous_aid_count', 0)

        # Simple scoring system
        base_score = 0.5

        # Lower grade (higher need) increases score
        grade_factor = max(0, (20 - grade) / 20) * 0.3
        base_score += grade_factor

        # Larger family size increases score
        family_factor = min(family_size / 10, 1) * 0.2
        base_score += family_factor

        # Lower income increases score
        income_factor = max(0, (100000 - income_estimate) / 100000) * 0.3
        base_score += income_factor

        # Previous aid decreases score slightly
        aid_factor = max(0, (5 - previous_aid_count) / 5) * 0.2
        base_score += aid_factor

        # Ensure score is between 0 and 1
        score = max(0, min(1, base_score))

        decision = "eligible" if score >= 0.5 else "ineligible"

        return score, decision

    def batch_predict(self, employees: List[Dict]) -> List[Tuple[float, str]]:
        """Predict eligibility for a batch of employees."""
        results = []
        for employee in employees:
            score, decision = self.predict_eligibility(employee)
            results.append((score, decision))
        return results


# Global service instance
eligibility_service = EligibilityService()