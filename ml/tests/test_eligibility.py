"""
Unit tests for eligibility prediction model.

Tests the model loading, prediction accuracy, and integration.
"""
import pytest
import numpy as np
import pandas as pd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from train_eligibility import load_data, preprocess_data, train_model, evaluate_model


def test_data_loading():
    """Test data loading and preprocessing."""
    X, y = load_data()

    assert X.shape[0] > 0, "Should have training samples"
    assert y.shape[0] > 0, "Should have target values"
    assert X.shape[0] == y.shape[0], "X and y should have same length"

    expected_features = ['grade', 'family_size', 'income_estimate', 'previous_aid_count']
    assert list(X.columns) == expected_features, "Should have correct features"


def test_data_preprocessing():
    """Test data preprocessing."""
    X, y = load_data()
    X_train, X_test, y_train, y_test, scaler = preprocess_data(X, y)

    assert X_train.shape[0] > 0, "Should have training data"
    assert X_test.shape[0] > 0, "Should have test data"
    assert y_train.shape[0] == X_train.shape[0], "Train data should match"
    assert y_test.shape[0] == X_test.shape[0], "Test data should match"

    # Check scaling
    assert np.mean(X_train) < 1e-10, "Training data should be scaled"
    assert np.std(X_train) - 1 < 1e-10, "Training data should have unit variance"


def test_model_training():
    """Test model training."""
    X, y = load_data()
    X_train, X_test, y_train, y_test, scaler = preprocess_data(X, y)

    model = train_model(X_train, y_train)

    assert model is not None, "Model should be trained"
    assert hasattr(model, 'predict'), "Model should have predict method"

    # Test prediction
    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)

    assert len(predictions) == len(y_test), "Predictions should match test set"
    assert probabilities.shape[0] == len(y_test), "Probabilities should match test set"
    assert probabilities.shape[1] == 2, "Should have 2 classes"


def test_model_evaluation():
    """Test model evaluation."""
    X, y = load_data()
    X_train, X_test, y_train, y_test, scaler = preprocess_data(X, y)

    model = train_model(X_train, y_train)
    evaluation = evaluate_model(model, X_test, y_test)

    required_keys = ['accuracy', 'auc', 'classification_report', 'confusion_matrix']
    for key in required_keys:
        assert key in evaluation, f"Evaluation should contain {key}"

    assert 0 <= evaluation['accuracy'] <= 1, "Accuracy should be between 0 and 1"
    assert 0 <= evaluation['auc'] <= 1, "AUC should be between 0 and 1"


def test_model_accuracy():
    """Test that model achieves reasonable accuracy on synthetic data."""
    X, y = load_data()
    X_train, X_test, y_train, y_test, scaler = preprocess_data(X, y)

    model = train_model(X_train, y_train)
    evaluation = evaluate_model(model, X_test, y_test)

    # Model should achieve at least 70% accuracy on synthetic data
    assert evaluation['accuracy'] >= 0.7, f"Model accuracy too low: {evaluation['accuracy']}"


if __name__ == "__main__":
    pytest.main([__file__])