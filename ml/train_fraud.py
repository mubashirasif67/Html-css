"""
Training script for fraud detection model.

This script trains an Isolation Forest model on synthetic data
to detect anomalous donation patterns.
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Tuple

np.random.seed(42)


def load_fraud_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load fraud detection data."""
    data_path = "/app/ml/synthetic_data/fraud.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)

    # Select features
    features = ['amount', 'frequency', 'amount_variance', 'time_since_last']
    target = 'is_fraud'

    X = df[features]
    y = df[target]

    return X, y


def train_fraud_model(X: pd.DataFrame) -> IsolationForest:
    """Train the fraud detection model."""
    # Initialize Isolation Forest
    model = IsolationForest(
        n_estimators=100,
        max_samples='auto',
        contamination=0.2,  # Expected fraud rate
        random_state=42
    )

    # Train model
    model.fit(X)

    return model


def evaluate_fraud_model(model: IsolationForest, X: pd.DataFrame, y: pd.Series) -> dict:
    """Evaluate fraud detection model."""
    # Make predictions (-1 for anomaly/fraud, 1 for normal)
    predictions = model.predict(X)
    scores = model.decision_function(X)

    # Convert predictions to binary (fraud/not fraud)
    y_pred = (predictions == -1).astype(int)
    y_true = y.astype(int)

    # Calculate metrics
    cm = confusion_matrix(y_true, y_pred)
    report = classification_report(y_true, y_pred, output_dict=True)

    # Calculate anomaly scores
    anomaly_scores = -scores  # Higher scores indicate more anomalous

    return {
        'confusion_matrix': cm,
        'classification_report': report,
        'predictions': predictions,
        'anomaly_scores': anomaly_scores,
        'true_labels': y_true
    }


def plot_fraud_results(evaluation: dict):
    """Plot fraud detection results."""
    # Confusion matrix
    plt.figure(figsize=(8, 6))
    cm = evaluation['confusion_matrix']
    sns.heatmap(cm, annot=True, fmt='d', cmap='Reds',
                xticklabels=['Normal', 'Fraud'],
                yticklabels=['Normal', 'Fraud'])
    plt.title('Confusion Matrix - Fraud Detection')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig('/app/ml/models/fraud_confusion_matrix.png')
    plt.close()

    # Anomaly score distribution
    plt.figure(figsize=(10, 6))
    scores = evaluation['anomaly_scores']
    labels = evaluation['true_labels']

    plt.hist(scores[labels == 0], bins=50, alpha=0.7, label='Normal', color='blue')
    plt.hist(scores[labels == 1], bins=50, alpha=0.7, label='Fraud', color='red')
    plt.title('Anomaly Score Distribution')
    plt.xlabel('Anomaly Score')
    plt.ylabel('Frequency')
    plt.legend()
    plt.savefig('/app/ml/models/anomaly_scores.png')
    plt.close()

    print("Fraud detection plots saved to /app/ml/models/")


def train_and_save_model():
    """Main training function."""
    print("Loading fraud data...")
    X, y = load_fraud_data()

    print(f"Dataset shape: {X.shape}")
    print(f"Target distribution: {y.value_counts().to_dict()}")

    print("Training fraud detection model...")
    model = train_fraud_model(X)

    print("Evaluating model...")
    evaluation = evaluate_fraud_model(model, X, y)

    print("Confusion Matrix:")
    print(evaluation['confusion_matrix'])
    print("Classification Report:")
    print(evaluation['classification_report'])

    print("Generating plots...")
    plot_fraud_results(evaluation)

    # Save model
    os.makedirs('/app/ml/models', exist_ok=True)
    joblib.dump(model, '/app/ml/models/fraud_model.joblib')

    print("Fraud model saved to /app/ml/models/")

    return model, evaluation


if __name__ == "__main__":
    train_and_save_model()