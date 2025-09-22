"""
Eligibility assessment ML module for the Blessings Donation System.

This module provides ML-powered eligibility scoring for ration distribution
based on employee data and trained models.
"""

import os
import numpy as np
import pandas as pd
import joblib
from typing import Dict, List, Optional, Tuple
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class EligibilityPredictor:
    """ML-powered eligibility assessment for ration distribution."""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.encoders = {}
        self.feature_names = []
        self.metrics = {}
        self.model_loaded = False
        
        # Load model on initialization
        self._load_model()
    
    def _load_model(self):
        """Load the trained eligibility model."""
        try:
            model_path = settings.eligibility_model_path
            
            if not os.path.exists(model_path):
                logger.warning("Eligibility model not found", path=model_path)
                return False
            
            # Load model data
            model_data = joblib.load(model_path)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.encoders = model_data['encoders']
            self.feature_names = model_data['feature_names']
            self.metrics = model_data['metrics']
            
            self.model_loaded = True
            
            logger.info(
                "Eligibility model loaded successfully",
                model_type=self.metrics.get('model_name', 'unknown'),
                auc_score=self.metrics.get('test_auc', 'unknown'),
                created_at=model_data.get('created_at', 'unknown')
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to load eligibility model", error=str(e))
            return False
    
    def predict_eligibility(self, employee_data: Dict) -> Dict[str, any]:
        """
        Predict eligibility for a single employee.
        
        Args:
            employee_data: Dictionary containing employee information
            
        Returns:
            Dict containing prediction results
        """
        if not self.model_loaded:
            return {
                'eligible': False,
                'probability': 0.0,
                'confidence': 0.0,
                'error': 'Model not loaded'
            }
        
        try:
            # Prepare features
            features = self._prepare_features([employee_data])
            
            if features is None:
                return {
                    'eligible': False,
                    'probability': 0.0,
                    'confidence': 0.0,
                    'error': 'Feature preparation failed'
                }
            
            # Make prediction
            probabilities = self.model.predict_proba(features)
            probability = probabilities[0][1]  # Probability of being eligible
            
            # Determine eligibility
            threshold = settings.model_confidence_threshold
            eligible = probability >= threshold
            
            # Calculate confidence (distance from threshold)
            confidence = abs(probability - 0.5) * 2  # 0 to 1 scale
            
            result = {
                'eligible': bool(eligible),
                'probability': float(probability),
                'confidence': float(confidence),
                'threshold': threshold,
                'features_used': len(self.feature_names)
            }
            
            logger.debug(
                "Eligibility prediction completed",
                employee_id=employee_data.get('employee_id', 'unknown'),
                eligible=eligible,
                probability=probability
            )
            
            return result
            
        except Exception as e:
            logger.error("Eligibility prediction failed", error=str(e))
            return {
                'eligible': False,
                'probability': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def predict_batch_eligibility(self, employees_data: List[Dict]) -> List[Dict]:
        """
        Predict eligibility for multiple employees.
        
        Args:
            employees_data: List of employee dictionaries
            
        Returns:
            List of prediction results
        """
        if not self.model_loaded:
            error_result = {
                'eligible': False,
                'probability': 0.0,
                'confidence': 0.0,
                'error': 'Model not loaded'
            }
            return [error_result] * len(employees_data)
        
        try:
            # Prepare features for all employees
            features = self._prepare_features(employees_data)
            
            if features is None:
                error_result = {
                    'eligible': False,
                    'probability': 0.0,
                    'confidence': 0.0,
                    'error': 'Feature preparation failed'
                }
                return [error_result] * len(employees_data)
            
            # Make batch predictions
            probabilities = self.model.predict_proba(features)[:, 1]
            
            # Process results
            threshold = settings.model_confidence_threshold
            results = []
            
            for i, probability in enumerate(probabilities):
                eligible = probability >= threshold
                confidence = abs(probability - 0.5) * 2
                
                result = {
                    'eligible': bool(eligible),
                    'probability': float(probability),
                    'confidence': float(confidence),
                    'threshold': threshold,
                    'employee_id': employees_data[i].get('employee_id', f'emp_{i}')
                }
                results.append(result)
            
            logger.info(
                "Batch eligibility prediction completed",
                total_employees=len(employees_data),
                eligible_count=sum(1 for r in results if r['eligible'])
            )
            
            return results
            
        except Exception as e:
            logger.error("Batch eligibility prediction failed", error=str(e))
            error_result = {
                'eligible': False,
                'probability': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }
            return [error_result] * len(employees_data)
    
    def _prepare_features(self, employees_data: List[Dict]) -> Optional[np.ndarray]:
        """
        Prepare features for ML model prediction.
        
        Args:
            employees_data: List of employee dictionaries
            
        Returns:
            Prepared feature matrix or None if preparation fails
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(employees_data)
            
            # Add default values for missing columns
            required_columns = [
                'grade', 'family_size', 'income_estimate', 'previous_aid_count',
                'dependents', 'employment_status', 'years_of_service',
                'medical_expenses', 'housing_status', 'education_expenses'
            ]
            
            for col in required_columns:
                if col not in df.columns:
                    # Set default values based on column type
                    if col == 'grade':
                        df[col] = 15  # Average grade
                    elif col == 'family_size':
                        df[col] = 4   # Average family size
                    elif col == 'income_estimate':
                        df[col] = 40000  # Average income
                    elif col == 'previous_aid_count':
                        df[col] = 1   # Average previous aid
                    elif col == 'dependents':
                        df[col] = 2   # Average dependents
                    elif col == 'employment_status':
                        df[col] = 'permanent'  # Default status
                    elif col == 'years_of_service':
                        df[col] = 5   # Average years
                    elif col == 'medical_expenses':
                        df[col] = 2000  # Average medical expenses
                    elif col == 'housing_status':
                        df[col] = 'rented'  # Default housing
                    elif col == 'education_expenses':
                        df[col] = 3000  # Average education expenses
            
            # Encode categorical variables using saved encoders
            if 'employment_status' in self.encoders:
                # Handle unknown categories
                valid_categories = self.encoders['employment_status'].classes_
                df['employment_status'] = df['employment_status'].apply(
                    lambda x: x if x in valid_categories else valid_categories[0]
                )
                df['employment_status_encoded'] = self.encoders['employment_status'].transform(
                    df['employment_status']
                )
            else:
                # Fallback encoding
                status_map = {'permanent': 0, 'contract': 1, 'temporary': 2}
                df['employment_status_encoded'] = df['employment_status'].map(status_map).fillna(0)
            
            if 'housing_status' in self.encoders:
                valid_categories = self.encoders['housing_status'].classes_
                df['housing_status'] = df['housing_status'].apply(
                    lambda x: x if x in valid_categories else valid_categories[0]
                )
                df['housing_status_encoded'] = self.encoders['housing_status'].transform(
                    df['housing_status']
                )
            else:
                # Fallback encoding
                housing_map = {'owned': 0, 'rented': 1, 'family': 2}
                df['housing_status_encoded'] = df['housing_status'].map(housing_map).fillna(1)
            
            # Create derived features (same as training)
            df['income_per_member'] = df['income_estimate'] / df['family_size']
            df['expense_ratio'] = (df['medical_expenses'] + df['education_expenses']) / df['income_estimate']
            df['grade_family_interaction'] = df['grade'] * df['family_size']
            df['aid_frequency'] = df['previous_aid_count'] / np.maximum(df['years_of_service'], 1)
            
            # Select features in the same order as training
            feature_data = df[self.feature_names].values
            
            # Scale features
            scaled_features = self.scaler.transform(feature_data)
            
            return scaled_features
            
        except Exception as e:
            logger.error("Feature preparation failed", error=str(e))
            return None
    
    def get_feature_importance(self) -> Optional[List[Dict]]:
        """
        Get feature importance from the trained model.
        
        Returns:
            List of feature importance dictionaries or None
        """
        if not self.model_loaded or not hasattr(self.model, 'feature_importances_'):
            return None
        
        try:
            importance_data = []
            
            for i, importance in enumerate(self.model.feature_importances_):
                importance_data.append({
                    'feature': self.feature_names[i],
                    'importance': float(importance),
                    'rank': i + 1
                })
            
            # Sort by importance
            importance_data.sort(key=lambda x: x['importance'], reverse=True)
            
            # Update ranks
            for i, item in enumerate(importance_data):
                item['rank'] = i + 1
            
            return importance_data
            
        except Exception as e:
            logger.error("Failed to get feature importance", error=str(e))
            return None
    
    def get_model_info(self) -> Dict[str, any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary containing model information
        """
        if not self.model_loaded:
            return {
                'loaded': False,
                'error': 'Model not loaded'
            }
        
        return {
            'loaded': True,
            'model_type': self.metrics.get('model_name', 'unknown'),
            'auc_score': self.metrics.get('test_auc', 'unknown'),
            'cv_score': self.metrics.get('cv_score', 'unknown'),
            'feature_count': len(self.feature_names),
            'threshold': settings.model_confidence_threshold,
            'created_at': self.metrics.get('created_at', 'unknown')
        }
    
    def is_model_loaded(self) -> bool:
        """Check if the model is loaded and ready for predictions."""
        return self.model_loaded


# Global instance for use throughout the application
eligibility_predictor = EligibilityPredictor()