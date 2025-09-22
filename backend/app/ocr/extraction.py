"""
Text and amount extraction utilities for OCR in the Blessings Donation System.

This module provides functions to extract currency amounts and relevant information
from OCR text using pattern matching and natural language processing.
"""

import re
from typing import List, Dict, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class AmountExtractor:
    """Utility class for extracting currency amounts from OCR text."""
    
    def __init__(self):
        # Currency patterns for Pakistani Rupees
        self.currency_patterns = [
            # Rs 1,000 or Rs1000 or Rs. 1000
            r'(?:Rs\.?\s*|₨\s*)([0-9,]+(?:\.[0-9]{2})?)',
            # PKR 1000 or PKR1000
            r'(?:PKR\s*)([0-9,]+(?:\.[0-9]{2})?)',
            # Amount: 1000 or Total: 1000
            r'(?:Amount|Total|Sum):\s*(?:Rs\.?\s*|₨\s*|PKR\s*)?([0-9,]+(?:\.[0-9]{2})?)',
            # Standalone numbers that might be amounts
            r'\b([0-9]{3,}(?:,[0-9]{3})*(?:\.[0-9]{2})?)\b',
            # Numbers with decimal points
            r'\b([0-9,]+\.[0-9]{2})\b',
        ]
        
        # Common words that indicate amounts
        self.amount_keywords = [
            'amount', 'total', 'sum', 'paid', 'payment', 'balance',
            'rupees', 'rs', 'pkr', 'cash', 'deposit'
        ]
        
        # Date patterns to exclude from amount detection
        self.date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{2,4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
        ]
    
    def extract_amounts(self, text: str) -> List[Dict[str, any]]:
        """
        Extract all potential currency amounts from text.
        
        Args:
            text: OCR extracted text
            
        Returns:
            List of dictionaries containing amount info
        """
        try:
            amounts = []
            text_lower = text.lower()
            
            # Remove dates to avoid false positives
            cleaned_text = self._remove_dates(text)
            
            # Try each currency pattern
            for i, pattern in enumerate(self.currency_patterns):
                matches = re.finditer(pattern, cleaned_text, re.IGNORECASE)
                
                for match in matches:
                    amount_str = match.group(1)
                    amount_value = self._parse_amount(amount_str)
                    
                    if amount_value and self._is_valid_amount(amount_value):
                        # Calculate confidence based on pattern and context
                        confidence = self._calculate_confidence(
                            match, text_lower, i, amount_value
                        )
                        
                        amounts.append({
                            'amount': amount_value,
                            'raw_text': match.group(0),
                            'confidence': confidence,
                            'pattern_index': i,
                            'position': match.start(),
                            'context': self._get_context(text, match.start(), match.end())
                        })
            
            # Sort by confidence and remove duplicates
            amounts = self._deduplicate_amounts(amounts)
            amounts.sort(key=lambda x: x['confidence'], reverse=True)
            
            logger.info(f"Extracted {len(amounts)} potential amounts from text")
            return amounts
            
        except Exception as e:
            logger.error("Amount extraction failed", error=str(e))
            return []
    
    def get_best_amount(self, text: str) -> Tuple[Optional[float], float]:
        """
        Get the most likely amount from text.
        
        Args:
            text: OCR extracted text
            
        Returns:
            Tuple of (amount, confidence)
        """
        amounts = self.extract_amounts(text)
        
        if not amounts:
            return None, 0.0
        
        # Return the highest confidence amount
        best = amounts[0]
        return best['amount'], best['confidence']
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string to float value."""
        try:
            # Remove commas and spaces
            cleaned = amount_str.replace(',', '').replace(' ', '')
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _is_valid_amount(self, amount: float) -> bool:
        """Check if amount is within reasonable range for donations."""
        # Reasonable range for donations: 10 PKR to 10,000,000 PKR
        return 10 <= amount <= 10_000_000
    
    def _calculate_confidence(
        self, 
        match: re.Match, 
        text_lower: str, 
        pattern_index: int, 
        amount_value: float
    ) -> float:
        """Calculate confidence score for extracted amount."""
        confidence = 0.5  # Base confidence
        
        # Pattern-based confidence
        pattern_scores = [0.9, 0.8, 0.7, 0.4, 0.3]  # Scores for each pattern
        if pattern_index < len(pattern_scores):
            confidence = pattern_scores[pattern_index]
        
        # Context-based confidence boost
        context_window = 50
        start_pos = max(0, match.start() - context_window)
        end_pos = min(len(text_lower), match.end() + context_window)
        context = text_lower[start_pos:end_pos]
        
        # Boost confidence if amount keywords are nearby
        for keyword in self.amount_keywords:
            if keyword in context:
                confidence += 0.1
                break
        
        # Boost for receipt-related words
        receipt_words = ['receipt', 'invoice', 'bill', 'payment', 'transaction']
        for word in receipt_words:
            if word in context:
                confidence += 0.05
                break
        
        # Reduce confidence for very round numbers (might be fake)
        if amount_value % 1000 == 0 and amount_value >= 10000:
            confidence -= 0.1
        
        # Boost confidence for common donation amounts
        common_amounts = [100, 500, 1000, 2000, 5000, 10000]
        if amount_value in common_amounts:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _get_context(self, text: str, start: int, end: int, window: int = 30) -> str:
        """Get context around the matched amount."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def _remove_dates(self, text: str) -> str:
        """Remove date patterns from text to avoid false positives."""
        cleaned = text
        for pattern in self.date_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        return cleaned
    
    def _deduplicate_amounts(self, amounts: List[Dict]) -> List[Dict]:
        """Remove duplicate amounts based on value and position."""
        if not amounts:
            return []
        
        unique_amounts = []
        seen_amounts = set()
        
        for amount in amounts:
            # Create a key based on amount value and approximate position
            key = (amount['amount'], amount['position'] // 10)  # Group by position within 10 chars
            
            if key not in seen_amounts:
                seen_amounts.add(key)
                unique_amounts.append(amount)
        
        return unique_amounts


class TextCleaner:
    """Utility class for cleaning and normalizing OCR text."""
    
    def __init__(self):
        # Common OCR errors and their corrections
        self.ocr_corrections = {
            'O': '0',  # Letter O mistaken for zero
            'l': '1',  # Lowercase L mistaken for one
            'I': '1',  # Uppercase I mistaken for one
            'S': '5',  # S mistaken for 5 in certain contexts
            'Z': '2',  # Z mistaken for 2
            'G': '6',  # G mistaken for 6
            'B': '8',  # B mistaken for 8
        }
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize OCR text.
        
        Args:
            text: Raw OCR text
            
        Returns:
            str: Cleaned text
        """
        try:
            # Remove extra whitespace
            cleaned = re.sub(r'\s+', ' ', text.strip())
            
            # Fix common OCR errors in numeric contexts
            cleaned = self._fix_numeric_errors(cleaned)
            
            # Normalize currency symbols
            cleaned = self._normalize_currency_symbols(cleaned)
            
            # Remove non-printable characters
            cleaned = ''.join(char for char in cleaned if char.isprintable())
            
            return cleaned
            
        except Exception as e:
            logger.error("Text cleaning failed", error=str(e))
            return text
    
    def _fix_numeric_errors(self, text: str) -> str:
        """Fix common OCR errors in numeric contexts."""
        # Pattern to find potential numeric strings
        numeric_pattern = r'\b[A-Za-z0-9,.-]+\b'
        
        def fix_numeric_match(match):
            word = match.group()
            # Only fix if the word contains digits and is likely a number
            if any(c.isdigit() for c in word) and len(word) <= 10:
                fixed = word
                for wrong, correct in self.ocr_corrections.items():
                    # Only replace if it makes sense in numeric context
                    if wrong in fixed and any(c.isdigit() for c in fixed):
                        fixed = fixed.replace(wrong, correct)
                return fixed
            return word
        
        return re.sub(numeric_pattern, fix_numeric_match, text)
    
    def _normalize_currency_symbols(self, text: str) -> str:
        """Normalize different currency symbol representations."""
        # Replace various Rs representations with standard Rs
        text = re.sub(r'Rs\.?|RS\.?|rs\.?', 'Rs', text)
        
        # Normalize PKR
        text = re.sub(r'pkr|PKr|pKR', 'PKR', text)
        
        return text


class ReceiptAnalyzer:
    """Analyzer for receipt-specific information."""
    
    def __init__(self):
        self.amount_extractor = AmountExtractor()
        self.text_cleaner = TextCleaner()
    
    def analyze_receipt(self, text: str) -> Dict[str, any]:
        """
        Analyze receipt text and extract relevant information.
        
        Args:
            text: OCR extracted text
            
        Returns:
            Dict containing analysis results
        """
        try:
            # Clean the text
            cleaned_text = self.text_cleaner.clean_text(text)
            
            # Extract amounts
            amounts = self.amount_extractor.extract_amounts(cleaned_text)
            best_amount, confidence = self.amount_extractor.get_best_amount(cleaned_text)
            
            # Detect receipt type
            receipt_type = self._detect_receipt_type(cleaned_text)
            
            # Extract date if possible
            date_info = self._extract_date(cleaned_text)
            
            # Detect bank or payment method
            payment_info = self._detect_payment_method(cleaned_text)
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(
                confidence, receipt_type, date_info, payment_info
            )
            
            return {
                'cleaned_text': cleaned_text,
                'best_amount': best_amount,
                'all_amounts': amounts,
                'confidence': overall_confidence,
                'receipt_type': receipt_type,
                'date_info': date_info,
                'payment_info': payment_info,
                'is_valid_receipt': self._is_valid_receipt(cleaned_text, best_amount)
            }
            
        except Exception as e:
            logger.error("Receipt analysis failed", error=str(e))
            return {
                'cleaned_text': text,
                'best_amount': None,
                'all_amounts': [],
                'confidence': 0.0,
                'receipt_type': 'unknown',
                'date_info': None,
                'payment_info': None,
                'is_valid_receipt': False
            }
    
    def _detect_receipt_type(self, text: str) -> str:
        """Detect the type of receipt."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['bank', 'atm', 'withdrawal', 'deposit']):
            return 'bank'
        elif any(word in text_lower for word in ['mobile', 'wallet', 'easypaisa', 'jazzcash']):
            return 'mobile_wallet'
        elif any(word in text_lower for word in ['online', 'internet', 'web']):
            return 'online'
        elif any(word in text_lower for word in ['cash', 'counter']):
            return 'cash'
        else:
            return 'unknown'
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from receipt text."""
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}\b',
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        
        return None
    
    def _detect_payment_method(self, text: str) -> Optional[str]:
        """Detect payment method from receipt text."""
        text_lower = text.lower()
        
        payment_methods = {
            'credit_card': ['credit', 'visa', 'mastercard', 'card'],
            'debit_card': ['debit', 'atm card'],
            'bank_transfer': ['transfer', 'neft', 'rtgs', 'imps'],
            'mobile_wallet': ['easypaisa', 'jazzcash', 'upaisa', 'sadapay'],
            'cash': ['cash', 'counter']
        }
        
        for method, keywords in payment_methods.items():
            if any(keyword in text_lower for keyword in keywords):
                return method
        
        return None
    
    def _calculate_overall_confidence(
        self, 
        amount_confidence: float, 
        receipt_type: str, 
        date_info: Optional[str], 
        payment_info: Optional[str]
    ) -> float:
        """Calculate overall confidence score for the receipt."""
        confidence = amount_confidence
        
        # Boost for recognized receipt type
        if receipt_type != 'unknown':
            confidence += 0.1
        
        # Boost for date information
        if date_info:
            confidence += 0.05
        
        # Boost for payment method information
        if payment_info:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _is_valid_receipt(self, text: str, amount: Optional[float]) -> bool:
        """Determine if this appears to be a valid receipt."""
        if not amount:
            return False
        
        text_lower = text.lower()
        
        # Must have some receipt-related keywords
        receipt_keywords = [
            'receipt', 'transaction', 'payment', 'amount', 'total',
            'bank', 'atm', 'cash', 'deposit', 'withdrawal'
        ]
        
        has_receipt_keywords = any(keyword in text_lower for keyword in receipt_keywords)
        
        # Must have reasonable amount
        has_reasonable_amount = 10 <= amount <= 10_000_000
        
        # Must have minimum text length
        has_sufficient_text = len(text.strip()) >= 20
        
        return has_receipt_keywords and has_reasonable_amount and has_sufficient_text