#!/usr/bin/env python3
"""
Eligibility Model Training Script for the Blessings Donation System.

This script trains a machine learning model to assess employee eligibility
for ration distribution based on various features.
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler, LabelEncoder
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


def generate_synthetic_data(n_samples=2000):
    """
    Generate synthetic training data for eligibility prediction.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        pd.DataFrame: Generated dataset
    """
    print(f"Generating {n_samples} synthetic training samples...")
    
    np.random.seed(42)  # For reproducible results
    
    data = []
    
    for i in range(n_samples):
        # Employee basic info
        employee_id = f"EMP{i+1:05d}"
        
        # Grade (1-20, lower is higher need)
        grade = np.random.choice(range(1, 21), p=generate_grade_probabilities())
        
        # Family size (1-12 members)
        family_size = np.random.choice(range(1, 13), p=generate_family_size_probabilities())
        
        # Income estimate based on grade (lower grade = higher income)
        base_income = 15000 + (20 - grade) * 5000  # Grade 20 = 15k, Grade 1 = 110k
        income_variation = np.random.normal(0, base_income * 0.2)
        income_estimate = max(10000, base_income + income_variation)
        
        # Previous aid count (0-10)
        previous_aid_count = np.random.poisson(2)  # Average 2 previous aids
        previous_aid_count = min(previous_aid_count, 10)
        
        # Dependents (0 to family_size-1)
        dependents = max(0, family_size - np.random.choice([1, 2]))
        
        # Employment status
        employment_status = np.random.choice(['permanent', 'contract', 'temporary'], 
                                           p=[0.6, 0.3, 0.1])
        
        # Years of service
        years_of_service = np.random.exponential(5)  # Average 5 years
        years_of_service = min(years_of_service, 35)  # Cap at 35 years
        
        # Medical expenses (monthly)
        medical_expenses = np.random.gamma(2, 1000)  # Average 2000 PKR
        medical_expenses = min(medical_expenses, 20000)  # Cap at 20k
        
        # Housing status
        housing_status = np.random.choice(['owned', 'rented', 'family'], p=[0.4, 0.5, 0.1])
        
        # Education expenses (monthly)
        education_expenses = family_size * np.random.gamma(1.5, 500)  # Per child
        education_expenses = min(education_expenses, 15000)  # Cap at 15k
        
        # Calculate eligibility based on business rules
        eligibility_score = calculate_eligibility_score(
            grade, family_size, income_estimate, previous_aid_count,
            dependents, employment_status, years_of_service,
            medical_expenses, housing_status, education_expenses
        )
        
        # Convert to binary classification (eligible/not eligible)
        is_eligible = 1 if eligibility_score >= 0.6 else 0
        
        data.append({
            'employee_id': employee_id,
            'grade': grade,
            'family_size': family_size,
            'income_estimate': income_estimate,
            'previous_aid_count': previous_aid_count,
            'dependents': dependents,
            'employment_status': employment_status,
            'years_of_service': years_of_service,
            'medical_expenses': medical_expenses,
            'housing_status': housing_status,
            'education_expenses': education_expenses,
            'eligibility_score': eligibility_score,
            'is_eligible': is_eligible
        })
    
    df = pd.DataFrame(data)
    print(f"Generated dataset shape: {df.shape}")
    print(f"Eligible: {df['is_eligible'].sum()}, Not Eligible: {len(df) - df['is_eligible'].sum()}")
    
    return df


def generate_grade_probabilities():
    """Generate probabilities for grade distribution (higher grades more common)."""
    # Higher grades (lower numbers) should be less common
    probs = np.array([0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11,
                     0.12, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03])
    return probs / probs.sum()


def generate_family_size_probabilities():
    """Generate probabilities for family size distribution."""
    # Most families have 3-6 members
    probs = np.array([0.05, 0.10, 0.20, 0.25, 0.20, 0.15, 0.08, 0.04, 0.02, 0.01, 0.005, 0.005])
    return probs / probs.sum()


def calculate_eligibility_score(grade, family_size, income_estimate, previous_aid_count,
                              dependents, employment_status, years_of_service,
                              medical_expenses, housing_status, education_expenses):
    """
    Calculate eligibility score based on business rules.
    
    Returns:
        float: Eligibility score between 0 and 1
    """
    score = 0.0
    
    # Grade-based scoring (higher grade = higher need)
    if grade >= 15:
        score += 0.3
    elif grade >= 10:
        score += 0.2
    elif grade >= 5:
        score += 0.1
    
    # Family size scoring
    if family_size >= 6:
        score += 0.25
    elif family_size >= 4:
        score += 0.15
    elif family_size >= 2:
        score += 0.05
    
    # Income-based scoring (lower income = higher need)
    if income_estimate <= 25000:
        score += 0.3
    elif income_estimate <= 40000:
        score += 0.2
    elif income_estimate <= 60000:
        score += 0.1
    
    # Previous aid (less previous aid = higher priority)
    if previous_aid_count == 0:
        score += 0.1
    elif previous_aid_count <= 2:
        score += 0.05
    else:
        score -= 0.05  # Penalty for frequent aid
    
    # Dependents scoring
    score += min(dependents * 0.02, 0.1)
    
    # Employment status
    if employment_status == 'temporary':
        score += 0.1
    elif employment_status == 'contract':
        score += 0.05
    
    # Medical expenses
    if medical_expenses >= 5000:
        score += 0.1
    elif medical_expenses >= 2000:
        score += 0.05
    
    # Housing status
    if housing_status == 'rented':
        score += 0.05
    
    # Education expenses
    if education_expenses >= 5000:
        score += 0.05
    
    # Add some randomness to make it more realistic
    noise = np.random.normal(0, 0.05)
    score = max(0, min(1, score + noise))
    
    return score


def prepare_features(df):
    """
    Prepare features for machine learning.
    
    Args:
        df: Raw dataframe
        
    Returns:
        tuple: (X, y, feature_names, encoders)
    """
    print("Preparing features...")
    
    # Create a copy for processing
    data = df.copy()
    
    # Encode categorical variables
    encoders = {}
    
    # Employment status
    le_employment = LabelEncoder()
    data['employment_status_encoded'] = le_employment.fit_transform(data['employment_status'])
    encoders['employment_status'] = le_employment
    
    # Housing status
    le_housing = LabelEncoder()
    data['housing_status_encoded'] = le_housing.fit_transform(data['housing_status'])
    encoders['housing_status'] = le_housing
    
    # Create derived features
    data['income_per_member'] = data['income_estimate'] / data['family_size']
    data['expense_ratio'] = (data['medical_expenses'] + data['education_expenses']) / data['income_estimate']
    data['grade_family_interaction'] = data['grade'] * data['family_size']
    data['aid_frequency'] = data['previous_aid_count'] / max(data['years_of_service'], 1)
    
    # Select features for training
    feature_columns = [
        'grade', 'family_size', 'income_estimate', 'previous_aid_count',
        'dependents', 'employment_status_encoded', 'years_of_service',
        'medical_expenses', 'housing_status_encoded', 'education_expenses',
        'income_per_member', 'expense_ratio', 'grade_family_interaction', 'aid_frequency'
    ]
    
    X = data[feature_columns].values
    y = data['is_eligible'].values
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Target distribution: {np.bincount(y)}")
    
    return X, y, feature_columns, encoders


def train_model(X, y, feature_names):
    """
    Train the eligibility prediction model.
    
    Args:
        X: Feature matrix
        y: Target vector
        feature_names: List of feature names
        
    Returns:
        tuple: (best_model, scaler, metrics)
    """
    print("Training eligibility prediction model...")
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Define models to try
    models = {
        'RandomForest': RandomForestClassifier(random_state=42),
        'GradientBoosting': GradientBoostingClassifier(random_state=42)
    }
    
    best_model = None
    best_score = 0
    best_model_name = ""
    
    results = {}
    
    for name, model in models.items():
        print(f"\nTraining {name}...")
        
        # Hyperparameter tuning
        if name == 'RandomForest':
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [10, 15, None],
                'min_samples_split': [2, 5],
                'min_samples_leaf': [1, 2]
            }
        else:  # GradientBoosting
            param_grid = {
                'n_estimators': [100, 200],
                'learning_rate': [0.05, 0.1],
                'max_depth': [3, 5],
                'min_samples_split': [2, 5]
            }
        
        # Grid search with cross-validation
        grid_search = GridSearchCV(
            model, param_grid, cv=5, scoring='roc_auc',
            n_jobs=-1, verbose=1
        )
        
        grid_search.fit(X_train_scaled, y_train)
        
        # Evaluate on test set
        y_pred = grid_search.predict(X_test_scaled)
        y_pred_proba = grid_search.predict_proba(X_test_scaled)[:, 1]
        
        auc_score = roc_auc_score(y_test, y_pred_proba)
        
        results[name] = {
            'model': grid_search.best_estimator_,
            'best_params': grid_search.best_params_,
            'cv_score': grid_search.best_score_,
            'test_auc': auc_score,
            'predictions': y_pred,
            'probabilities': y_pred_proba
        }
        
        print(f"{name} - CV Score: {grid_search.best_score_:.4f}, Test AUC: {auc_score:.4f}")
        
        if auc_score > best_score:
            best_score = auc_score
            best_model = grid_search.best_estimator_
            best_model_name = name
    
    print(f"\nBest model: {best_model_name} (AUC: {best_score:.4f})")
    
    # Generate detailed metrics for the best model
    best_results = results[best_model_name]
    y_pred = best_results['predictions']
    y_pred_proba = best_results['probabilities']
    
    # Classification report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Feature importance
    if hasattr(best_model, 'feature_importances_'):
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': best_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nTop 10 Most Important Features:")
        print(feature_importance.head(10))
        
        # Plot feature importance
        plt.figure(figsize=(10, 8))
        sns.barplot(data=feature_importance.head(10), x='importance', y='feature')
        plt.title('Top 10 Feature Importances - Eligibility Model')
        plt.xlabel('Importance')
        plt.tight_layout()
        plt.savefig(os.path.join(PLOTS_DIR, 'eligibility_feature_importance.png'))
        plt.close()
    
    # ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label=f'ROC Curve (AUC = {best_score:.4f})')
    plt.plot([0, 1], [0, 1], 'k--', label='Random')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve - Eligibility Model')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(PLOTS_DIR, 'eligibility_roc_curve.png'))
    plt.close()
    
    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Not Eligible', 'Eligible'],
                yticklabels=['Not Eligible', 'Eligible'])
    plt.title('Confusion Matrix - Eligibility Model')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig(os.path.join(PLOTS_DIR, 'eligibility_confusion_matrix.png'))
    plt.close()
    
    metrics = {
        'model_name': best_model_name,
        'cv_score': best_results['cv_score'],
        'test_auc': best_score,
        'best_params': best_results['best_params'],
        'feature_importance': feature_importance.to_dict('records') if hasattr(best_model, 'feature_importances_') else None
    }
    
    return best_model, scaler, metrics


def save_model(model, scaler, encoders, feature_names, metrics):
    """
    Save the trained model and preprocessing objects.
    
    Args:
        model: Trained model
        scaler: Feature scaler
        encoders: Label encoders
        feature_names: List of feature names
        metrics: Model metrics
    """
    print("Saving model...")
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'encoders': encoders,
        'feature_names': feature_names,
        'metrics': metrics,
        'created_at': datetime.now().isoformat(),
        'version': '1.0'
    }
    
    model_path = os.path.join(MODEL_DIR, 'eligibility_model.joblib')
    joblib.dump(model_data, model_path)
    
    print(f"Model saved to: {model_path}")
    
    # Save metrics to JSON
    import json
    metrics_path = os.path.join(MODEL_DIR, 'eligibility_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"Metrics saved to: {metrics_path}")


def main():
    """Main training pipeline."""
    print("Starting Eligibility Model Training Pipeline")
    print("=" * 50)
    
    # Generate synthetic data
    df = generate_synthetic_data(n_samples=2000)
    
    # Save training data
    train_data_path = os.path.join(DATA_DIR, 'eligibility_training_data.csv')
    df.to_csv(train_data_path, index=False)
    print(f"Training data saved to: {train_data_path}")
    
    # Prepare features
    X, y, feature_names, encoders = prepare_features(df)
    
    # Train model
    model, scaler, metrics = train_model(X, y, feature_names)
    
    # Save model
    save_model(model, scaler, encoders, feature_names, metrics)
    
    print("\n" + "=" * 50)
    print("Training completed successfully!")
    print(f"Final AUC Score: {metrics['test_auc']:.4f}")
    print("Model artifacts saved in:", MODEL_DIR)
    print("Plots saved in:", PLOTS_DIR)


if __name__ == "__main__":
    main()