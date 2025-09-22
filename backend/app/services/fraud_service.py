"""
Fraud detection service using Isolation Forest.

This module loads the trained fraud detection model and provides
inference for identifying potentially fraudulent activities.
"""
import joblib
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class FraudService:
    """Service for detecting fraudulent activities."""

    def __init__(self, model_path: str = "/app/ml/models/fraud_model.joblib"):
        """Initialize the service with model path."""
        self.model_path = model_path
        self.model = None
        self.load_model()

    def load_model(self):
        """Load the trained model from disk."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info("Fraud detection model loaded successfully")
            else:
                logger.warning(f"Model not found at {self.model_path}. Using rule-based fallback.")
                self.model = None
        except Exception as e:
            logger.error(f"Error loading fraud model: {e}")
            self.model = None

    def predict_fraud(self, features: Dict) -> Tuple[float, bool]:
        """Predict fraud score and flag for a record."""
        if self.model is None:
            # Fallback to rule-based system
            return self._rule_based_prediction(features)

        try:
            # Prepare features for model input
            feature_order = ['amount', 'frequency', 'amount_variance', 'time_since_last']
            feature_values = [features.get(key, 0) for key in feature_order]

            # Make prediction (-1 for anomaly, 1 for normal)
            prediction = self.model.predict([feature_values])[0]
            score = self.model.decision_function([feature_values])[0]

            # Convert to fraud flag and score
            is_fraud = prediction == -1
            # Normalize score to 0-1 range
            fraud_score = 1 / (1 + np.exp(-score))  # Sigmoid function

            return fraud_score, is_fraud

        except Exception as e:
            logger.error(f"Error predicting fraud: {e}")
            return self._rule_based_prediction(features)

    def _rule_based_prediction(self, features: Dict) -> Tuple[float, bool]:
        """Fallback rule-based fraud detection."""
        amount = features.get('amount', 0)
        frequency = features.get('frequency', 1)
        amount_variance = features.get('amount_variance', 0)
        time_since_last = features.get('time_since_last', 30)

        # Simple scoring system
        fraud_score = 0.0

        # High amounts may be suspicious
        if amount > 50000:
            fraud_score += 0.3

        # Very high frequency may indicate fraud
        if frequency > 10:
            fraud_score += 0.4

        # High variance in amounts
        if amount_variance > 0.5:
            fraud_score += 0.2

        # Very recent activity after long gap
        if time_since_last < 1 and frequency > 5:
            fraud_score += 0.3

        # Normalize to 0-1
        fraud_score = min(1.0, fraud_score)

        is_fraud = fraud_score > 0.6

        return fraud_score, is_fraud

    def batch_predict(self, records: List[Dict]) -> List[Tuple[float, bool]]:
        """Predict fraud for a batch of records."""
        results = []
        for record in records:
            score, is_fraud = self.predict_fraud(record)
            results.append((score, is_fraud))
        return results


# Global service instance
fraud_service = FraudService()