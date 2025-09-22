"""
Fraud detection ML module for the Blessings Donation System.

This module provides ML-powered fraud detection for donations using
anomaly detection and pattern recognition techniques.
"""

import os
import numpy as np
import pandas as pd
import joblib
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class FraudDetector:
    """ML-powered fraud detection for donations."""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.metrics = {}
        self.model_loaded = False
        
        # Load model on initialization
        self._load_model()
    
    def _load_model(self):
        """Load the trained fraud detection model."""
        try:
            model_path = settings.fraud_model_path
            
            if not os.path.exists(model_path):
                logger.warning("Fraud detection model not found", path=model_path)
                return False
            
            # Load model data
            model_data = joblib.load(model_path)
            
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.metrics = model_data['metrics']
            
            self.model_loaded = True
            
            logger.info(
                "Fraud detection model loaded successfully",
                model_type=self.metrics.get('model_type', 'unknown'),
                f1_score=self.metrics.get('f1_score', 'unknown'),
                created_at=model_data.get('created_at', 'unknown')
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to load fraud detection model", error=str(e))
            return False
    
    def predict_fraud(self, donation_data: Dict) -> Dict[str, any]:
        """
        Predict fraud probability for a single donation.
        
        Args:
            donation_data: Dictionary containing donation information
            
        Returns:
            Dict containing fraud prediction results
        """
        if not self.model_loaded:
            return {
                'is_fraud': False,
                'fraud_probability': 0.0,
                'risk_level': 'unknown',
                'confidence': 0.0,
                'error': 'Model not loaded'
            }
        
        try:
            # Prepare features
            features = self._prepare_features([donation_data])
            
            if features is None:
                return {
                    'is_fraud': False,
                    'fraud_probability': 0.0,
                    'risk_level': 'unknown',
                    'confidence': 0.0,
                    'error': 'Feature preparation failed'
                }
            
            # Get anomaly score
            anomaly_score = self.model.decision_function(features)[0]
            
            # Convert to fraud probability
            fraud_probability = self._anomaly_score_to_probability(anomaly_score)
            
            # Determine fraud prediction
            threshold = settings.fraud_detection_threshold
            is_fraud = fraud_probability >= threshold
            
            # Determine risk level
            risk_level = self._get_risk_level(fraud_probability)
            
            # Calculate confidence
            confidence = abs(fraud_probability - 0.5) * 2
            
            result = {
                'is_fraud': bool(is_fraud),
                'fraud_probability': float(fraud_probability),
                'risk_level': risk_level,
                'confidence': float(confidence),
                'anomaly_score': float(anomaly_score),
                'threshold': threshold
            }
            
            logger.debug(
                "Fraud prediction completed",
                donation_id=donation_data.get('donation_id', 'unknown'),
                is_fraud=is_fraud,
                fraud_probability=fraud_probability,
                risk_level=risk_level
            )
            
            return result
            
        except Exception as e:
            logger.error("Fraud prediction failed", error=str(e))
            return {
                'is_fraud': False,
                'fraud_probability': 0.0,
                'risk_level': 'unknown',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def predict_batch_fraud(self, donations_data: List[Dict]) -> List[Dict]:
        """
        Predict fraud probability for multiple donations.
        
        Args:
            donations_data: List of donation dictionaries
            
        Returns:
            List of fraud prediction results
        """
        if not self.model_loaded:
            error_result = {
                'is_fraud': False,
                'fraud_probability': 0.0,
                'risk_level': 'unknown',
                'confidence': 0.0,
                'error': 'Model not loaded'
            }
            return [error_result] * len(donations_data)
        
        try:
            # Prepare features for all donations
            features = self._prepare_features(donations_data)
            
            if features is None:
                error_result = {
                    'is_fraud': False,
                    'fraud_probability': 0.0,
                    'risk_level': 'unknown',
                    'confidence': 0.0,
                    'error': 'Feature preparation failed'
                }
                return [error_result] * len(donations_data)
            
            # Get anomaly scores
            anomaly_scores = self.model.decision_function(features)
            
            # Convert to fraud probabilities
            fraud_probabilities = [
                self._anomaly_score_to_probability(score) 
                for score in anomaly_scores
            ]
            
            # Process results
            threshold = settings.fraud_detection_threshold
            results = []
            
            for i, fraud_probability in enumerate(fraud_probabilities):
                is_fraud = fraud_probability >= threshold
                risk_level = self._get_risk_level(fraud_probability)
                confidence = abs(fraud_probability - 0.5) * 2
                
                result = {
                    'is_fraud': bool(is_fraud),
                    'fraud_probability': float(fraud_probability),
                    'risk_level': risk_level,
                    'confidence': float(confidence),
                    'anomaly_score': float(anomaly_scores[i]),
                    'donation_id': donations_data[i].get('donation_id', f'don_{i}')
                }
                results.append(result)
            
            logger.info(
                "Batch fraud prediction completed",
                total_donations=len(donations_data),
                fraud_detected=sum(1 for r in results if r['is_fraud']),
                high_risk=sum(1 for r in results if r['risk_level'] == 'high')
            )
            
            return results
            
        except Exception as e:
            logger.error("Batch fraud prediction failed", error=str(e))
            error_result = {
                'is_fraud': False,
                'fraud_probability': 0.0,
                'risk_level': 'unknown',
                'confidence': 0.0,
                'error': str(e)
            }
            return [error_result] * len(donations_data)
    
    def _prepare_features(self, donations_data: List[Dict]) -> Optional[np.ndarray]:
        """
        Prepare features for ML model prediction.
        
        Args:
            donations_data: List of donation dictionaries
            
        Returns:
            Prepared feature matrix or None if preparation fails
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(donations_data)
            
            # Add default values for missing columns
            current_time = datetime.utcnow()
            
            # Basic donation fields
            if 'amount' not in df.columns:
                df['amount'] = 1000.0  # Default amount
            if 'donor_age' not in df.columns:
                df['donor_age'] = 35   # Default age
            if 'created_at' not in df.columns:
                df['created_at'] = current_time
            
            # Extract time-based features
            if df['created_at'].dtype == 'object':
                df['created_at'] = pd.to_datetime(df['created_at'])
            
            df['hour_of_day'] = df['created_at'].dt.hour
            df['day_of_week'] = df['created_at'].dt.dayofweek
            
            # Contact information
            df['has_email'] = df.get('donor_email', '').notna().astype(int)
            df['has_phone'] = df.get('donor_phone', '').notna().astype(int)
            df['cnic_provided'] = df.get('donor_cnic', '').notna().astype(int)
            
            # Amount-based features
            df['amount_is_round'] = (df['amount'] % 100 == 0).astype(int)
            df['amount_is_very_round'] = (df['amount'] % 1000 == 0).astype(int)
            
            # Default values for other features
            if 'submission_speed' not in df.columns:
                df['submission_speed'] = 120  # Default 2 minutes
            if 'repeat_donor' not in df.columns:
                df['repeat_donor'] = 0  # Default new donor
            
            # City encoding (simplified)
            major_cities = ['karachi', 'lahore', 'islamabad', 'rawalpindi']
            city_col = df.get('city', '').str.lower().fillna('other')
            
            for city in major_cities:
                df[f'city_{city}'] = (city_col == city).astype(int)
            
            # Payment method encoding
            payment_methods = ['bank_transfer', 'cash', 'online', 'mobile_wallet']
            payment_col = df.get('payment_method', 'cash').fillna('cash')
            
            for method in payment_methods:
                df[f'payment_{method}'] = (payment_col == method).astype(int)
            
            # Donation type encoding
            donation_types = ['zakat', 'sadaqah', 'general']
            type_col = df.get('donation_type', 'general').fillna('general')
            
            for dtype in donation_types:
                df[f'type_{dtype}'] = (type_col == dtype).astype(int)
            
            # Create derived features
            df['amount_log'] = np.log1p(df['amount'])
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            df['is_night'] = ((df['hour_of_day'] >= 22) | (df['hour_of_day'] <= 5)).astype(int)
            df['is_business_hours'] = ((df['hour_of_day'] >= 9) & (df['hour_of_day'] <= 17)).astype(int)
            df['submission_speed_log'] = np.log1p(df['submission_speed'])
            df['contact_completeness'] = df['has_email'] + df['has_phone'] + df['cnic_provided']
            
            # Amount category
            df['amount_category'] = pd.cut(df['amount'], 
                                         bins=[0, 500, 2000, 10000, float('inf')], 
                                         labels=[0, 1, 2, 3]).astype(int)
            
            # Select features in the same order as training
            try:
                feature_data = df[self.feature_names].values
            except KeyError as e:
                logger.warning("Missing features, using available ones", missing=str(e))
                # Use only available features
                available_features = [f for f in self.feature_names if f in df.columns]
                feature_data = df[available_features].values
                
                # Pad with zeros for missing features
                if len(available_features) < len(self.feature_names):
                    padding = np.zeros((len(df), len(self.feature_names) - len(available_features)))
                    feature_data = np.hstack([feature_data, padding])
            
            # Scale features
            scaled_features = self.scaler.transform(feature_data)
            
            return scaled_features
            
        except Exception as e:
            logger.error("Feature preparation failed", error=str(e))
            return None
    
    def _anomaly_score_to_probability(self, anomaly_score: float) -> float:
        """
        Convert anomaly score to fraud probability.
        
        Args:
            anomaly_score: Raw anomaly score from Isolation Forest
            
        Returns:
            Fraud probability between 0 and 1
        """
        # Sigmoid transformation to convert to probability
        # More negative scores = higher fraud probability
        probability = 1 / (1 + np.exp(anomaly_score))
        return float(np.clip(probability, 0.0, 1.0))
    
    def _get_risk_level(self, fraud_probability: float) -> str:
        """
        Determine risk level based on fraud probability.
        
        Args:
            fraud_probability: Fraud probability between 0 and 1
            
        Returns:
            Risk level string
        """
        if fraud_probability >= 0.7:
            return 'high'
        elif fraud_probability >= 0.4:
            return 'medium'
        elif fraud_probability >= 0.2:
            return 'low'
        else:
            return 'very_low'
    
    def get_fraud_indicators(self, donation_data: Dict) -> List[Dict]:
        """
        Get specific fraud indicators for a donation.
        
        Args:
            donation_data: Donation data dictionary
            
        Returns:
            List of fraud indicator dictionaries
        """
        indicators = []
        
        try:
            # Check amount patterns
            amount = donation_data.get('amount', 0)
            if amount % 1000 == 0 and amount >= 10000:
                indicators.append({
                    'type': 'suspicious_amount',
                    'description': 'Very round, large amount',
                    'severity': 'medium',
                    'value': amount
                })
            
            # Check timing patterns
            created_at = donation_data.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    created_at = pd.to_datetime(created_at)
                
                hour = created_at.hour
                if hour <= 5 or hour >= 23:
                    indicators.append({
                        'type': 'unusual_timing',
                        'description': 'Donation made during unusual hours',
                        'severity': 'low',
                        'value': f"{hour:02d}:00"
                    })
            
            # Check contact information
            has_email = bool(donation_data.get('donor_email'))
            has_phone = bool(donation_data.get('donor_phone'))
            has_cnic = bool(donation_data.get('donor_cnic'))
            
            contact_count = sum([has_email, has_phone, has_cnic])
            if contact_count <= 1:
                indicators.append({
                    'type': 'incomplete_contact',
                    'description': 'Insufficient contact information provided',
                    'severity': 'medium',
                    'value': contact_count
                })
            
            # Check for rapid submission
            submission_speed = donation_data.get('submission_speed', 120)
            if submission_speed < 30:
                indicators.append({
                    'type': 'rapid_submission',
                    'description': 'Form submitted too quickly',
                    'severity': 'high',
                    'value': f"{submission_speed}s"
                })
            
            # Check email patterns
            email = donation_data.get('donor_email', '')
            if email:
                temp_domains = ['10minutemail.com', 'guerrillamail.com', 'tempmail.org']
                domain = email.split('@')[-1].lower()
                if domain in temp_domains:
                    indicators.append({
                        'type': 'temporary_email',
                        'description': 'Temporary email address used',
                        'severity': 'high',
                        'value': domain
                    })
            
            return indicators
            
        except Exception as e:
            logger.error("Failed to get fraud indicators", error=str(e))
            return []
    
    def get_model_info(self) -> Dict[str, any]:
        """
        Get information about the loaded fraud detection model.
        
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
            'model_type': self.metrics.get('model_type', 'unknown'),
            'f1_score': self.metrics.get('f1_score', 'unknown'),
            'precision': self.metrics.get('precision', 'unknown'),
            'recall': self.metrics.get('recall', 'unknown'),
            'feature_count': len(self.feature_names),
            'threshold': settings.fraud_detection_threshold,
            'contamination_rate': self.metrics.get('contamination_rate', 'unknown'),
            'created_at': self.metrics.get('created_at', 'unknown')
        }
    
    def is_model_loaded(self) -> bool:
        """Check if the fraud detection model is loaded and ready."""
        return self.model_loaded


# Global instance for use throughout the application
fraud_detector = FraudDetector()