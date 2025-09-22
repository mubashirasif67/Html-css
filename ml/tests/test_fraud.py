"""
Unit tests for fraud detection model.

Tests the fraud detection model loading, prediction, and performance.
"""
import pytest
import numpy as np
import pandas as pd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from train_fraud import load_fraud_data, train_fraud_model, evaluate_fraud_model


def test_fraud_data_loading():
    """Test fraud data loading."""
    X, y = load_fraud_data()

    assert X.shape[0] > 0, "Should have training samples"
    assert y.shape[0] > 0, "Should have target values"
    assert X.shape[0] == y.shape[0], "X and y should have same length"

    expected_features = ['amount', 'frequency', 'amount_variance', 'time_since_last']
    assert list(X.columns) == expected_features, "Should have correct features"


def test_fraud_model_training():
    """Test fraud model training."""
    X, y = load_fraud_data()

    model = train_fraud_model(X)

    assert model is not None, "Model should be trained"
    assert hasattr(model, 'predict'), "Model should have predict method"

    # Test prediction
    predictions = model.predict(X)
    scores = model.decision_function(X)

    assert len(predictions) == len(X), "Predictions should match data"
    assert len(scores) == len(X), "Scores should match data"

    # Check that predictions are either -1 or 1
    assert all(pred in [-1, 1] for pred in predictions), "Predictions should be -1 or 1"


def test_fraud_model_evaluation():
    """Test fraud model evaluation."""
    X, y = load_fraud_data()

    model = train_fraud_model(X)
    evaluation = evaluate_fraud_model(model, X, y)

    required_keys = ['confusion_matrix', 'classification_report', 'predictions', 'anomaly_scores']
    for key in required_keys:
        assert key in evaluation, f"Evaluation should contain {key}"

    # Check shapes
    assert len(evaluation['predictions']) == len(X), "Predictions should match data"
    assert len(evaluation['anomaly_scores']) == len(X), "Scores should match data"


def test_fraud_detection():
    """Test that fraud detection identifies anomalies."""
    X, y = load_fraud_data()

    model = train_fraud_model(X)
    evaluation = evaluate_fraud_model(model, X, y)

    predictions = evaluation['predictions']

    # Should detect some anomalies
    unique_predictions = set(predictions)
    assert -1 in unique_predictions, "Should detect at least some anomalies"

    # Calculate detection rate
    fraud_detected = np.sum(predictions == -1)
    total_samples = len(predictions)
    detection_rate = fraud_detected / total_samples

    # Should detect fraud at reasonable rate (contamination parameter)
    expected_rate = 0.2  # From contamination parameter
    assert 0.1 <= detection_rate <= 0.3, f"Detection rate should be reasonable: {detection_rate}"


if __name__ == "__main__":
    pytest.main([__file__])