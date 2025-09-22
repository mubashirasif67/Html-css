#!/usr/bin/env python
"""
Train fraud detection model using Isolation Forest
This script generates synthetic data and trains an anomaly detection model
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_synthetic_fraud_data(n_samples=5000):
    """
    Generate synthetic data for fraud detection
    
    Features vary by context (donations vs beneficiaries)
    We'll create mixed scenarios with normal and anomalous patterns
    """
    logger.info(f"Generating {n_samples} synthetic fraud detection samples...")
    
    data = []
    
    # Generate normal patterns (90%)
    n_normal = int(n_samples * 0.9)
    n_fraud = n_samples - n_normal
    
    # Normal donation patterns
    for i in range(n_normal // 2):
        data.append({
            'amount_normalized': np.random.beta(2, 5),  # Most donations are small-medium
            'frequency': np.random.poisson(2) / 10.0,  # Low frequency
            'time_anomaly': 0.0,  # Normal timing
            'anonymous_flag': np.random.choice([0.0, 1.0], p=[0.9, 0.1]),  # Mostly not anonymous
            'grade_normalized': np.random.beta(5, 3),  # Middle grades
            'family_size_norm': np.random.beta(4, 4),  # Normal family sizes
            'aid_count_norm': np.random.beta(2, 8),  # Few previous aids
            'duplicate_flag': 0.0,  # No duplication
            'is_fraud': 0
        })
    
    # Normal beneficiary patterns
    for i in range(n_normal // 2):
        data.append({
            'amount_normalized': 0.0,  # Not applicable for beneficiaries
            'frequency': 0.0,
            'time_anomaly': 0.0,
            'anonymous_flag': 0.0,
            'grade_normalized': np.random.beta(3, 5),  # Lower-middle grades
            'family_size_norm': np.random.beta(4, 3),  # Normal to large families
            'aid_count_norm': np.random.beta(2, 6),  # Some previous aid
            'duplicate_flag': 0.0,
            'is_fraud': 0
        })
    
    # Fraudulent patterns - Donation fraud
    for i in range(n_fraud // 2):
        fraud_type = np.random.choice(['high_amount', 'high_frequency', 'suspicious_pattern'])
        
        if fraud_type == 'high_amount':
            # Unusually high donation amounts
            data.append({
                'amount_normalized': np.random.uniform(0.8, 1.0),  # Very high amounts
                'frequency': np.random.uniform(0.5, 1.0),  # High frequency
                'time_anomaly': np.random.choice([0.0, 1.0], p=[0.3, 0.7]),  # Often at odd times
                'anonymous_flag': np.random.choice([0.0, 1.0], p=[0.2, 0.8]),  # Often anonymous
                'grade_normalized': np.random.uniform(0, 1),
                'family_size_norm': 0.0,
                'aid_count_norm': 0.0,
                'duplicate_flag': 0.0,
                'is_fraud': 1
            })
        elif fraud_type == 'high_frequency':
            # Too many donations in short time
            data.append({
                'amount_normalized': np.random.uniform(0.2, 0.6),
                'frequency': np.random.uniform(0.7, 1.0),  # Very high frequency
                'time_anomaly': np.random.uniform(0.5, 1.0),  # Unusual timing
                'anonymous_flag': np.random.choice([0.0, 1.0]),
                'grade_normalized': np.random.uniform(0, 1),
                'family_size_norm': 0.0,
                'aid_count_norm': 0.0,
                'duplicate_flag': np.random.choice([0.0, 1.0], p=[0.7, 0.3]),
                'is_fraud': 1
            })
        else:  # suspicious_pattern
            # Mixed suspicious patterns
            data.append({
                'amount_normalized': np.random.uniform(0.4, 0.9),
                'frequency': np.random.uniform(0.3, 0.8),
                'time_anomaly': 1.0,  # Always at odd times
                'anonymous_flag': 1.0,  # Always anonymous
                'grade_normalized': np.random.uniform(0, 1),
                'family_size_norm': np.random.uniform(0, 0.2),
                'aid_count_norm': np.random.uniform(0, 0.3),
                'duplicate_flag': np.random.choice([0.0, 1.0], p=[0.5, 0.5]),
                'is_fraud': 1
            })
    
    # Fraudulent patterns - Beneficiary fraud
    for i in range(n_fraud // 2):
        fraud_type = np.random.choice(['duplicate_family', 'excessive_aid', 'data_mismatch'])
        
        if fraud_type == 'duplicate_family':
            # Multiple registrations from same family
            data.append({
                'amount_normalized': 0.0,
                'frequency': 0.0,
                'time_anomaly': 0.0,
                'anonymous_flag': 0.0,
                'grade_normalized': np.random.uniform(0.4, 0.8),
                'family_size_norm': np.random.uniform(0.6, 1.0),  # Large family claims
                'aid_count_norm': np.random.uniform(0.3, 0.7),
                'duplicate_flag': 1.0,  # Duplicate registration
                'is_fraud': 1
            })
        elif fraud_type == 'excessive_aid':
            # Too much aid received
            data.append({
                'amount_normalized': 0.0,
                'frequency': 0.0,
                'time_anomaly': 0.0,
                'anonymous_flag': 0.0,
                'grade_normalized': np.random.uniform(0.5, 0.9),  # Higher grades
                'family_size_norm': np.random.uniform(0.1, 0.4),  # Small family
                'aid_count_norm': np.random.uniform(0.7, 1.0),  # Many previous aids
                'duplicate_flag': np.random.choice([0.0, 1.0], p=[0.6, 0.4]),
                'is_fraud': 1
            })
        else:  # data_mismatch
            # Inconsistent data patterns
            data.append({
                'amount_normalized': np.random.uniform(0, 0.3),
                'frequency': np.random.uniform(0, 0.3),
                'time_anomaly': np.random.uniform(0.5, 1.0),
                'anonymous_flag': np.random.choice([0.0, 1.0]),
                'grade_normalized': np.random.uniform(0.7, 1.0),  # High grade
                'family_size_norm': np.random.uniform(0.7, 1.0),  # Large family claim
                'aid_count_norm': np.random.uniform(0.5, 1.0),  # High aid count
                'duplicate_flag': np.random.choice([0.0, 1.0], p=[0.3, 0.7]),
                'is_fraud': 1
            })
    
    df = pd.DataFrame(data)
    
    # Shuffle data
    df = df.sample(frac=1).reset_index(drop=True)
    
    # Log class distribution
    class_dist = df['is_fraud'].value_counts()
    logger.info(f"Class distribution: Normal={class_dist.get(0, 0)}, Fraud={class_dist.get(1, 0)}")
    
    return df


def prepare_features(df):
    """
    Select and prepare features for training
    We'll use a subset of features that are most relevant
    """
    # Select key features for anomaly detection
    feature_cols = [
        'amount_normalized',
        'frequency', 
        'time_anomaly',
        'duplicate_flag'
    ]
    
    X = df[feature_cols].values
    y = df['is_fraud'].values
    
    return X, y, feature_cols


def train_fraud_model(X, y):
    """
    Train Isolation Forest for anomaly detection
    """
    logger.info("Training fraud detection model...")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train Isolation Forest
    # Note: IsolationForest is unsupervised, so we train on normal data primarily
    # But we'll use all data to capture patterns
    model = IsolationForest(
        n_estimators=100,
        max_samples='auto',
        contamination=0.1,  # Expected proportion of outliers
        random_state=42,
        warm_start=False
    )
    
    # Fit the model
    model.fit(X_train)
    
    # Predict on test set
    y_pred = model.predict(X_test)
    # Convert to binary (1 for normal, -1 for anomaly -> 0 for normal, 1 for fraud)
    y_pred_binary = (y_pred == -1).astype(int)
    
    # Calculate scores
    scores = model.decision_function(X_test)
    # Convert to probability-like scores
    fraud_scores = 1 / (1 + np.exp(scores))  # Sigmoid transformation
    
    return model, X_test, y_test, y_pred_binary, fraud_scores


def evaluate_fraud_model(model, X_test, y_test, y_pred, fraud_scores, feature_names, save_path):
    """
    Evaluate fraud detection model
    """
    logger.info("Evaluating fraud detection model...")
    
    # Classification report
    report = classification_report(y_test, y_pred, target_names=['Normal', 'Fraud'])
    logger.info(f"\nClassification Report:\n{report}")
    
    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    
    # ROC-AUC (if we have probability scores)
    try:
        roc_auc = roc_auc_score(y_test, fraud_scores)
        logger.info(f"ROC-AUC Score: {roc_auc:.3f}")
    except:
        roc_auc = 0.0
        logger.warning("Could not calculate ROC-AUC")
    
    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Confusion Matrix
    sns.heatmap(cm, annot=True, fmt='d', cmap='Reds', ax=axes[0, 0])
    axes[0, 0].set_title('Confusion Matrix - Fraud Detection')
    axes[0, 0].set_xlabel('Predicted')
    axes[0, 0].set_ylabel('Actual')
    
    # Score Distribution
    axes[0, 1].hist([fraud_scores[y_test == 0], fraud_scores[y_test == 1]], 
                    label=['Normal', 'Fraud'], bins=30, alpha=0.7)
    axes[0, 1].set_xlabel('Fraud Score')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Fraud Score Distribution')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Feature Analysis
    feature_importance = np.abs(model.score_samples(X_test).std())
    axes[1, 0].bar(range(len(feature_names)), [feature_importance] * len(feature_names))
    axes[1, 0].set_xticks(range(len(feature_names)))
    axes[1, 0].set_xticklabels(feature_names, rotation=45)
    axes[1, 0].set_title('Feature Contribution to Anomaly Detection')
    axes[1, 0].set_ylabel('Relative Importance')
    
    # Detection Rate by Score Threshold
    thresholds = np.linspace(0, 1, 50)
    tpr_list = []
    fpr_list = []
    
    for threshold in thresholds:
        pred_at_threshold = (fraud_scores > threshold).astype(int)
        tp = np.sum((pred_at_threshold == 1) & (y_test == 1))
        fp = np.sum((pred_at_threshold == 1) & (y_test == 0))
        tn = np.sum((pred_at_threshold == 0) & (y_test == 0))
        fn = np.sum((pred_at_threshold == 0) & (y_test == 1))
        
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        tpr_list.append(tpr)
        fpr_list.append(fpr)
    
    axes[1, 1].plot(fpr_list, tpr_list, 'b-', label=f'ROC (AUC ≈ {roc_auc:.2f})')
    axes[1, 1].plot([0, 1], [0, 1], 'r--', label='Random')
    axes[1, 1].set_xlabel('False Positive Rate')
    axes[1, 1].set_ylabel('True Positive Rate')
    axes[1, 1].set_title('ROC Curve - Fraud Detection')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path / 'fraud_model_evaluation.png', dpi=100, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Evaluation plots saved to {save_path}")
    
    # Save metrics
    with open(save_path / 'fraud_metrics.txt', 'w') as f:
        f.write(f"Fraud Detection Model Evaluation\n")
        f.write(f"=================================\n\n")
        f.write(f"Model: Isolation Forest\n")
        f.write(f"Contamination Factor: 0.1\n\n")
        f.write(f"Performance Metrics:\n")
        f.write(f"ROC-AUC Score: {roc_auc:.3f}\n\n")
        f.write(f"Classification Report:\n{report}\n")
        f.write(f"\nConfusion Matrix:\n{cm}\n")
        f.write(f"\nInterpretation:\n")
        f.write(f"- True Positives (Fraud Caught): {cm[1, 1]}\n")
        f.write(f"- False Positives (False Alarms): {cm[0, 1]}\n")
        f.write(f"- True Negatives (Normal Correct): {cm[0, 0]}\n")
        f.write(f"- False Negatives (Fraud Missed): {cm[1, 0]}\n")
    
    return {
        'roc_auc': roc_auc,
        'confusion_matrix': cm.tolist(),
        'classification_report': report
    }


def main():
    """Main training pipeline"""
    logger.info("Starting fraud detection model training...")
    
    # Set paths
    model_dir = Path("/app/app/ml/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate synthetic data
    df = generate_synthetic_fraud_data(n_samples=5000)
    
    # Save sample data
    df.head(100).to_csv(model_dir / 'fraud_sample_data.csv', index=False)
    logger.info(f"Sample data saved to {model_dir / 'fraud_sample_data.csv'}")
    
    # Prepare features
    X, y, feature_names = prepare_features(df)
    
    # Train model
    model, X_test, y_test, y_pred, fraud_scores = train_fraud_model(X, y)
    
    # Evaluate
    metrics = evaluate_fraud_model(
        model, X_test, y_test, y_pred, fraud_scores, 
        feature_names, model_dir
    )
    
    # Save model
    model_path = model_dir / 'fraud_model.joblib'
    joblib.dump(model, model_path)
    logger.info(f"Model saved to {model_path}")
    
    # Test loading
    loaded_model = joblib.load(model_path)
    test_pred = loaded_model.predict(X_test[:5])
    logger.info(f"Model loaded successfully. Test predictions: {test_pred}")
    
    logger.info("Fraud detection model training completed!")
    
    # Notebook-style interpretation comments
    interpretation = """
    === Model Interpretation ===
    
    The Isolation Forest algorithm works by isolating anomalies rather than profiling normal data points.
    
    Key insights:
    1. Anomalies are few and different, making them easier to isolate
    2. The algorithm builds random trees and measures path length to isolate points
    3. Shorter paths indicate anomalies (easier to isolate)
    
    Feature importance for fraud detection:
    - amount_normalized: Unusual donation amounts (too high or structured)
    - frequency: Abnormal donation frequency patterns
    - time_anomaly: Donations at unusual times
    - duplicate_flag: Multiple registrations from same source
    
    The model learns to identify:
    - Donation fraud: Suspicious amounts, frequencies, or patterns
    - Beneficiary fraud: Duplicate registrations, excessive aid claims
    - Data inconsistencies: Mismatched information patterns
    
    Threshold tuning:
    - Lower threshold: Catch more fraud but more false positives
    - Higher threshold: Fewer false alarms but might miss some fraud
    - Current contamination factor: 0.1 (expecting ~10% anomalies)
    """
    
    logger.info(interpretation)
    
    with open(model_dir / 'fraud_model_interpretation.txt', 'w') as f:
        f.write(interpretation)
    
    return metrics


if __name__ == "__main__":
    metrics = main()