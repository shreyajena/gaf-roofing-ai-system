"""Scraper for GAF contractor listing/search results page"""

import time
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import tempfile

from app.config import get_settings

settings = get_settings()


class ListingScraper:
    """Scrapes contractor listings from GAF search results page"""
    
    BASE_URL = "https://www.gaf.com/en-us/roofing-contractors/residential"
    
    def __init__(self, zipcode: str = "10013", distance: int = 25, delay: float = 2.0):
        """
        Initialize listing scraper
        
        Args:
            zipcode: ZIP code for search
            distance: Search radius in miles
            delay: Delay between requests in seconds
        """
        self.zipcode = zipcode
        self.distance = distance
        self.delay = delay
        self.driver = None
    
    def _setup_driver(self):
        """Set up Chrome WebDriver with appropriate options"""
        if self.driver:
            return self.driver
        
        chrome_options = Options()
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"--user-agent={user_agent}")
        chrome_options.add_argument("--accept-language=en-US,en;q=0.9")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        temp_dir = tempfile.mkdtemp(prefix="gaf_chrome_")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride", {"userAgent": user_agent}
            )
            self.driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """
                },
            )
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(20)
            return self.driver
        except Exception as e:
            print(f"Error setting up Chrome WebDriver: {e}")
            return None
    
    def _safe_navigate(self, url: str, max_retries: int = 3) -> bool:
        """Safely navigate with retry and anti-access-denied logic"""
        if not self.driver:
            self._setup_driver()
        
        if not self.driver:
            return False
        
        for attempt in range(max_retries):
            try:
                print(f"Navigating to {url} (attempt {attempt+1}/{max_retries})")
                self.driver.get(url)
                
                WebDriverWait(self.driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                if "Access Denied" in self.driver.title or "Forbidden" in self.driver.title:
                    print("Access denied, retrying...")
                    time.sleep(random.uniform(5, 10))
                    continue
                
                # Wait for listings to load
                time.sleep(3)
                
                # Scroll to load content
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                return True
                
            except Exception as e:
                print(f"Navigation error: {e}")
                time.sleep(random.uniform(2, 5))
        
        return False
    
    def build_search_url(self) -> str:
        """Build the search URL with parameters"""
        return f"{self.BASE_URL}?distance={self.distance}&zipcode={self.zipcode}"
    
    def scrape_listings(self, limit: int = 10) -> List[Dict]:
        """
        Scrape contractor listings from search results
        
        Args:
            limit: Maximum number of contractors to scrape
            
        Returns:
            List of contractor dictionaries with listing-level data
        """
        url = self.build_search_url()
        contractors = []
        
        try:
            if not self._safe_navigate(url):
                print("Failed to navigate to listings page")
                return contractors
            
            # Wait for listing elements to appear
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.contractor-listing__results"))
                )
            except TimeoutException:
                print("Timeout waiting for listing elements to load")
            
            # Additional scroll to ensure all content is loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "lxml")
            
            # Find all contractor listing cards
            # Structure: ul.contractor-listing__results > li > article.certification-card
            listing_elements = soup.select("ul.contractor-listing__results > li > article.certification-card")
            
            print(f"Found {len(listing_elements)} listing elements")
            
            for element in listing_elements[:limit]:
                contractor_data = self._parse_listing_element(element)
                if contractor_data:
                    contractors.append(contractor_data)
            
            # Rate limiting
            time.sleep(self.delay)
            
        except Exception as e:
            print(f"Error parsing listings: {e}")
            import traceback
            traceback.print_exc()
        
        return contractors
    
    def cleanup(self):
        """Clean up the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _parse_listing_element(self, element) -> Optional[Dict]:
        """
        Parse individual contractor listing element
        
        Args:
            element: BeautifulSoup element for a contractor listing
            
        Returns:
            Dictionary with listing-level data or None
        """
        try:
            # Extract contractor name from h2.certification-card__heading > a > span
            contractor_data = {
                "contractor_name": self._extract_contractor_name(element),
                "rating": self._extract_rating(element),
                "review_count": self._extract_review_count(element),
                "city": None,  # Will be parsed from city string
                "state": None,  # Will be parsed from city string
                "certifications": self._extract_certifications(element),
                "profile_url": self._extract_profile_url(element),
                "external_contractor_id": None  # Will be set after extracting URL
            }
            
            # Parse city and state from certification-card__city
            city_state = self._extract_city_state(element)
            if city_state:
                contractor_data["city"] = city_state.get("city")
                contractor_data["state"] = city_state.get("state")
            
            # Derive external_contractor_id from profile_url
            if contractor_data["profile_url"]:
                contractor_data["external_contractor_id"] = self._extract_contractor_id(
                    contractor_data["profile_url"]
                )
            
            # Only return if we have at least a name
            if contractor_data["contractor_name"]:
                return contractor_data
            
        except Exception as e:
            print(f"Error parsing listing element: {e}")
        
        return None
    
    def _extract_text(self, element, selector: str) -> str:
        """Extract text from element by CSS selector"""
        found = element.select_one(selector)
        return found.get_text(strip=True) if found else ""
    
    def _extract_contractor_name(self, element) -> str:
        """Extract contractor name from h2.certification-card__heading > a > span"""
        # Try span first (more specific), then fallback to heading text
        span = element.select_one("h2.certification-card__heading a span")
        if span:
            return span.get_text(strip=True)
        
        # Fallback: get text from heading link
        heading_link = element.select_one("h2.certification-card__heading a")
        if heading_link:
            return heading_link.get_text(strip=True)
        
        return ""
    
    def _extract_rating(self, element) -> Optional[float]:
        """Extract rating from span.rating-stars__average"""
        rating_elem = element.select_one("span.rating-stars__average")
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            try:
                return float(rating_text)
            except ValueError:
                pass
        
        return None
    
    def _extract_review_count(self, element) -> int:
        """Extract review count from span.rating-stars__total (format: "(50)")"""
        count_elem = element.select_one("span.rating-stars__total")
        if count_elem:
            count_text = count_elem.get_text(strip=True)
            # Extract number from text like "(50)" or "(244)"
            match = re.search(r'\((\d+)\)', count_text)
            if match:
                return int(match.group(1))
        
        return 0
    
    def _extract_city_state(self, element) -> Optional[Dict[str, str]]:
        """
        Extract city and state from p.certification-card__city
        Format: "New Hyde Park, NY - 17.0 mi"
        
        Returns:
            Dictionary with 'city' and 'state' keys or None
        """
        city_elem = element.select_one("p.certification-card__city")
        if city_elem:
            city_text = city_elem.get_text(strip=True)
            # Parse format: "City, ST - X.X mi"
            # Remove distance part
            city_state_part = re.sub(r'\s*-\s*\d+\.\d+\s*mi\s*$', '', city_text)
            # Split by comma
            parts = [p.strip() for p in city_state_part.split(",")]
            if len(parts) >= 2:
                return {
                    "city": parts[0],
                    "state": parts[1].upper()[:2]  # Ensure 2-letter state code
                }
        
        return None
    
    def _extract_certifications(self, element) -> List[str]:
        """
        Extract certifications from ul.certification-card__certifications-list > li.certification-card__certification
        Text is directly in the <li> element
        """
        certifications = []
        cert_elements = element.select("ul.certification-card__certifications-list > li.certification-card__certification")
        
        for cert_elem in cert_elements:
            cert_text = cert_elem.get_text(strip=True)
            if cert_text:
                certifications.append(cert_text)
        
        return certifications
    
    def _extract_profile_url(self, element) -> Optional[str]:
        """
        Extract profile URL from h2.certification-card__heading > a
        URL is already full (absolute), but we'll ensure it's complete
        """
        link = element.select_one("h2.certification-card__heading a")
        
        if link:
            href = link.get("href")
            if href:
                # URLs are already absolute, but ensure they're complete
                if href.startswith("http"):
                    return href
                else:
                    return urljoin(self.BASE_URL, href)
        
        return None
    
    def _extract_contractor_id(self, url: str) -> Optional[str]:
        """
        Extract external contractor ID from profile URL
        
        URL format: https://www.gaf.com/en-us/roofing-contractors/residential/usa/ny/new-hyde-park/preferred-exterior-corp-1004859
        ID is the number at the end of the URL path after the last hyphen
        
        Args:
            url: Profile URL
            
        Returns:
            Contractor ID string (e.g., "1004859") or None
        """
        if not url:
            return None
        
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        
        if path_parts:
            # Get the last part of the path (e.g., "preferred-exterior-corp-1004859")
            last_part = path_parts[-1]
            # Extract the number at the end (after last hyphen)
            match = re.search(r'-(\d+)$', last_part)
            if match:
                return match.group(1)
        
        return None

