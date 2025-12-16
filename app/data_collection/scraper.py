"""GAF contractor data scraper"""

import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin

from app.config import get_settings

settings = get_settings()


class GAFScraper:
    """Scraper for GAF roofing contractor directory"""
    
    BASE_URL = "https://www.gaf.com/en-us/roofing-contractors/residential"
    
    def __init__(self, zipcode: Optional[str] = None, distance: Optional[int] = None):
        self.zipcode = zipcode or settings.default_zipcode
        self.distance = distance or settings.default_distance
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def build_url(self) -> str:
        """Build the search URL with parameters"""
        return f"{self.BASE_URL}?distance={self.distance}&zipcode={self.zipcode}"
    
    def scrape_contractors(self) -> List[Dict]:
        """
        Scrape contractor data from GAF directory
        
        Returns:
            List of contractor dictionaries
        """
        url = self.build_url()
        contractors = []
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "lxml")
            
            # TODO: Implement actual scraping logic based on GAF page structure
            # This is a placeholder structure
            contractor_cards = soup.find_all("div", class_="contractor-card")  # Example selector
            
            for card in contractor_cards:
                contractor_data = self._parse_contractor_card(card)
                if contractor_data:
                    contractors.append(contractor_data)
            
            # Add delay between requests
            time.sleep(settings.scraping_delay)
            
        except Exception as e:
            print(f"Error scraping contractors: {e}")
        
        return contractors
    
    def _parse_contractor_card(self, card) -> Optional[Dict]:
        """
        Parse individual contractor card element
        
        Args:
            card: BeautifulSoup element
            
        Returns:
            Dictionary with contractor data or None
        """
        try:
            # TODO: Implement actual parsing based on GAF page structure
            contractor = {
                "name": self._extract_text(card, "contractor-name"),
                "business_name": self._extract_text(card, "business-name"),
                "address": self._extract_text(card, "address"),
                "phone": self._extract_text(card, "phone"),
                "website": self._extract_link(card, "website"),
                "description": self._extract_text(card, "description"),
                "zipcode": self.zipcode,
                "distance": self.distance,
                "source_url": self.build_url()
            }
            return contractor
        except Exception as e:
            print(f"Error parsing contractor card: {e}")
            return None
    
    def _extract_text(self, element, class_name: str) -> str:
        """Extract text from element by class name"""
        found = element.find(class_=class_name)
        return found.get_text(strip=True) if found else ""
    
    def _extract_link(self, element, class_name: str) -> str:
        """Extract href from element by class name"""
        found = element.find(class_=class_name)
        if found:
            link = found.get("href") or found.find("a", href=True)
            if link:
                if isinstance(link, str):
                    return urljoin(self.BASE_URL, link)
                return urljoin(self.BASE_URL, link.get("href", ""))
        return ""

