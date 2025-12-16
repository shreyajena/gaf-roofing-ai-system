"""Storage operations for contractor data in SQLite"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Contractor, Certification, ContractorText
from app.etl import ETLProcessor


class ContractorStorage:
    """
    Storage operations for contractor data in SQLite
    
    Handles CRUD operations and data quality management:
    - Upsert logic for idempotent re-scraping (keys on external_contractor_id)
    - Data freshness tracking via last_scraped_at field
    - Data confidence scoring based on completeness
    
    Data Quality & Relevance Over Time:
    - last_scraped_at: Auto-updates on every save/update to track freshness
    - get_stale_contractors(): Identifies contractors needing re-scraping
    - get_freshness_report(): Provides metrics on data freshness
    - For production: Add scheduled jobs (e.g., Celery) to re-scrape stale records
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize storage with database session
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.etl = ETLProcessor()
    
    def save_contractor(
        self,
        listing_data: Dict,
        profile_data: Dict,
        update_existing: bool = True
    ) -> Optional[Contractor]:
        """
        Save contractor data (listing + profile) to database
        
        Args:
            listing_data: Processed listing-level data
            profile_data: Processed profile-level data
            update_existing: Whether to update existing contractor records
            
        Returns:
            Contractor object or None if save failed
        """
        try:
            # Process data through ETL
            processed_listing = self.etl.process_listing_data(listing_data)
            processed_profile = self.etl.process_profile_data(profile_data, processed_listing)
            
            # Calculate data confidence
            data_confidence = self.etl.calculate_data_confidence(
                processed_listing,
                processed_profile
            )
            
            # Check if contractor exists
            external_id = processed_listing.get("external_contractor_id")
            contractor = None
            
            if external_id:
                contractor = self.db.query(Contractor).filter(
                    Contractor.external_contractor_id == external_id
                ).first()
            
            # Create or update contractor
            if contractor and update_existing:
                # Update existing contractor
                self._update_contractor(contractor, processed_listing, processed_profile, data_confidence)
            else:
                # Create new contractor
                contractor = self._create_contractor(
                    processed_listing,
                    processed_profile,
                    data_confidence
                )
                self.db.add(contractor)
            
            # Flush to get the contractor ID before saving related records
            self.db.flush()
            
            # Save certifications (now contractor.id is available)
            if processed_listing.get("certifications"):
                self._save_certifications(contractor, processed_listing["certifications"])
            
            # Save text data
            self._save_text_data(contractor, processed_profile)
            
            # Commit all changes
            self.db.commit()
            self.db.refresh(contractor)
            
            return contractor
            
        except IntegrityError as e:
            self.db.rollback()
            print(f"Integrity error saving contractor: {e}")
            return None
        except Exception as e:
            self.db.rollback()
            print(f"Error saving contractor: {e}")
            return None
    
    def _create_contractor(
        self,
        listing_data: Dict,
        profile_data: Dict,
        data_confidence: str
    ) -> Contractor:
        """Create new Contractor object from processed data"""
        return Contractor(
            contractor_name=listing_data.get("contractor_name"),
            rating=listing_data.get("rating"),
            review_count=listing_data.get("review_count", 0),
            city=listing_data.get("city"),
            state=listing_data.get("state"),
            profile_url=listing_data.get("profile_url"),
            external_contractor_id=listing_data.get("external_contractor_id"),
            years_in_business=profile_data.get("years_in_business"),
            business_start_year=profile_data.get("business_start_year"),
            employee_range=profile_data.get("employee_range"),
            state_license_number=profile_data.get("state_license_number"),
            address=profile_data.get("address"),
            phone=profile_data.get("phone"),
            data_confidence=data_confidence
        )
    
    def _update_contractor(
        self,
        contractor: Contractor,
        listing_data: Dict,
        profile_data: Dict,
        data_confidence: str
    ):
        """Update existing Contractor object with new data"""
        # Update listing-level fields
        if listing_data.get("contractor_name"):
            contractor.contractor_name = listing_data["contractor_name"]
        if listing_data.get("rating") is not None:
            contractor.rating = listing_data["rating"]
        if listing_data.get("review_count") is not None:
            contractor.review_count = listing_data["review_count"]
        if listing_data.get("city"):
            contractor.city = listing_data["city"]
        if listing_data.get("state"):
            contractor.state = listing_data["state"]
        if listing_data.get("profile_url"):
            contractor.profile_url = listing_data["profile_url"]
        
        # Update profile-level fields
        if profile_data.get("years_in_business") is not None:
            contractor.years_in_business = profile_data["years_in_business"]
        if profile_data.get("business_start_year") is not None:
            contractor.business_start_year = profile_data["business_start_year"]
        if profile_data.get("employee_range"):
            contractor.employee_range = profile_data["employee_range"]
        if profile_data.get("state_license_number"):
            contractor.state_license_number = profile_data["state_license_number"]
        if profile_data.get("address"):
            contractor.address = profile_data["address"]
        if profile_data.get("phone"):
            contractor.phone = profile_data["phone"]
        
        # Update metadata
        contractor.data_confidence = data_confidence
    
    def _save_certifications(self, contractor: Contractor, certifications: List[str]):
        """Save certifications for a contractor"""
        # Remove existing certifications
        self.db.query(Certification).filter(
            Certification.contractor_id == contractor.id
        ).delete()
        
        # Add new certifications
        for cert_name in certifications:
            if cert_name:  # Skip empty strings
                cert = Certification(
                    contractor_id=contractor.id,
                    name=cert_name,
                    original_text=cert_name  # Store original for reference
                )
                self.db.add(cert)
    
    def _save_text_data(self, contractor: Contractor, profile_data: Dict):
        """Save unstructured text data for a contractor"""
        # Check if text data already exists
        text_data = self.db.query(ContractorText).filter(
            ContractorText.contractor_id == contractor.id
        ).first()
        
        # Prepare review snippets (concatenate with separator)
        review_snippets = profile_data.get("review_snippets", [])
        review_text = "\n\n---\n\n".join(review_snippets) if review_snippets else None
        
        if text_data:
            # Update existing
            if profile_data.get("about_text"):
                text_data.about_text = profile_data["about_text"]
            if review_text:
                text_data.review_snippets = review_text
        else:
            # Create new
            text_data = ContractorText(
                contractor_id=contractor.id,
                about_text=profile_data.get("about_text"),
                review_snippets=review_text
            )
            self.db.add(text_data)
    
    def get_contractor_by_external_id(self, external_id: str) -> Optional[Contractor]:
        """Get contractor by external ID"""
        return self.db.query(Contractor).filter(
            Contractor.external_contractor_id == external_id
        ).first()
    
    def get_all_contractors(self, limit: Optional[int] = None) -> List[Contractor]:
        """Get all contractors"""
        query = self.db.query(Contractor)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def count_contractors(self) -> int:
        """Get total count of contractors"""
        return self.db.query(Contractor).count()
    
    def get_stale_contractors(self, days_old: int = 30) -> List[Contractor]:
        """
        Get contractors that haven't been scraped in X days (stale data)
        
        This enables re-scraping of outdated records to maintain data freshness.
        
        Args:
            days_old: Number of days since last scrape to consider stale (default: 30)
            
        Returns:
            List of Contractor objects that are stale
        """
        cutoff = datetime.now() - timedelta(days=days_old)
        return self.db.query(Contractor).filter(
            Contractor.last_scraped_at < cutoff
        ).all()
    
    def get_freshness_report(self) -> Dict[str, any]:
        """
        Get summary report of data freshness
        
        Returns metrics about how fresh the contractor data is, which helps
        monitor data quality and relevance over time.
        
        Returns:
            Dictionary with freshness metrics
        """
        now = datetime.now()
        total = self.db.query(Contractor).count()
        
        if total == 0:
            return {
                "total": 0,
                "fresh_7d": 0,
                "fresh_30d": 0,
                "fresh_90d": 0,
                "stale_30d": 0,
                "stale_90d": 0,
                "freshness_rate_30d": 0.0
            }
        
        fresh_7d = self.db.query(Contractor).filter(
            Contractor.last_scraped_at > now - timedelta(days=7)
        ).count()
        
        fresh_30d = self.db.query(Contractor).filter(
            Contractor.last_scraped_at > now - timedelta(days=30)
        ).count()
        
        fresh_90d = self.db.query(Contractor).filter(
            Contractor.last_scraped_at > now - timedelta(days=90)
        ).count()
        
        stale_30d = total - fresh_30d
        stale_90d = total - fresh_90d
        
        return {
            "total": total,
            "fresh_7d": fresh_7d,
            "fresh_30d": fresh_30d,
            "fresh_90d": fresh_90d,
            "stale_30d": stale_30d,
            "stale_90d": stale_90d,
            "freshness_rate_30d": (fresh_30d / total * 100) if total > 0 else 0.0
        }

