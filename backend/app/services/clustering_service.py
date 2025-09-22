"""
Clustering service for pickup scheduling optimization.

This module uses K-means clustering to group beneficiaries by location
to minimize crowding at pickup points.
"""
from sklearn.cluster import KMeans
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ClusteringService:
    """Service for optimizing pickup schedules using clustering."""

    def __init__(self):
        self.default_coords = (33.6846, 73.0479)  # Islamabad coordinates

    def cluster_employees(self, employees: List[Dict], n_clusters: Optional[int] = None) -> Dict:
        """Cluster employees by location for pickup scheduling."""
        if not employees:
            return {}

        # Extract coordinates
        coords = []
        employee_indices = []

        for i, emp in enumerate(employees):
            if emp.get('latitude') and emp.get('longitude'):
                coords.append([emp['latitude'], emp['longitude']])
            else:
                # Use default coordinates for missing location data
                coords.append([self.default_coords[0], self.default_coords[1]])
            employee_indices.append(i)

        coords = np.array(coords)

        # Determine number of clusters
        if n_clusters is None:
            n_clusters = min(5, len(employees) // 10)  # 1 cluster per 10 employees, max 5
            n_clusters = max(1, n_clusters)

        # Perform K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(coords)

        # Group employees by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = {
                    'employees': [],
                    'center': kmeans.cluster_centers_[label].tolist()
                }
            clusters[label]['employees'].append(employees[employee_indices[i]])

        logger.info(f"Clustered {len(employees)} employees into {n_clusters} pickup groups")
        return clusters

    def assign_time_slots(self, clusters: Dict, base_datetime: datetime) -> Dict:
        """Assign time slots to clusters to minimize overlap."""
        # Define time slots (30-minute intervals)
        time_slots = [
            base_datetime.replace(hour=9, minute=0),
            base_datetime.replace(hour=9, minute=30),
            base_datetime.replace(hour=10, minute=0),
            base_datetime.replace(hour=10, minute=30),
            base_datetime.replace(hour=11, minute=0),
            base_datetime.replace(hour=14, minute=0),
            base_datetime.replace(hour=14, minute=30),
            base_datetime.replace(hour=15, minute=0),
            base_datetime.replace(hour=15, minute=30),
        ]

        # Assign slots to clusters
        for i, (cluster_id, cluster_data) in enumerate(clusters.items()):
            slot_index = i % len(time_slots)
            slot_time = time_slots[slot_index]
            next_slot_time = slot_time.replace(minute=slot_time.minute + 30)

            cluster_data['pickup_slot'] = f"{slot_time.strftime('%Y-%m-%d %H:%M')}-{next_slot_time.strftime('%H:%M')}"

        return clusters

    def optimize_schedule(self, employees: List[Dict], run_date: datetime) -> List[Dict]:
        """Complete optimization pipeline."""
        # Cluster employees
        clusters = self.cluster_employees(employees)

        # Assign time slots
        clusters_with_slots = self.assign_time_slots(clusters, run_date)

        # Flatten back to employee list with slots
        optimized_employees = []
        for cluster_data in clusters_with_slots.values():
            for emp in cluster_data['employees']:
                emp['pickup_slot'] = cluster_data['pickup_slot']
                optimized_employees.append(emp)

        return optimized_employees


# Global service instance
clustering_service = ClusteringService()