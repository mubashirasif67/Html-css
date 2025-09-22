"""
Tests for ML services.
"""
import pytest
import numpy as np
from app.services.eligibility_service import eligibility_service
from app.services.fraud_service import fraud_service


def test_eligibility_service_prediction():
    """Test eligibility prediction service."""
    # Test data
    test_features = {
        'grade': 5,
        'family_size': 4,
        'income_estimate': 25000,
        'previous_aid_count': 2
    }

    score, decision = eligibility_service.predict_eligibility(test_features)

    assert 0 <= score <= 1, "Score should be between 0 and 1"
    assert decision in ['eligible', 'ineligible'], "Decision should be valid"

    # Test that lower grade generally increases eligibility
    low_grade_features = test_features.copy()
    low_grade_features['grade'] = 1
    low_grade_score, _ = eligibility_service.predict_eligibility(low_grade_features)

    assert low_grade_score > score, "Lower grade should have higher eligibility score"


def test_fraud_service_prediction():
    """Test fraud detection service."""
    # Test data
    test_features = {
        'amount': 10000,
        'frequency': 5,
        'amount_variance': 0.1,
        'time_since_last': 30
    }

    score, is_fraud = fraud_service.predict_fraud(test_features)

    assert 0 <= score <= 1, "Fraud score should be between 0 and 1"
    assert isinstance(is_fraud, bool), "Fraud flag should be boolean"

    # Test that suspicious patterns increase fraud score
    suspicious_features = test_features.copy()
    suspicious_features['amount'] = 99999  # Unusual amount
    suspicious_features['frequency'] = 1   # Very low frequency
    suspicious_score, _ = fraud_service.predict_fraud(suspicious_features)

    assert suspicious_score > score, "Suspicious patterns should increase fraud score"


def test_batch_predictions():
    """Test batch prediction capabilities."""
    # Test eligibility batch
    test_employees = [
        {'grade': 5, 'family_size': 4, 'income_estimate': 25000, 'previous_aid_count': 2},
        {'grade': 1, 'family_size': 6, 'income_estimate': 15000, 'previous_aid_count': 0},
        {'grade': 15, 'family_size': 2, 'income_estimate': 80000, 'previous_aid_count': 5}
    ]

    eligibility_results = eligibility_service.batch_predict(test_employees)

    assert len(eligibility_results) == 3, "Should return results for all employees"
    for score, decision in eligibility_results:
        assert 0 <= score <= 1, "Each score should be between 0 and 1"
        assert decision in ['eligible', 'ineligible'], "Each decision should be valid"

    # Test fraud batch
    test_records = [
        {'amount': 10000, 'frequency': 5, 'amount_variance': 0.1, 'time_since_last': 30},
        {'amount': 99999, 'frequency': 1, 'amount_variance': 0.9, 'time_since_last': 0},
        {'amount': 5000, 'frequency': 10, 'amount_variance': 0.05, 'time_since_last': 60}
    ]

    fraud_results = fraud_service.batch_predict(test_records)

    assert len(fraud_results) == 3, "Should return results for all records"
    for score, is_fraud in fraud_results:
        assert 0 <= score <= 1, "Each fraud score should be between 0 and 1"
        assert isinstance(is_fraud, bool), "Each fraud flag should be boolean"


def test_model_fallback():
    """Test fallback behavior when models are not available."""
    # Temporarily set model to None to test fallback
    original_model = eligibility_service.model
    eligibility_service.model = None

    try:
        test_features = {
            'grade': 5,
            'family_size': 4,
            'income_estimate': 25000,
            'previous_aid_count': 2
        }

        score, decision = eligibility_service.predict_eligibility(test_features)

        assert 0 <= score <= 1, "Fallback should still return valid score"
        assert decision in ['eligible', 'ineligible'], "Fallback should return valid decision"
    finally:
        # Restore original model
        eligibility_service.model = original_model