"""
Training script for eligibility prediction model.

This script trains a Random Forest classifier on synthetic employee data
to predict eligibility for aid distribution.
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Tuple

# Set random seed for reproducibility
np.random.seed(42)


def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load and preprocess training data."""
    # Load synthetic data
    data_path = "/app/ml/synthetic_data/employees.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)

    # Select features
    features = ['grade', 'family_size', 'income_estimate', 'previous_aid_count']
    target = 'is_eligible'

    X = df[features]
    y = df[target]

    return X, y


def preprocess_data(X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Preprocess data for training."""
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


def train_model(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    """Train the eligibility prediction model."""
    # Initialize model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        class_weight='balanced'  # Handle imbalanced data
    )

    # Train model
    model.fit(X_train, y_train)

    return model


def evaluate_model(model: RandomForestClassifier, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """Evaluate model performance."""
    # Make predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Calculate metrics
    accuracy = model.score(X_test, y_test)
    auc = roc_auc_score(y_test, y_pred_proba)

    # Generate classification report
    report = classification_report(y_test, y_pred, output_dict=True)

    # Create confusion matrix
    cm = confusion_matrix(y_test, y_pred)

    return {
        'accuracy': accuracy,
        'auc': auc,
        'classification_report': report,
        'confusion_matrix': cm,
        'predictions': y_pred,
        'probabilities': y_pred_proba
    }


def plot_results(evaluation: dict, model: RandomForestClassifier):
    """Plot evaluation results."""
    # Confusion matrix
    plt.figure(figsize=(8, 6))
    cm = evaluation['confusion_matrix']
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Ineligible', 'Eligible'],
                yticklabels=['Ineligible', 'Eligible'])
    plt.title('Confusion Matrix - Eligibility Prediction')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig('/app/ml/models/confusion_matrix.png')
    plt.close()

    # Feature importance
    plt.figure(figsize=(10, 6))
    features = ['grade', 'family_size', 'income_estimate', 'previous_aid_count']
    importances = model.feature_importances_
    plt.barh(features, importances)
    plt.title('Feature Importance')
    plt.xlabel('Importance')
    plt.savefig('/app/ml/models/feature_importance.png')
    plt.close()

    print("Evaluation plots saved to /app/ml/models/")


def train_and_save_model():
    """Main training function."""
    print("Loading data...")
    X, y = load_data()

    print(f"Dataset shape: {X.shape}")
    print(f"Target distribution: {y.value_counts().to_dict()}")

    print("Preprocessing data...")
    X_train, X_test, y_train, y_test, scaler = preprocess_data(X, y)

    print("Training model...")
    model = train_model(X_train, y_train)

    print("Evaluating model...")
    evaluation = evaluate_model(model, X_test, y_test)

    print(f"Accuracy: {evaluation['accuracy']".4f"}")
    print(f"AUC: {evaluation['auc']".4f"}")
    print("Classification Report:")
    print(evaluation['classification_report'])

    print("Generating plots...")
    plot_results(evaluation, model)

    # Save model and scaler
    os.makedirs('/app/ml/models', exist_ok=True)
    joblib.dump(model, '/app/ml/models/eligibility_model.joblib')
    joblib.dump(scaler, '/app/ml/models/eligibility_scaler.joblib')

    print("Model and scaler saved to /app/ml/models/")

    return model, evaluation


if __name__ == "__main__":
    train_and_save_model()