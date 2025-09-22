"""
Deduplication Service for family deduplication
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Service for handling family deduplication"""
    
    def is_duplicate_family(
        self,
        employee: Any,
        selected_beneficiaries: List[Dict],
        db: Session
    ) -> bool:
        """
        Check if employee belongs to an already selected family
        
        Args:
            employee: Employee to check
            selected_beneficiaries: List of already selected beneficiaries
            db: Database session
        
        Returns:
            True if duplicate family member
        """
        # Get employee's family key
        family_key = employee.family_key or employee.calculate_family_key()
        
        for ben in selected_beneficiaries:
            # Check family key match
            if ben["family_key"] == family_key:
                # Fuzzy match on names for confirmation
                if self._fuzzy_match_names(
                    employee.name,
                    employee.father_name,
                    ben["employee"].name,
                    ben["employee"].father_name
                ):
                    logger.info(f"Duplicate family detected: {employee.name} matches {ben['employee'].name}")
                    return True
        
        return False
    
    def _fuzzy_match_names(
        self,
        name1: str,
        father1: str,
        name2: str,
        father2: str,
        threshold: float = 0.8
    ) -> bool:
        """
        Fuzzy match names to detect family members
        
        Args:
            name1: First person's name
            father1: First person's father name
            name2: Second person's name
            father2: Second person's father name
            threshold: Similarity threshold
        
        Returns:
            True if names are similar enough to be same family
        """
        # Check father name similarity (strong indicator)
        if father1 and father2:
            father_similarity = SequenceMatcher(None, father1.lower(), father2.lower()).ratio()
            if father_similarity >= threshold:
                return True
        
        # Check if last names match (assuming last word is family name)
        name1_parts = name1.split()
        name2_parts = name2.split()
        
        if name1_parts and name2_parts:
            last1 = name1_parts[-1].lower()
            last2 = name2_parts[-1].lower()
            
            if SequenceMatcher(None, last1, last2).ratio() >= threshold:
                return True
        
        return False
    
    def find_family_members(
        self,
        employee: Any,
        db: Session
    ) -> List[Any]:
        """
        Find all family members of an employee
        
        Args:
            employee: Employee to find family for
            db: Database session
        
        Returns:
            List of family member employees
        """
        from app.models.employee import Employee
        
        family_key = employee.family_key or employee.calculate_family_key()
        
        # Find by family key
        family_members = db.query(Employee).filter(
            Employee.family_key == family_key,
            Employee.id != employee.id
        ).all()
        
        # Additional fuzzy matching on father name
        if employee.father_name:
            potential_members = db.query(Employee).filter(
                Employee.id != employee.id
            ).all()
            
            for emp in potential_members:
                if emp not in family_members:
                    if self._fuzzy_match_names(
                        employee.name,
                        employee.father_name,
                        emp.name,
                        emp.father_name
                    ):
                        family_members.append(emp)
        
        return family_members
    
    def merge_duplicate_records(
        self,
        primary_id: int,
        duplicate_ids: List[int],
        db: Session
    ) -> bool:
        """
        Merge duplicate employee records
        
        Args:
            primary_id: Primary employee ID to keep
            duplicate_ids: List of duplicate IDs to merge
            db: Database session
        
        Returns:
            Success status
        """
        from app.models.employee import Employee
        
        try:
            primary = db.query(Employee).filter(Employee.id == primary_id).first()
            
            if not primary:
                logger.error(f"Primary employee {primary_id} not found")
                return False
            
            for dup_id in duplicate_ids:
                duplicate = db.query(Employee).filter(Employee.id == dup_id).first()
                
                if duplicate:
                    # Update primary with any missing information
                    if not primary.father_name and duplicate.father_name:
                        primary.father_name = duplicate.father_name
                    
                    if not primary.mobile and duplicate.mobile:
                        primary.mobile = duplicate.mobile
                    
                    if not primary.email and duplicate.email:
                        primary.email = duplicate.email
                    
                    # Update aid count
                    primary.previous_aid_count += duplicate.previous_aid_count
                    
                    # Mark duplicate as inactive or delete
                    duplicate.is_eligible = False
                    
                    logger.info(f"Merged employee {dup_id} into {primary_id}")
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error merging duplicates: {e}")
            db.rollback()
            return False