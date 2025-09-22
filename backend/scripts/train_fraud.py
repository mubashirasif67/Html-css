#!/usr/bin/env python3
"""
Fraud Detection Model Training Script for the Blessings Donation System.

This script trains a machine learning model to detect potentially fraudulent
donations using various features and anomaly detection techniques.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_curve
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# Set up paths
MODEL_DIR = "app/ml/models"
DATA_DIR = "data"
PLOTS_DIR = "data/plots"

# Create directories if they don't exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)


def generate_synthetic_fraud_data(n_samples=1500, fraud_rate=0.05):
    """
    Generate synthetic donation data with fraud indicators.
    
    Args:
        n_samples: Number of samples to generate
        fraud_rate: Proportion of fraudulent donations
        
    Returns:
        pd.DataFrame: Generated dataset with fraud labels
    """
    print(f"Generating {n_samples} synthetic donation samples (fraud rate: {fraud_rate:.2%})...")
    
    np.random.seed(42)  # For reproducible results
    
    n_fraud = int(n_samples * fraud_rate)
    n_legitimate = n_samples - n_fraud
    
    data = []
    
    # Generate legitimate donations
    for i in range(n_legitimate):
        donation = generate_legitimate_donation(i + 1)
        donation['is_fraud'] = 0
        data.append(donation)
    
    # Generate fraudulent donations
    for i in range(n_fraud):
        donation = generate_fraudulent_donation(i + n_legitimate + 1)
        donation['is_fraud'] = 1
        data.append(donation)
    
    # Shuffle the data
    np.random.shuffle(data)
    
    df = pd.DataFrame(data)
    print(f"Generated dataset shape: {df.shape}")
    print(f"Fraudulent: {df['is_fraud'].sum()}, Legitimate: {len(df) - df['is_fraud'].sum()}")
    
    return df


def generate_legitimate_donation(donation_id):
    """Generate a legitimate donation record."""
    # Normal donation amounts (Pakistani context)
    amount_categories = [
        (100, 500, 0.3),    # Small donations
        (500, 2000, 0.4),   # Medium donations  
        (2000, 10000, 0.25), # Large donations
        (10000, 50000, 0.05) # Very large donations
    ]
    
    category = np.random.choice(len(amount_categories), p=[cat[2] for cat in amount_categories])
    min_amt, max_amt, _ = amount_categories[category]
    
    # Generate amount with some randomness
    if np.random.random() < 0.7:
        # Round amounts are common
        amount = np.random.choice([100, 200, 500, 1000, 2000, 5000, 10000])
        if amount < min_amt or amount > max_amt:
            amount = np.random.uniform(min_amt, max_amt)
    else:
        amount = np.random.uniform(min_amt, max_amt)
    
    # Donation timing (business hours more common)
    hour = np.random.choice(range(24), p=generate_hour_probabilities())
    day_of_week = np.random.choice(range(7), p=[0.1, 0.15, 0.15, 0.15, 0.15, 0.2, 0.1])  # Weekend slightly higher
    
    # Donor information
    donor_age = np.random.normal(35, 12)  # Average age 35
    donor_age = max(18, min(80, donor_age))
    
    # Location (Pakistani cities)
    cities = ['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Multan', 'Peshawar', 'Quetta']
    city = np.random.choice(cities, p=[0.3, 0.25, 0.15, 0.1, 0.08, 0.05, 0.04, 0.03])
    
    # Payment method
    payment_methods = ['bank_transfer', 'cash', 'online', 'mobile_wallet']
    payment_method = np.random.choice(payment_methods, p=[0.4, 0.3, 0.2, 0.1])
    
    # Donation type
    donation_types = ['zakat', 'sadaqah', 'general']
    donation_type = np.random.choice(donation_types, p=[0.4, 0.35, 0.25])
    
    # Email and phone patterns (legitimate)
    has_email = np.random.random() < 0.8  # 80% have email
    has_phone = np.random.random() < 0.9  # 90% have phone
    
    return {
        'donation_id': f"DON{donation_id:06d}",
        'amount': round(amount, 2),
        'hour_of_day': hour,
        'day_of_week': day_of_week,
        'donor_age': round(donor_age),
        'city': city,
        'payment_method': payment_method,
        'donation_type': donation_type,
        'has_email': int(has_email),
        'has_phone': int(has_phone),
        'amount_is_round': int(amount % 100 == 0),
        'submission_speed': np.random.normal(120, 60),  # Seconds to fill form
        'repeat_donor': int(np.random.random() < 0.3),  # 30% repeat donors
        'cnic_provided': int(np.random.random() < 0.7),  # 70% provide CNIC
    }


def generate_fraudulent_donation(donation_id):
    """Generate a fraudulent donation record with suspicious patterns."""
    # Fraudulent donations often have suspicious amounts
    fraud_patterns = [
        'round_large',      # Large round numbers
        'duplicate',        # Duplicate amounts
        'unusual_timing',   # Unusual timing
        'fake_info',        # Fake information patterns
        'rapid_submission'  # Too fast submission
    ]
    
    fraud_type = np.random.choice(fraud_patterns)
    
    if fraud_type == 'round_large':
        # Very round, large amounts
        amount = np.random.choice([10000, 20000, 50000, 100000])
    elif fraud_type == 'duplicate':
        # Common duplicate amounts
        amount = np.random.choice([5000, 7500, 15000])
    else:
        # Other fraud types can have various amounts
        amount = np.random.uniform(1000, 25000)
    
    # Suspicious timing patterns
    if fraud_type == 'unusual_timing':
        hour = np.random.choice([2, 3, 4, 23, 0, 1])  # Very late/early hours
    else:
        hour = np.random.choice(range(24), p=generate_hour_probabilities())
    
    day_of_week = np.random.choice(range(7))
    
    # Suspicious donor age
    if fraud_type == 'fake_info':
        donor_age = np.random.choice([25, 30, 35, 40])  # Round ages
    else:
        donor_age = np.random.normal(32, 8)
        donor_age = max(18, min(70, donor_age))
    
    # Location (fraudulent might prefer certain cities)
    cities = ['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Multan', 'Peshawar', 'Quetta']
    if fraud_type == 'fake_info':
        city = np.random.choice(['Karachi', 'Lahore'], p=[0.6, 0.4])  # Prefer major cities
    else:
        city = np.random.choice(cities, p=[0.3, 0.25, 0.15, 0.1, 0.08, 0.05, 0.04, 0.03])
    
    # Payment method (fraud might prefer certain methods)
    payment_methods = ['bank_transfer', 'cash', 'online', 'mobile_wallet']
    payment_method = np.random.choice(payment_methods, p=[0.5, 0.2, 0.25, 0.05])
    
    # Donation type
    donation_types = ['zakat', 'sadaqah', 'general']
    donation_type = np.random.choice(donation_types, p=[0.5, 0.3, 0.2])  # Zakat more common in fraud
    
    # Contact information (fraudulent patterns)
    has_email = int(np.random.random() < 0.6)  # Less likely to provide email
    has_phone = int(np.random.random() < 0.7)  # Less likely to provide phone
    
    # Suspicious submission speed
    if fraud_type == 'rapid_submission':
        submission_speed = np.random.uniform(10, 30)  # Very fast
    else:
        submission_speed = np.random.normal(90, 40)  # Slightly faster than normal
    
    return {
        'donation_id': f"DON{donation_id:06d}",
        'amount': round(amount, 2),
        'hour_of_day': hour,
        'day_of_week': day_of_week,
        'donor_age': round(donor_age),
        'city': city,
        'payment_method': payment_method,
        'donation_type': donation_type,
        'has_email': has_email,
        'has_phone': has_phone,
        'amount_is_round': int(amount % 1000 == 0),  # More likely to be round
        'submission_speed': max(5, submission_speed),
        'repeat_donor': int(np.random.random() < 0.1),  # Less likely to be repeat
        'cnic_provided': int(np.random.random() < 0.4),  # Less likely to provide CNIC
        'fraud_type': fraud_type
    }


def generate_hour_probabilities():
    """Generate probabilities for hour of day (business hours more likely)."""
    probs = np.array([
        0.01, 0.01, 0.01, 0.01, 0.01, 0.02,  # 0-5 AM
        0.03, 0.04, 0.06, 0.08, 0.10, 0.12,  # 6-11 AM
        0.10, 0.08, 0.09, 0.10, 0.08, 0.07,  # 12-5 PM
        0.06, 0.05, 0.04, 0.03, 0.02, 0.01   # 6-11 PM
    ])
    return probs / probs.sum()


def prepare_features(df):
    """
    Prepare features for fraud detection model.
    
    Args:
        df: Raw dataframe
        
    Returns:
        tuple: (X, y, feature_names, encoders)
    """
    print("Preparing features for fraud detection...")
    
    # Create a copy for processing
    data = df.copy()
    
    # Encode categorical variables
    encoders = {}
    
    # City encoding (one-hot for major cities, 'other' for rest)
    major_cities = ['Karachi', 'Lahore', 'Islamabad', 'Rawalpindi']
    for city in major_cities:
        data[f'city_{city.lower()}'] = (data['city'] == city).astype(int)
    
    # Payment method encoding
    payment_methods = ['bank_transfer', 'cash', 'online', 'mobile_wallet']
    for method in payment_methods:
        data[f'payment_{method}'] = (data['payment_method'] == method).astype(int)
    
    # Donation type encoding
    donation_types = ['zakat', 'sadaqah', 'general']
    for dtype in donation_types:
        data[f'type_{dtype}'] = (data['donation_type'] == dtype).astype(int)
    
    # Create derived features
    data['amount_log'] = np.log1p(data['amount'])
    data['is_weekend'] = (data['day_of_week'] >= 5).astype(int)
    data['is_night'] = ((data['hour_of_day'] >= 22) | (data['hour_of_day'] <= 5)).astype(int)
    data['is_business_hours'] = ((data['hour_of_day'] >= 9) & (data['hour_of_day'] <= 17)).astype(int)
    data['submission_speed_log'] = np.log1p(data['submission_speed'])
    data['contact_completeness'] = data['has_email'] + data['has_phone'] + data['cnic_provided']
    
    # Amount-based features
    data['amount_is_very_round'] = ((data['amount'] % 1000) == 0).astype(int)
    data['amount_category'] = pd.cut(data['amount'], 
                                   bins=[0, 500, 2000, 10000, float('inf')], 
                                   labels=[0, 1, 2, 3]).astype(int)
    
    # Select features for training
    feature_columns = [
        'amount', 'amount_log', 'hour_of_day', 'day_of_week', 'donor_age',
        'has_email', 'has_phone', 'amount_is_round', 'amount_is_very_round',
        'submission_speed', 'submission_speed_log', 'repeat_donor', 'cnic_provided',
        'contact_completeness', 'is_weekend', 'is_night', 'is_business_hours',
        'amount_category'
    ]
    
    # Add encoded categorical features
    feature_columns.extend([f'city_{city.lower()}' for city in major_cities])
    feature_columns.extend([f'payment_{method}' for method in payment_methods])
    feature_columns.extend([f'type_{dtype}' for dtype in donation_types])
    
    X = data[feature_columns].values
    y = data['is_fraud'].values
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Fraud distribution: Legitimate: {np.sum(y == 0)}, Fraudulent: {np.sum(y == 1)}")
    
    return X, y, feature_columns, encoders


def train_fraud_model(X, y, feature_names):
    """
    Train the fraud detection model using Isolation Forest.
    
    Args:
        X: Feature matrix
        y: Target vector (for evaluation only)
        feature_names: List of feature names
        
    Returns:
        tuple: (model, scaler, metrics)
    """
    print("Training fraud detection model...")
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Use only legitimate donations for training (unsupervised)
    X_train_clean = X_train[y_train == 0]
    
    print(f"Training on {len(X_train_clean)} legitimate donations")
    
    # Scale the features
    scaler = RobustScaler()  # More robust to outliers
    X_train_scaled = scaler.fit_transform(X_train_clean)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Isolation Forest
    contamination_rate = 0.05  # Expected fraud rate
    
    iso_forest = IsolationForest(
        contamination=contamination_rate,
        random_state=42,
        n_estimators=200,
        max_samples='auto',
        max_features=1.0,
        bootstrap=False,
        n_jobs=-1,
        verbose=1
    )
    
    iso_forest.fit(X_train_scaled)
    
    # Predict on test set
    y_pred = iso_forest.predict(X_test_scaled)
    y_pred_binary = (y_pred == -1).astype(int)  # -1 indicates anomaly (fraud)
    
    # Get anomaly scores
    anomaly_scores = iso_forest.decision_function(X_test_scaled)
    # Convert to fraud probability (higher score = less likely to be fraud)
    fraud_probabilities = 1 / (1 + np.exp(anomaly_scores))  # Sigmoid transformation
    
    # Evaluate performance
    print("\nFraud Detection Performance:")
    print(classification_report(y_test, y_pred_binary, target_names=['Legitimate', 'Fraudulent']))
    
    # Calculate precision-recall curve
    precision, recall, thresholds = precision_recall_curve(y_test, fraud_probabilities)
    
    # Find optimal threshold
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
    optimal_idx = np.argmax(f1_scores)
    optimal_threshold = thresholds[optimal_idx] if optimal_idx < len(thresholds) else 0.5
    
    print(f"Optimal threshold: {optimal_threshold:.4f}")
    print(f"Best F1 Score: {f1_scores[optimal_idx]:.4f}")
    
    # Plot precision-recall curve
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, label=f'Fraud Detection (AUC = {np.trapz(precision, recall):.4f})')
    plt.scatter(recall[optimal_idx], precision[optimal_idx], color='red', s=100, 
               label=f'Optimal Point (F1={f1_scores[optimal_idx]:.3f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve - Fraud Detection')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(PLOTS_DIR, 'fraud_precision_recall_curve.png'))
    plt.close()
    
    # Plot confusion matrix
    cm = confusion_matrix(y_test, y_pred_binary)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Reds',
                xticklabels=['Legitimate', 'Fraudulent'],
                yticklabels=['Legitimate', 'Fraudulent'])
    plt.title('Confusion Matrix - Fraud Detection')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(os.path.join(PLOTS_DIR, 'fraud_confusion_matrix.png'))
    plt.close()
    
    # Plot anomaly score distribution
    plt.figure(figsize=(10, 6))
    legitimate_scores = anomaly_scores[y_test == 0]
    fraud_scores = anomaly_scores[y_test == 1]
    
    plt.hist(legitimate_scores, bins=50, alpha=0.7, label='Legitimate', color='blue')
    plt.hist(fraud_scores, bins=50, alpha=0.7, label='Fraudulent', color='red')
    plt.axvline(x=np.log(optimal_threshold / (1 - optimal_threshold)), color='green', 
                linestyle='--', label='Optimal Threshold')
    plt.xlabel('Anomaly Score')
    plt.ylabel('Frequency')
    plt.title('Distribution of Anomaly Scores')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(PLOTS_DIR, 'fraud_score_distribution.png'))
    plt.close()
    
    # Calculate metrics
    from sklearn.metrics import precision_score, recall_score, f1_score
    
    precision_val = precision_score(y_test, y_pred_binary)
    recall_val = recall_score(y_test, y_pred_binary)
    f1_val = f1_score(y_test, y_pred_binary)
    
    metrics = {
        'model_type': 'IsolationForest',
        'contamination_rate': contamination_rate,
        'precision': precision_val,
        'recall': recall_val,
        'f1_score': f1_val,
        'optimal_threshold': optimal_threshold,
        'n_estimators': iso_forest.n_estimators,
        'training_samples': len(X_train_clean)
    }
    
    print(f"\nFinal Metrics:")
    print(f"Precision: {precision_val:.4f}")
    print(f"Recall: {recall_val:.4f}")
    print(f"F1 Score: {f1_val:.4f}")
    
    return iso_forest, scaler, metrics


def save_fraud_model(model, scaler, feature_names, metrics):
    """
    Save the trained fraud detection model.
    
    Args:
        model: Trained model
        scaler: Feature scaler
        feature_names: List of feature names
        metrics: Model metrics
    """
    print("Saving fraud detection model...")
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_names,
        'metrics': metrics,
        'created_at': datetime.now().isoformat(),
        'version': '1.0',
        'model_type': 'fraud_detection'
    }
    
    model_path = os.path.join(MODEL_DIR, 'fraud_model.joblib')
    joblib.dump(model_data, model_path)
    
    print(f"Fraud model saved to: {model_path}")
    
    # Save metrics to JSON
    import json
    metrics_path = os.path.join(MODEL_DIR, 'fraud_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"Metrics saved to: {metrics_path}")


def main():
    """Main training pipeline for fraud detection."""
    print("Starting Fraud Detection Model Training Pipeline")
    print("=" * 55)
    
    # Generate synthetic data
    df = generate_synthetic_fraud_data(n_samples=1500, fraud_rate=0.05)
    
    # Save training data
    train_data_path = os.path.join(DATA_DIR, 'fraud_training_data.csv')
    df.to_csv(train_data_path, index=False)
    print(f"Training data saved to: {train_data_path}")
    
    # Prepare features
    X, y, feature_names, encoders = prepare_features(df)
    
    # Train model
    model, scaler, metrics = train_fraud_model(X, y, feature_names)
    
    # Save model
    save_fraud_model(model, scaler, feature_names, metrics)
    
    print("\n" + "=" * 55)
    print("Fraud detection model training completed successfully!")
    print(f"Final F1 Score: {metrics['f1_score']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print("Model artifacts saved in:", MODEL_DIR)
    print("Plots saved in:", PLOTS_DIR)


if __name__ == "__main__":
    main()