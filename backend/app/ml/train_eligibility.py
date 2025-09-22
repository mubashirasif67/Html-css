#!/usr/bin/env python
"""
Train eligibility classification model
This script generates synthetic training data and trains a model to predict beneficiary eligibility
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging
from datetime import datetime, timedelta
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_synthetic_data(n_samples=5000):
    """
    Generate synthetic training data for eligibility model
    
    Features:
    - grade: Employee grade (1-22)
    - family_size: Number of family members
    - income_estimate: Estimated monthly income
    - previous_aid_count: Number of times received aid
    - days_since_last_aid: Days since last distribution
    
    Target:
    - eligible: 1 if eligible, 0 if not
    """
    logger.info(f"Generating {n_samples} synthetic samples...")
    
    data = []
    
    for i in range(n_samples):
        # Generate features with realistic distributions
        grade = np.random.choice(range(1, 23), p=get_grade_distribution())
        family_size = max(1, int(np.random.normal(4, 1.5)))
        
        # Income correlated with grade (higher grade = higher income)
        base_income = 20000 + (grade * 3000)
        income_estimate = max(15000, np.random.normal(base_income, 10000))
        
        previous_aid_count = np.random.poisson(1.5)
        days_since_last_aid = np.random.randint(30, 365)
        
        # Rule-based eligibility with some noise
        eligibility_score = 0.5
        
        # Grade impact (lower grades more eligible)
        if grade <= 5:
            eligibility_score += 0.3
        elif grade <= 10:
            eligibility_score += 0.2
        elif grade <= 15:
            eligibility_score += 0.1
        else:
            eligibility_score -= 0.15
        
        # Family size impact
        if family_size >= 5:
            eligibility_score += 0.2
        elif family_size >= 3:
            eligibility_score += 0.1
        else:
            eligibility_score -= 0.1
        
        # Income impact
        if income_estimate < 30000:
            eligibility_score += 0.25
        elif income_estimate < 50000:
            eligibility_score += 0.15
        elif income_estimate > 100000:
            eligibility_score -= 0.3
        
        # Previous aid impact
        if previous_aid_count > 3:
            eligibility_score -= 0.2
        elif previous_aid_count == 0:
            eligibility_score += 0.1
        
        # Days since last aid
        if days_since_last_aid > 180:
            eligibility_score += 0.15
        elif days_since_last_aid < 60:
            eligibility_score -= 0.15
        
        # Add noise
        eligibility_score += np.random.normal(0, 0.1)
        
        # Convert to binary with threshold
        eligible = 1 if eligibility_score > 0.5 else 0
        
        # Occasionally flip labels for more realistic data
        if np.random.random() < 0.05:  # 5% label noise
            eligible = 1 - eligible
        
        data.append({
            'grade': grade,
            'family_size': family_size,
            'income_estimate': income_estimate,
            'previous_aid_count': previous_aid_count,
            'days_since_last_aid': days_since_last_aid,
            'eligible': eligible
        })
    
    df = pd.DataFrame(data)
    
    # Log class distribution
    class_dist = df['eligible'].value_counts()
    logger.info(f"Class distribution: Eligible={class_dist.get(1, 0)}, Not Eligible={class_dist.get(0, 0)}")
    
    return df


def get_grade_distribution():
    """Get realistic grade distribution (more employees in middle grades)"""
    # Bell curve centered around grade 10-12
    grades = np.arange(1, 23)
    probs = np.exp(-0.5 * ((grades - 11) / 5) ** 2)
    probs = probs / probs.sum()
    return probs


def prepare_features(df):
    """
    Prepare and normalize features for training
    """
    # Normalize features
    feature_cols = ['grade', 'family_size', 'income_estimate', 
                   'previous_aid_count', 'days_since_last_aid']
    
    # Create normalized versions
    df['grade_norm'] = (df['grade'] - 1) / 21.0
    df['family_size_norm'] = df['family_size'] / 10.0
    df['income_norm'] = np.clip(df['income_estimate'] / 100000.0, 0, 1)
    df['previous_aid_norm'] = df['previous_aid_count'] / 10.0
    df['days_norm'] = np.clip(df['days_since_last_aid'] / 365.0, 0, 1)
    
    feature_cols_norm = ['grade_norm', 'family_size_norm', 'income_norm',
                        'previous_aid_norm', 'days_norm']
    
    return df[feature_cols_norm].values, df['eligible'].values


def train_model(X, y):
    """
    Train eligibility classification model
    """
    logger.info("Training eligibility model...")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Try multiple models
    models = {
        'RandomForest': RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        ),
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
    }
    
    best_model = None
    best_score = 0
    
    for name, model in models.items():
        logger.info(f"Training {name}...")
        
        # Train
        model.fit(X_train, y_train)
        
        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
        mean_cv_score = cv_scores.mean()
        
        logger.info(f"{name} CV ROC-AUC: {mean_cv_score:.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        # Test set performance
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        test_score = roc_auc_score(y_test, y_pred_proba)
        logger.info(f"{name} Test ROC-AUC: {test_score:.3f}")
        
        if test_score > best_score:
            best_score = test_score
            best_model = model
    
    logger.info(f"Best model selected with ROC-AUC: {best_score:.3f}")
    
    return best_model, X_test, y_test


def evaluate_model(model, X_test, y_test, save_path):
    """
    Evaluate model and save metrics
    """
    logger.info("Evaluating model...")
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Classification report
    report = classification_report(y_test, y_pred, target_names=['Not Eligible', 'Eligible'])
    logger.info(f"\nClassification Report:\n{report}")
    
    # ROC-AUC
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    logger.info(f"ROC-AUC Score: {roc_auc:.3f}")
    
    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    
    # Create visualizations
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Confusion Matrix
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0])
    axes[0].set_title('Confusion Matrix')
    axes[0].set_xlabel('Predicted')
    axes[0].set_ylabel('Actual')
    
    # ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    axes[1].plot(fpr, tpr, label=f'ROC Curve (AUC = {roc_auc:.3f})')
    axes[1].plot([0, 1], [0, 1], 'k--', label='Random')
    axes[1].set_xlabel('False Positive Rate')
    axes[1].set_ylabel('True Positive Rate')
    axes[1].set_title('ROC Curve')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    # Feature Importance (if RandomForest)
    if hasattr(model, 'feature_importances_'):
        feature_names = ['Grade', 'Family Size', 'Income', 'Previous Aid', 'Days Since Aid']
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        axes[2].bar(range(len(importances)), importances[indices])
        axes[2].set_xticks(range(len(importances)))
        axes[2].set_xticklabels([feature_names[i] for i in indices], rotation=45)
        axes[2].set_title('Feature Importance')
        axes[2].set_ylabel('Importance')
    
    plt.tight_layout()
    plt.savefig(save_path / 'eligibility_model_evaluation.png', dpi=100, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Evaluation plots saved to {save_path}")
    
    # Save metrics to file
    with open(save_path / 'eligibility_metrics.txt', 'w') as f:
        f.write(f"Model Evaluation Metrics\n")
        f.write(f"========================\n\n")
        f.write(f"ROC-AUC Score: {roc_auc:.3f}\n\n")
        f.write(f"Classification Report:\n{report}\n")
        f.write(f"\nConfusion Matrix:\n{cm}\n")
        f.write(f"\nFeature Importance:\n")
        if hasattr(model, 'feature_importances_'):
            for name, importance in zip(feature_names, model.feature_importances_):
                f.write(f"  {name}: {importance:.3f}\n")
    
    return {
        'roc_auc': roc_auc,
        'confusion_matrix': cm.tolist(),
        'classification_report': report
    }


def main():
    """Main training pipeline"""
    logger.info("Starting eligibility model training...")
    
    # Set paths
    model_dir = Path("/app/app/ml/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate data
    df = generate_synthetic_data(n_samples=5000)
    
    # Save sample data
    df.head(100).to_csv(model_dir / 'eligibility_sample_data.csv', index=False)
    logger.info(f"Sample data saved to {model_dir / 'eligibility_sample_data.csv'}")
    
    # Prepare features
    X, y = prepare_features(df)
    
    # Train model
    model, X_test, y_test = train_model(X, y)
    
    # Evaluate
    metrics = evaluate_model(model, X_test, y_test, model_dir)
    
    # Save model
    model_path = model_dir / 'eligibility_model.joblib'
    joblib.dump(model, model_path)
    logger.info(f"Model saved to {model_path}")
    
    # Test loading
    loaded_model = joblib.load(model_path)
    test_pred = loaded_model.predict(X_test[:5])
    logger.info(f"Model loaded successfully. Test predictions: {test_pred}")
    
    logger.info("Training completed successfully!")
    
    return metrics


if __name__ == "__main__":
    metrics = main()