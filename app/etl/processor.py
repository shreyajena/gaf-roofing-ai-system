"""ETL processor for normalizing and cleaning contractor data"""

import re
from typing import Dict, Optional, List
from datetime import datetime


class ETLProcessor:
    """Processes and normalizes scraped contractor data"""
    
    # Certification name normalization mapping
    CERTIFICATION_NORMALIZATION = {
        # Common variations - user can expand this based on actual GAF certifications
        "master elite": "Master Elite",
        "master elite contractor": "Master Elite",
        "gaf master elite": "Master Elite",
        "certified": "Certified",
        "certified contractor": "Certified",
    }
    
    def process_listing_data(self, raw_data: Dict) -> Dict:
        """
        Process listing-level data
        
        Args:
            raw_data: Raw scraped listing data
            
        Returns:
            Cleaned and normalized listing data
        """
        processed = raw_data.copy()
        
        # Normalize contractor name
        if "contractor_name" in processed:
            processed["contractor_name"] = self._clean_text(processed["contractor_name"])
        
        # Normalize city and state
        if "city" in processed:
            processed["city"] = self._clean_text(processed["city"])
        if "state" in processed:
            processed["state"] = processed["state"].upper().strip()[:2]  # Ensure 2-letter code
        
        # Normalize certifications
        if "certifications" in processed and isinstance(processed["certifications"], list):
            processed["certifications"] = [
                self._normalize_certification(cert) for cert in processed["certifications"]
            ]
        
        return processed
    
    def process_profile_data(self, raw_data: Dict, listing_data: Dict) -> Dict:
        """
        Process profile-level data
        
        Args:
            raw_data: Raw scraped profile data
            listing_data: Associated listing data for context
            
        Returns:
            Cleaned and normalized profile data
        """
        processed = raw_data.copy()
        
        # Normalize years_in_business
        if "years_in_business" in processed:
            processed["years_in_business"] = self._normalize_years(processed["years_in_business"])
        
        # Normalize business_start_year
        if "business_start_year" in processed:
            processed["business_start_year"] = self._normalize_start_year(
                processed["business_start_year"]
            )
        
        # Clean address
        if "address" in processed:
            processed["address"] = self._clean_address(processed["address"])
        
        # Clean phone
        if "phone" in processed:
            processed["phone"] = self._clean_phone(processed["phone"])
        
        # Clean about text
        if "about_text" in processed:
            processed["about_text"] = self._clean_text(processed["about_text"])
        
        # Clean review snippets
        if "review_snippets" in processed and isinstance(processed["review_snippets"], list):
            processed["review_snippets"] = [
                self._clean_text(snippet) for snippet in processed["review_snippets"]
            ]
        
        return processed
    
    def calculate_data_confidence(self, listing_data: Dict, profile_data: Dict) -> str:
        """
        Calculate data confidence level (high/medium/low)
        
        Args:
            listing_data: Processed listing data
            profile_data: Processed profile data
            
        Returns:
            Confidence level string
        """
        score = 0
        max_score = 10
        
        # Listing data completeness (4 points)
        if listing_data.get("contractor_name"):
            score += 1
        if listing_data.get("city") and listing_data.get("state"):
            score += 1
        if listing_data.get("rating") is not None:
            score += 1
        if listing_data.get("profile_url"):
            score += 1
        
        # Profile data completeness (6 points)
        if profile_data.get("address"):
            score += 1
        if profile_data.get("phone"):
            score += 1
        if profile_data.get("years_in_business"):
            score += 1
        if profile_data.get("employee_range"):
            score += 1
        if profile_data.get("about_text"):
            score += 1
        if profile_data.get("review_snippets"):
            score += 1
        
        # Determine confidence level
        if score >= 8:
            return "high"
        elif score >= 5:
            return "medium"
        else:
            return "low"
    
    @staticmethod
    def _clean_text(text: Optional[str]) -> Optional[str]:
        """Clean and normalize text fields"""
        if not text:
            return None
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', str(text).strip())
        
        # Remove special control characters but keep standard punctuation
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text if text else None
    
    @staticmethod
    def _normalize_years(years: Optional[int]) -> Optional[int]:
        """Normalize years in business value"""
        if years is None:
            return None
        
        # Sanity check: reasonable range
        if 0 <= years <= 200:
            return years
        
        return None
    
    @staticmethod
    def _normalize_start_year(year: Optional[int]) -> Optional[int]:
        """Normalize business start year"""
        if year is None:
            return None
        
        current_year = datetime.now().year
        
        # Sanity check: reasonable range (1800 to current year)
        if 1800 <= year <= current_year:
            return year
        
        return None
    
    @staticmethod
    def _clean_address(address: Optional[str]) -> Optional[str]:
        """Clean address text"""
        if not address:
            return None
        
        # Remove excessive whitespace and newlines
        address = re.sub(r'\s+', ' ', str(address).strip())
        address = re.sub(r',\s*,', ',', address)  # Remove double commas
        
        return address if address else None
    
    @staticmethod
    def _clean_phone(phone: Optional[str]) -> Optional[str]:
        """Clean and normalize phone number"""
        if not phone:
            return None
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
        # Remove leading + if followed by 1 (US country code)
        if cleaned.startswith("+1"):
            cleaned = cleaned[2:]
        elif cleaned.startswith("1") and len(cleaned) == 11:
            cleaned = cleaned[1:]
        
        # Validate format (10 digits)
        if len(cleaned) == 10 and cleaned.isdigit():
            return cleaned
        
        return None
    
    def _normalize_certification(self, cert: str) -> str:
        """
        Normalize certification name
        
        Args:
            cert: Raw certification text
            
        Returns:
            Normalized certification name
        """
        if not cert:
            return ""
        
        cert_lower = cert.lower().strip()
        
        # Check normalization mapping
        for key, normalized in self.CERTIFICATION_NORMALIZATION.items():
            if key in cert_lower:
                return normalized
        
        # Default: title case
        return cert.strip().title()

