"""ETL pipeline for processing contractor data"""

import pandas as pd
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models import Contractor
from app.config import get_settings

settings = get_settings()


class ETLPipeline:
    """Extract, Transform, Load pipeline for contractor data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def extract(self, raw_data: List[Dict]) -> pd.DataFrame:
        """
        Extract raw data into DataFrame
        
        Args:
            raw_data: List of raw contractor dictionaries
            
        Returns:
            DataFrame with extracted data
        """
        return pd.DataFrame(raw_data)
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform and clean data
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Remove duplicates
        df = df.drop_duplicates(subset=["name", "phone"], keep="first")
        
        # Clean phone numbers
        if "phone" in df.columns:
            df["phone"] = df["phone"].apply(self._clean_phone)
        
        # Clean email addresses
        if "email" in df.columns:
            df["email"] = df["email"].str.lower().str.strip()
            df["email"] = df["email"].apply(self._validate_email)
        
        # Clean website URLs
        if "website" in df.columns:
            df["website"] = df["website"].apply(self._normalize_url)
        
        # Standardize zipcode format
        if "zipcode" in df.columns:
            df["zipcode"] = df["zipcode"].astype(str).str.strip()
        
        # Fill missing values
        df = df.fillna("")
        
        return df
    
    def load(self, df: pd.DataFrame) -> List[Contractor]:
        """
        Load transformed data into database
        
        Args:
            df: Transformed DataFrame
            
        Returns:
            List of created/updated Contractor objects
        """
        contractors = []
        
        for _, row in df.iterrows():
            # Check if contractor already exists
            existing = self.db.query(Contractor).filter(
                Contractor.name == row.get("name"),
                Contractor.zipcode == row.get("zipcode")
            ).first()
            
            if existing:
                # Update existing contractor
                for key, value in row.items():
                    if hasattr(existing, key) and value:
                        setattr(existing, key, value)
                contractors.append(existing)
            else:
                # Create new contractor
                contractor = Contractor(**row.to_dict())
                self.db.add(contractor)
                contractors.append(contractor)
        
        self.db.commit()
        return contractors
    
    def run(self, raw_data: List[Dict]) -> List[Contractor]:
        """
        Run complete ETL pipeline
        
        Args:
            raw_data: Raw contractor data
            
        Returns:
            List of Contractor objects
        """
        df = self.extract(raw_data)
        df = self.transform(df)
        contractors = self.load(df)
        return contractors
    
    @staticmethod
    def _clean_phone(phone: str) -> str:
        """Clean and normalize phone number"""
        if not phone:
            return ""
        # Remove non-digit characters except +
        cleaned = "".join(c for c in str(phone) if c.isdigit() or c == "+")
        return cleaned
    
    @staticmethod
    def _validate_email(email: str) -> Optional[str]:
        """Validate email format"""
        if not email or "@" not in email:
            return None
        return email
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize website URL"""
        if not url:
            return ""
        url = str(url).strip()
        if url and not url.startswith(("http://", "https://")):
            return f"https://{url}"
        return url

