"""
Machine Learning Service for eligibility and fraud detection
"""

import os
import joblib
import numpy as np
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class MLService:
    """Service for ML model inference"""
    
    def __init__(self):
        """Initialize ML service and load models"""
        self.eligibility_model = None
        self.fraud_model = None
        self.models_loaded = False
        self._load_models()
    
    def _load_models(self):
        """Load trained ML models"""
        try:
            model_dir = Path("/app/app/ml/models")
            
            # Load eligibility model
            eligibility_path = model_dir / "eligibility_model.joblib"
            if eligibility_path.exists():
                self.eligibility_model = joblib.load(eligibility_path)
                logger.info("Eligibility model loaded successfully")
            else:
                logger.warning(f"Eligibility model not found at {eligibility_path}")
            
            # Load fraud detection model  
            fraud_path = model_dir / "fraud_model.joblib"
            if fraud_path.exists():
                self.fraud_model = joblib.load(fraud_path)
                logger.info("Fraud detection model loaded successfully")
            else:
                logger.warning(f"Fraud model not found at {fraud_path}")
            
            self.models_loaded = (self.eligibility_model is not None and 
                                 self.fraud_model is not None)
            
        except Exception as e:
            logger.error(f"Error loading ML models: {e}")
            self.models_loaded = False
    
    async def check_eligibility(self, employee: Any) -> Dict[str, Any]:
        """
        Check employee eligibility using ML model
        
        Args:
            employee: Employee object with required attributes
            
        Returns:
            Dictionary with eligibility score and decision
        """
        try:
            # Extract features
            features = self._extract_eligibility_features(employee)
            
            if self.eligibility_model and self.models_loaded:
                # Use trained model
                X = np.array(features).reshape(1, -1)
                
                # Get prediction and probability
                prediction = self.eligibility_model.predict(X)[0]
                probability = self.eligibility_model.predict_proba(X)[0]
                
                eligibility_score = float(probability[1])  # Probability of being eligible
                
            else:
                # Fallback to rule-based scoring
                eligibility_score = self._calculate_rule_based_eligibility(employee)
                prediction = 1 if eligibility_score >= 0.5 else 0
            
            # Determine eligibility with reasons
            reasons = self._get_eligibility_reasons(employee, eligibility_score)
            
            return {
                "eligible": bool(prediction),
                "score": round(eligibility_score, 3),
                "reasons": reasons,
                "model_used": "ml" if self.models_loaded else "rule_based"
            }
            
        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            return {
                "eligible": True,
                "score": 0.5,
                "reasons": ["Error in eligibility check - defaulting to neutral"],
                "model_used": "error"
            }
    
    async def detect_fraud(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential fraud using ML model
        
        Args:
            data: Dictionary with transaction/beneficiary data
            
        Returns:
            Dictionary with fraud flag and score
        """
        try:
            # Extract features
            features = self._extract_fraud_features(data)
            
            if self.fraud_model and self.models_loaded:
                # Use trained model
                X = np.array(features).reshape(1, -1)
                
                # Get anomaly score
                anomaly_score = self.fraud_model.decision_function(X)[0]
                prediction = self.fraud_model.predict(X)[0]
                
                # Convert to probability-like score (0-1)
                # IsolationForest: negative scores are anomalies
                fraud_score = 1 / (1 + np.exp(anomaly_score))  # Sigmoid transformation
                is_fraud = prediction == -1  # -1 indicates anomaly
                
            else:
                # Fallback to rule-based detection
                fraud_score = self._calculate_rule_based_fraud(data)
                is_fraud = fraud_score > 0.7
            
            return {
                "is_fraud": is_fraud,
                "fraud_score": round(fraud_score, 3),
                "risk_level": self._get_risk_level(fraud_score),
                "model_used": "ml" if self.models_loaded else "rule_based"
            }
            
        except Exception as e:
            logger.error(f"Error detecting fraud: {e}")
            return {
                "is_fraud": False,
                "fraud_score": 0.0,
                "risk_level": "low",
                "model_used": "error"
            }
    
    def _extract_eligibility_features(self, employee: Any) -> List[float]:
        """
        Extract features for eligibility model
        
        Features:
        - grade (normalized)
        - family_size
        - income_estimate (normalized)
        - previous_aid_count
        - days_since_last_distribution
        """
        grade_normalized = (employee.grade - 1) / 21.0  # Normalize 1-22 to 0-1
        family_size = float(employee.family_size)
        income_normalized = min(employee.income_estimate / 100000.0, 1.0) if employee.income_estimate else 0.5
        previous_aid = float(employee.previous_aid_count) if employee.previous_aid_count else 0.0
        
        # Days since last distribution
        days_since = 365  # Default to 1 year
        if hasattr(employee, 'last_distribution_date') and employee.last_distribution_date:
            from datetime import datetime
            days_since = (datetime.now() - employee.last_distribution_date).days
        
        days_normalized = min(days_since / 365.0, 1.0)
        
        return [
            grade_normalized,
            family_size,
            income_normalized,
            previous_aid,
            days_normalized
        ]
    
    def _extract_fraud_features(self, data: Dict[str, Any]) -> List[float]:
        """
        Extract features for fraud detection model
        
        Features vary based on context (donation vs beneficiary)
        """
        features = []
        
        if 'amount' in data:  # Donation fraud
            features.extend([
                data.get('amount', 0) / 100000.0,  # Normalized amount
                1.0 if data.get('is_anonymous', False) else 0.0,
                data.get('frequency', 1) / 10.0,  # Normalized frequency
                1.0 if data.get('unusual_time', False) else 0.0,
            ])
        else:  # Beneficiary fraud
            features.extend([
                data.get('grade', 10) / 22.0,
                data.get('family_size', 4) / 10.0,
                data.get('previous_aid_count', 0) / 5.0,
                1.0 if data.get('duplicate_family', False) else 0.0,
            ])
        
        # Pad with zeros if needed
        while len(features) < 4:
            features.append(0.0)
        
        return features[:4]  # Ensure consistent feature count
    
    def _calculate_rule_based_eligibility(self, employee: Any) -> float:
        """
        Calculate eligibility using rule-based approach
        
        Args:
            employee: Employee object
            
        Returns:
            Eligibility score between 0 and 1
        """
        score = 0.5  # Base score
        
        # Grade-based scoring (lower grades get higher scores)
        if employee.grade <= 5:
            score += 0.3
        elif employee.grade <= 10:
            score += 0.2
        elif employee.grade <= 15:
            score += 0.1
        else:
            score -= 0.1
        
        # Family size impact
        if employee.family_size >= 5:
            score += 0.15
        elif employee.family_size >= 3:
            score += 0.1
        
        # Income consideration
        if hasattr(employee, 'income_estimate') and employee.income_estimate:
            if employee.income_estimate < 30000:
                score += 0.2
            elif employee.income_estimate < 50000:
                score += 0.1
            elif employee.income_estimate > 100000:
                score -= 0.2
        
        # Previous aid consideration
        if employee.previous_aid_count and employee.previous_aid_count > 3:
            score -= 0.15
        
        return max(0.0, min(1.0, score))  # Clamp to [0, 1]
    
    def _calculate_rule_based_fraud(self, data: Dict[str, Any]) -> float:
        """
        Calculate fraud score using rules
        
        Args:
            data: Transaction/beneficiary data
            
        Returns:
            Fraud score between 0 and 1
        """
        score = 0.0
        
        # Check for suspicious patterns
        if data.get('duplicate_family'):
            score += 0.4
        
        if data.get('unusual_pattern'):
            score += 0.3
        
        if data.get('high_frequency'):
            score += 0.2
        
        if data.get('mismatched_info'):
            score += 0.3
        
        return min(1.0, score)
    
    def _get_eligibility_reasons(self, employee: Any, score: float) -> List[str]:
        """
        Generate human-readable eligibility reasons
        
        Args:
            employee: Employee object
            score: Eligibility score
            
        Returns:
            List of reason strings
        """
        reasons = []
        
        if score >= 0.7:
            reasons.append("High eligibility score")
            if employee.grade <= 10:
                reasons.append("Low grade level indicates higher need")
            if employee.family_size >= 5:
                reasons.append("Large family size")
        elif score >= 0.5:
            reasons.append("Moderate eligibility score")
        else:
            reasons.append("Low eligibility score")
            if employee.grade > 15:
                reasons.append("Higher grade level")
            if employee.previous_aid_count > 3:
                reasons.append("Received aid multiple times recently")
        
        return reasons
    
    def _get_risk_level(self, fraud_score: float) -> str:
        """
        Determine risk level from fraud score
        
        Args:
            fraud_score: Fraud score between 0 and 1
            
        Returns:
            Risk level string
        """
        if fraud_score >= 0.8:
            return "high"
        elif fraud_score >= 0.5:
            return "medium"
        else:
            return "low"