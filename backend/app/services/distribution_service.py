"""
Distribution Service for managing ration distributions
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta
import logging
import numpy as np
from sklearn.cluster import KMeans

from app.models.employee import Employee
from app.models.distribution import Distribution, DistributionBeneficiary, PickupSchedule
from app.services.ml_service import MLService
from app.services.deduplication_service import DeduplicationService

logger = logging.getLogger(__name__)


class DistributionService:
    """Service for managing distributions"""
    
    def __init__(self):
        """Initialize distribution service"""
        self.ml_service = MLService()
        self.dedup_service = DeduplicationService()
    
    async def generate_distribution(
        self,
        db: Session,
        distribution_date: date,
        max_beneficiaries: int,
        created_by: int,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a distribution list with ML-based eligibility and fraud detection
        
        Args:
            db: Database session
            distribution_date: Date of distribution
            max_beneficiaries: Maximum number of beneficiaries
            created_by: User ID creating the distribution
            config: Optional configuration parameters
        
        Returns:
            Distribution result with beneficiary list
        """
        logger.info(f"Generating distribution for {distribution_date} with max {max_beneficiaries} beneficiaries")
        
        # Create distribution record
        distribution = Distribution(
            distribution_date=distribution_date,
            status="pending_approval",
            created_by=created_by,
            config=str(config) if config else None
        )
        db.add(distribution)
        db.commit()
        
        # Get eligible employees
        employees = db.query(Employee).filter(
            Employee.is_eligible == True
        ).order_by(
            Employee.grade.asc(),  # Lower grades first (higher priority)
            Employee.previous_aid_count.asc()  # Fewer previous aids first
        ).all()
        
        logger.info(f"Found {len(employees)} eligible employees")
        
        # Apply ML-based eligibility scoring
        scored_employees = []
        for emp in employees:
            # Check eligibility with ML
            eligibility_result = await self.ml_service.check_eligibility(emp)
            
            # Check fraud
            fraud_data = {
                "grade": emp.grade,
                "family_size": emp.family_size,
                "previous_aid_count": emp.previous_aid_count,
                "duplicate_family": False  # Will be checked in deduplication
            }
            fraud_result = await self.ml_service.detect_fraud(fraud_data)
            
            scored_employees.append({
                "employee": emp,
                "eligibility_score": eligibility_result["score"],
                "fraud_flag": fraud_result["is_fraud"],
                "fraud_score": fraud_result["fraud_score"]
            })
        
        # Sort by eligibility score (descending) and fraud score (ascending)
        scored_employees.sort(
            key=lambda x: (x["eligibility_score"], -x["fraud_score"]),
            reverse=True
        )
        
        # Apply family deduplication
        selected_beneficiaries = []
        selected_families = set()
        excluded_dedup = 0
        excluded_fraud = 0
        excluded_eligibility = 0
        
        for item in scored_employees:
            emp = item["employee"]
            
            # Check if we've reached the limit
            if len(selected_beneficiaries) >= max_beneficiaries:
                break
            
            # Skip if fraud flagged (unless override in config)
            if item["fraud_flag"] and not config.get("include_fraud_flagged", False):
                excluded_fraud += 1
                continue
            
            # Skip if eligibility score too low
            if item["eligibility_score"] < config.get("min_eligibility_score", 0.3):
                excluded_eligibility += 1
                continue
            
            # Family deduplication
            family_key = emp.family_key or emp.calculate_family_key()
            if family_key in selected_families:
                # Check if it's really the same family
                is_duplicate = self.dedup_service.is_duplicate_family(
                    emp, selected_beneficiaries, db
                )
                if is_duplicate:
                    excluded_dedup += 1
                    continue
            
            # Add to selected beneficiaries
            selected_families.add(family_key)
            selected_beneficiaries.append({
                "employee": emp,
                "family_key": family_key,
                "eligibility_score": item["eligibility_score"],
                "fraud_flag": item["fraud_flag"]
            })
        
        # Create beneficiary records
        for idx, ben in enumerate(selected_beneficiaries):
            dist_ben = DistributionBeneficiary(
                distribution_id=distribution.id,
                employee_id=ben["employee"].id,
                family_key=ben["family_key"],
                eligibility_score=ben["eligibility_score"],
                fraud_flag=ben["fraud_flag"],
                priority_rank=idx + 1,
                amount_allocated=5000.0  # Default amount, can be configured
            )
            db.add(dist_ben)
        
        # Update distribution statistics
        distribution.total_beneficiaries = len(selected_beneficiaries)
        distribution.total_families = len(selected_families)
        distribution.total_amount = len(selected_beneficiaries) * 5000.0
        
        db.commit()
        
        logger.info(f"Distribution generated: {len(selected_beneficiaries)} beneficiaries selected")
        logger.info(f"Excluded: {excluded_dedup} (dedup), {excluded_eligibility} (eligibility), {excluded_fraud} (fraud)")
        
        # Prepare response
        beneficiaries_data = []
        for ben in selected_beneficiaries:
            emp = ben["employee"]
            beneficiaries_data.append({
                "employee_id": emp.id,
                "employee_name": emp.name,
                "employee_cnic": f"*****-*******-{emp.cnic[-4:]}",  # Masked
                "grade": emp.grade,
                "family_key": ben["family_key"],
                "family_size": emp.family_size,
                "eligibility_score": round(ben["eligibility_score"], 3),
                "fraud_flag": ben["fraud_flag"],
                "priority_rank": selected_beneficiaries.index(ben) + 1,
                "amount_allocated": 5000.0
            })
        
        return {
            "distribution_id": distribution.id,
            "distribution_date": distribution_date,
            "status": distribution.status,
            "total_beneficiaries": len(selected_beneficiaries),
            "total_families": len(selected_families),
            "beneficiaries": beneficiaries_data,
            "excluded_due_to_deduplication": excluded_dedup,
            "excluded_due_to_eligibility": excluded_eligibility,
            "excluded_due_to_fraud": excluded_fraud
        }
    
    async def generate_pickup_schedules(
        self,
        db: Session,
        distribution_id: int,
        slots_per_day: int = 10,
        minutes_per_slot: int = 30
    ) -> List[PickupSchedule]:
        """
        Generate pickup schedules using clustering for efficient scheduling
        
        Args:
            db: Database session
            distribution_id: Distribution ID
            slots_per_day: Number of pickup slots per day
            minutes_per_slot: Duration of each slot in minutes
        
        Returns:
            List of pickup schedules
        """
        logger.info(f"Generating pickup schedules for distribution {distribution_id}")
        
        # Get distribution and beneficiaries
        distribution = db.query(Distribution).filter(
            Distribution.id == distribution_id
        ).first()
        
        beneficiaries = db.query(DistributionBeneficiary).join(
            Employee
        ).filter(
            DistributionBeneficiary.distribution_id == distribution_id
        ).all()
        
        if not beneficiaries:
            logger.warning("No beneficiaries found for distribution")
            return []
        
        # Prepare location data for clustering
        locations = []
        ben_with_location = []
        ben_without_location = []
        
        for ben in beneficiaries:
            if ben.employee.lat and ben.employee.lon:
                locations.append([ben.employee.lat, ben.employee.lon])
                ben_with_location.append(ben)
            else:
                ben_without_location.append(ben)
        
        # Cluster beneficiaries by location if we have location data
        clusters = {}
        if locations and len(locations) >= slots_per_day:
            # Use KMeans clustering
            n_clusters = min(slots_per_day, len(locations))
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(locations)
            
            for i, ben in enumerate(ben_with_location):
                cluster_id = int(cluster_labels[i])
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(ben)
        else:
            # No clustering, distribute evenly
            for i, ben in enumerate(beneficiaries):
                cluster_id = i % slots_per_day
                if cluster_id not in clusters:
                    clusters[cluster_id] = []
                clusters[cluster_id].append(ben)
        
        # Add beneficiaries without location to smallest clusters
        for ben in ben_without_location:
            smallest_cluster = min(clusters.keys(), key=lambda k: len(clusters[k]))
            clusters[smallest_cluster].append(ben)
        
        # Create pickup schedules
        schedules = []
        pickup_date = distribution.distribution_date
        base_time = datetime.combine(pickup_date, datetime.min.time()).replace(hour=9)  # Start at 9 AM
        
        for slot_num, (cluster_id, cluster_beneficiaries) in enumerate(clusters.items()):
            # Calculate slot time
            start_time = base_time + timedelta(minutes=slot_num * minutes_per_slot)
            end_time = start_time + timedelta(minutes=minutes_per_slot)
            
            # Create schedule
            schedule = PickupSchedule(
                distribution_id=distribution_id,
                pickup_date=pickup_date,
                start_time=start_time,
                end_time=end_time,
                slot_number=slot_num + 1,
                location="Main Distribution Center",  # Default location
                max_beneficiaries=len(cluster_beneficiaries),
                current_beneficiaries=len(cluster_beneficiaries),
                cluster_id=cluster_id
            )
            
            # Set cluster center if we have locations
            if locations and cluster_id < len(kmeans.cluster_centers_):
                schedule.cluster_center_lat = float(kmeans.cluster_centers_[cluster_id][0])
                schedule.cluster_center_lon = float(kmeans.cluster_centers_[cluster_id][1])
            
            db.add(schedule)
            db.flush()  # Get the schedule ID
            
            # Assign beneficiaries to this schedule
            for ben in cluster_beneficiaries:
                ben.pickup_schedule_id = schedule.id
            
            schedules.append(schedule)
        
        db.commit()
        
        logger.info(f"Created {len(schedules)} pickup schedules")
        
        return schedules