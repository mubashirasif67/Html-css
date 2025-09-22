"""
Distribution generation service.

This module handles the logic for generating provisional distribution
lists based on eligibility, family deduplication, and fraud detection.
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple
from datetime import datetime
import logging
from ..models import Employee, DistributionRun, Distribution, Donation
from ..services.eligibility_service import eligibility_service
from ..services.fraud_service import fraud_service
from ..utils import extract_family_key, grade_to_int
from sklearn.cluster import KMeans
import numpy as np

logger = logging.getLogger(__name__)


class DistributionService:
    """Service for generating and managing distributions."""

    def __init__(self, db: Session):
        self.db = db

    def generate_provisional_distribution(self, run_date: datetime, total_budget: float) -> DistributionRun:
        """Generate a provisional distribution list."""
        # Get all eligible employees
        employees = self.db.query(Employee).filter(Employee.is_eligible == True).all()

        if not employees:
            raise ValueError("No eligible employees found")

        # Prepare employee features for ML models
        employee_features = []
        for emp in employees:
            features = {
                'grade': grade_to_int(emp.grade),
                'family_size': emp.family_size,
                'income_estimate': 30000 + (grade_to_int(emp.grade) * 1000),  # Estimate
                'previous_aid_count': len(self.db.query(Distribution).filter(Distribution.employee_id == emp.id).all())
            }
            employee_features.append(features)

        # Predict eligibility
        eligibility_results = eligibility_service.batch_predict(employee_features)

        # Filter eligible employees
        eligible_employees = []
        for i, (emp, (score, decision)) in enumerate(zip(employees, eligibility_results)):
            if decision == "eligible":
                emp.eligibility_score = score
                eligible_employees.append(emp)

        # Apply family deduplication
        eligible_employees = self._deduplicate_families(eligible_employees)

        # Apply fraud detection
        eligible_employees = self._detect_fraud(eligible_employees)

        # Sort by grade (ascending priority)
        eligible_employees.sort(key=lambda x: grade_to_int(x.grade))

        # Assign pickup slots using clustering
        pickup_assignments = self._assign_pickup_slots(eligible_employees, run_date)

        # Calculate distribution amounts
        distribution_amounts = self._calculate_amounts(eligible_employees, total_budget)

        # Create distribution run
        distribution_run = DistributionRun(
            run_date=run_date,
            status="pending",
            total_beneficiaries=len(eligible_employees),
            total_amount=sum(distribution_amounts)
        )
        self.db.add(distribution_run)
        self.db.flush()  # Get ID

        # Create distributions
        for i, (emp, amount, slot) in enumerate(zip(eligible_employees, distribution_amounts, pickup_assignments)):
            distribution = Distribution(
                employee_id=emp.id,
                run_id=distribution_run.id,
                amount=amount,
                pickup_slot=slot
            )
            self.db.add(distribution)

        self.db.commit()
        logger.info(f"Generated provisional distribution for {len(eligible_employees)} employees")

        return distribution_run

    def _deduplicate_families(self, employees: List[Employee]) -> List[Employee]:
        """Remove duplicate family members, keeping the lowest grade (highest priority)."""
        family_groups = {}
        deduplicated = []

        for emp in employees:
            family_key = emp.family_key or extract_family_key(emp.cnic)

            if family_key not in family_groups:
                family_groups[family_key] = []

            family_groups[family_key].append(emp)

        # For each family, keep only the employee with lowest grade
        for family_key, family_members in family_groups.items():
            if len(family_members) == 1:
                deduplicated.extend(family_members)
            else:
                # Sort by grade (ascending) and keep the first
                family_members.sort(key=lambda x: grade_to_int(x.grade))
                deduplicated.append(family_members[0])

        return deduplicated

    def _detect_fraud(self, employees: List[Employee]) -> List[Employee]:
        """Apply fraud detection to employees."""
        fraud_features = []

        for emp in employees:
            features = {
                'amount': emp.eligibility_score * 10000,  # Estimated amount
                'frequency': len(self.db.query(Distribution).filter(Distribution.employee_id == emp.id).all()),
                'amount_variance': 0.1,  # Placeholder
                'time_since_last': 30  # Placeholder
            }
            fraud_features.append(features)

        fraud_results = fraud_service.batch_predict(fraud_features)

        # Filter out fraudulent employees
        non_fraudulent = []
        for emp, (score, is_fraud) in zip(employees, fraud_results):
            emp.fraud_flag = is_fraud
            if not is_fraud:
                non_fraudulent.append(emp)

        return non_fraudulent

    def _assign_pickup_slots(self, employees: List[Employee], run_date: datetime) -> List[str]:
        """Assign pickup time slots using clustering."""
        if len(employees) <= 10:
            # Simple assignment for small groups
            slots = []
            base_time = run_date.replace(hour=9, minute=0)
            for i, emp in enumerate(employees):
                slot_time = base_time.replace(hour=9 + i)
                slot = f"{slot_time.strftime('%Y-%m-%d %H:%M')}-{slot_time.replace(minute=slot_time.minute + 30).strftime('%H:%M')}"
                slots.append(slot)
            return slots

        # Use K-means clustering based on location
        coords = []
        for emp in employees:
            if emp.latitude and emp.longitude:
                coords.append([emp.latitude, emp.longitude])
            else:
                # Assign default coordinates for employees without location
                coords.append([33.6846, 73.0479])  # Islamabad coordinates

        coords = np.array(coords)

        # Determine number of clusters (pickup points)
        n_clusters = min(5, len(employees) // 10)

        if n_clusters > 1:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(coords)

            # Assign slots by cluster
            slots = []
            cluster_times = [
                run_date.replace(hour=9, minute=0),
                run_date.replace(hour=10, minute=0),
                run_date.replace(hour=11, minute=0),
                run_date.replace(hour=14, minute=0),
                run_date.replace(hour=15, minute=0),
            ]

            for i, emp in enumerate(employees):
                cluster_id = cluster_labels[i]
                base_time = cluster_times[cluster_id % len(cluster_times)]
                slot = f"{base_time.strftime('%Y-%m-%d %H:%M')}-{base_time.replace(minute=base_time.minute + 30).strftime('%H:%M')}"
                slots.append(slot)
        else:
            # Fallback to simple assignment
            slots = []
            base_time = run_date.replace(hour=9, minute=0)
            for i, emp in enumerate(employees):
                slot_time = base_time.replace(hour=9 + i % 8)
                slot = f"{slot_time.strftime('%Y-%m-%d %H:%M')}-{slot_time.replace(minute=slot_time.minute + 30).strftime('%H:%M')}"
                slots.append(slot)

        return slots

    def _calculate_amounts(self, employees: List[Employee], total_budget: float) -> List[float]:
        """Calculate distribution amounts based on eligibility scores."""
        if not employees:
            return []

        # Calculate weighted amounts based on eligibility scores
        total_score = sum(emp.eligibility_score for emp in employees)

        if total_score == 0:
            # Equal distribution if no scores
            amount_per_person = total_budget / len(employees)
            return [amount_per_person] * len(employees)

        amounts = []
        for emp in employees:
            # Weight by eligibility score
            weight = emp.eligibility_score / total_score
            amount = total_budget * weight
            amounts.append(max(1000, amount))  # Minimum amount

        return amounts